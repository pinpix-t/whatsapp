"""
Bulk Ordering Service
Handles the complete bulk ordering flow from product selection to discount codes
"""

import logging
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from config.bulk_products import (
    BULK_PRODUCTS, DISCOUNT_CODES, PRODUCT_SELECTION_LIST, PRODUCT_URLS, HOMEPAGE_URL,
    OTHER_PRODUCTS, OTHER_PRODUCTS_LIST, PRICE_POINT_MAPPING
)
from services.bulk_pricing import bulk_pricing_service
from services.freshdesk_service import FreshdeskService
from services.region_lookup import RegionLookupService
from database.redis_store import redis_store
from database.postgres_store import postgres_store
from bot.whatsapp_api import WhatsAppAPI

logger = logging.getLogger(__name__)


class BulkOrderingService:
    """Service for handling bulk ordering conversations"""
    
    def __init__(self, whatsapp_api: WhatsAppAPI):
        self.whatsapp_api = whatsapp_api
        self.redis_store = redis_store
        self.freshdesk_service = FreshdeskService()
        self.region_lookup_service = RegionLookupService()
    
    def _track_stage_transition(self, user_id: str, from_state: Optional[str], to_state: str, selections: Dict, duration_seconds: Optional[float] = None):
        """Track stage transition event"""
        try:
            transition_data = {
                "from_state": from_state,
                "to_state": to_state,
                "flow": "bulk_ordering",
                "duration_seconds": duration_seconds,
                "selections": {k: v for k, v in selections.items() if k not in ["email", "postcode"]},
                "timestamp": datetime.utcnow().isoformat()
            }
            postgres_store.save_analytics_event(
                event_type="stage_transition",
                user_id=user_id,
                data=transition_data
            )
            logger.debug(f"📊 Tracked stage transition: {from_state} -> {to_state} for {user_id}")
        except Exception as e:
            logger.error(f"Error tracking stage transition: {e}", exc_info=True)
    
    def _track_user_action(self, user_id: str, action_type: str, action_value: str, current_state: str):
        """Track user action event (button click, list selection, text input)"""
        try:
            action_data = {
                "action_type": action_type,
                "action_value": action_value,
                "current_state": current_state,
                "flow": "bulk_ordering",
                "timestamp": datetime.utcnow().isoformat()
            }
            postgres_store.save_analytics_event(
                event_type="user_action",
                user_id=user_id,
                data=action_data
            )
            logger.debug(f"📊 Tracked user action: {action_type} = {action_value} in state {current_state} for {user_id}")
        except Exception as e:
            logger.error(f"Error tracking user action: {e}", exc_info=True)
    
    def _set_state_with_tracking(self, user_id: str, new_state: str, data: Dict):
        """Set bulk order state and track transition"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        old_state = state_data.get("state") if state_data else None
        selections = data.get("selections", {})
        
        # Set state and get transition info
        transition_info = self.redis_store.set_bulk_order_state(user_id, new_state, data)
        
        # Track transition if state actually changed
        if old_state and old_state != new_state and transition_info:
            duration = transition_info.get("duration_seconds") if transition_info else None
            self._track_stage_transition(user_id, old_state, new_state, selections, duration)
        
        return transition_info
    
    async def start_bulk_ordering(self, user_id: str) -> None:
        """Start the bulk ordering flow - show product selection"""
        # Reset/clear any existing state first
        self.redis_store.clear_bulk_order_state(user_id)
        self.redis_store.clear_last_message_sent(user_id)
        
        # Set new state (no transition tracking on start)
        self.redis_store.set_bulk_order_state(
            user_id,
            "selecting_product",
            {"selections": {}, "discount_offers": []}
        )
        
        # Track initial entry
        try:
            postgres_store.save_analytics_event(
                event_type="flow_started",
                user_id=user_id,
                data={
                    "flow": "bulk_ordering",
                    "state": "selecting_product",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error tracking flow start: {e}")
        
        # Send product selection list
        sections = [{"rows": PRODUCT_SELECTION_LIST}]
        step_info = {"flow": "bulk_ordering", "state": "selecting_product"}
        await self.whatsapp_api.send_list_message(
            to=user_id,
            body_text="Welcome to Bulk Ordering 👋 I'll get you a quick quote.\n\nWhich product are you interested in?\n\n💡 Tip: Reply 'restart' to start over anytime",
            button_text="Choose Product",
            sections=sections,
            step_info=step_info
        )
    
    def end_bulk_ordering(self, user_id: str) -> None:
        """End bulk ordering flow and clear state"""
        self.redis_store.clear_bulk_order_state(user_id)
        self.redis_store.clear_last_message_sent(user_id)
        logger.info(f"Ended bulk ordering for user {user_id}")
    
    async def handle_interactive_response(self, user_id: str, button_id: str, list_id: Optional[str] = None) -> str:
        """
        Handle interactive response (button or list selection)
        
        Args:
            user_id: User's phone number
            button_id: Button ID or list selection ID
            list_id: List selection ID (if from list message)
        
        Returns:
            Status message
        """
        state_data = self.redis_store.get_bulk_order_state(user_id)
        
        if not state_data:
            # Not in bulk ordering flow, restart
            await self.start_bulk_ordering(user_id)
            return "restarted"
        
        current_state = state_data.get("state")
        selections = state_data.get("selections", {})
        
        # Track user action
        action_id = button_id or list_id
        action_type = "button_click" if button_id else "list_selection"
        if action_id:
            self._track_user_action(user_id, action_type, action_id, current_state)
        
        # Handle product selection
        if current_state == "selecting_product":
            # Handle Other product item selection (e.g., "other_wall_calendar")
            if button_id.startswith("other_") or list_id and list_id.startswith("other_"):
                selection_id = button_id or list_id
                other_product = selection_id.replace("other_", "")
                selections["product"] = other_product
                selections["is_other"] = True
                # Other products skip questions - go straight to quantity
                self._set_state_with_tracking(
                    user_id,
                    "asking_quantity",
                    {"selections": selections, "discount_offers": []}
                )
                await self._ask_quantity(user_id)
                return "other_product_selected"
            
            # Handle main product selection (product_other, product_blankets, etc.)
            elif button_id.startswith("product_") or (list_id and list_id.startswith("product_")):
                selection_id = button_id or list_id
                product = selection_id.replace("product_", "")
                
                # Handle "Other" product selection - show list of Other products
                if product == "other":
                    sections = [{"rows": OTHER_PRODUCTS_LIST}]
                    step_info = {"flow": "bulk_ordering", "state": "selecting_product"}
                    await self.whatsapp_api.send_list_message(
                        to=user_id,
                        body_text="Which product are you interested in?",
                        button_text="Choose Product",
                        sections=sections,
                        step_info=step_info
                    )
                    # Keep state as selecting_product, waiting for other product selection
                    return "other_product_list_shown"
                
                # Regular product (blankets, canvas, etc.)
                selections["product"] = product
                self._set_state_with_tracking(
                    user_id,
                    "selecting_specs",
                    {"selections": selections, "discount_offers": []}
                )
                await self._send_next_question(user_id, product)
                return "product_selected"
        
        # Handle product-specific questions
        elif current_state == "selecting_specs":
            product = selections.get("product")
            if not product:
                # Reset if product missing
                await self.start_bulk_ordering(user_id)
                return "restarted"
            
            # Get the selection ID (could be from button or list)
            selection_id = button_id or list_id or button_id
            
            # Process the selection based on product type
            next_state = await self._process_selection(user_id, product, selection_id, selections)
            return next_state
        
        # Handle quantity limit response
        elif current_state == "handling_quantity_limit":
            if button_id == "quantity_go_to_website":
                logger.info(f"User {user_id} clicked 'Go to website' button")
                product_url = self._get_product_url(selections)
                step_info = {"flow": "bulk_ordering", "state": "handling_quantity_limit"}
                await self.whatsapp_api.send_message(
                    user_id,
                    f"You can find quantity discounts for up to 10 units on our website:\n\n{product_url}\n\nFeel free to reach out if you need help with anything else! 😊",
                    step_info=step_info
                )
                # Clear bulk ordering state
                self.redis_store.clear_bulk_order_state(user_id)
                return "quantity_go_to_website"
            elif button_id == "quantity_change":
                logger.info(f"User {user_id} clicked 'Change quantity' button")
                # Loop back to asking for quantity
                await self._ask_quantity(user_id)
                return "quantity_change"
        
        # Handle discount code acceptance/rejection
        elif current_state in ["offering_first_discount", "offering_second_discount"]:
            if button_id == "discount_accept":
                await self._handle_discount_acceptance(user_id, current_state)
                return "discount_accepted"
            elif button_id == "discount_reject":
                await self._handle_discount_rejection(user_id, current_state)
                return "discount_rejected"
        
        # Handle decline reason follow-up
        if button_id == "decline_not_ready":
            logger.info(f"User {user_id} clicked 'Not ready yet' button")
            await self._handle_decline_not_ready(user_id)
            return "decline_not_ready"
        elif button_id == "decline_too_expensive":
            logger.info(f"User {user_id} clicked 'Too expensive' button")
            await self._handle_decline_too_expensive(user_id)
            return "decline_too_expensive"
        elif button_id == "still_not_ready":
            logger.info(f"User {user_id} clicked 'Still not ready' button")
            await self._handle_decline_not_ready(user_id)
            return "still_not_ready"
        elif button_id == "too_expensive_after_second":
            logger.info(f"User {user_id} clicked 'Too expensive' after second discount")
            await self._handle_too_expensive_after_second(user_id)
            return "too_expensive_after_second"
        
        # Handle rejection reasons (after showing buttons) - legacy handler
        elif current_state == "handling_rejection":
            if button_id == "reject_price":
                # Offer second discount
                await self._offer_second_discount(user_id, selections)
                return "second_discount_offered"
            elif button_id == "reject_delivery":
                # Answer delivery time using RAG
                await self._handle_delivery_time_question(user_id)
                return "delivery_time_answered"
            elif button_id == "reject_agent":
                # Handoff to agent
                await self._handoff_to_agent(user_id, selections)
                return "agent_handoff"
        
        return "unknown_state"
    
    async def _send_next_question(self, user_id: str, product: str) -> None:
        """Send the next question in the product qualification flow"""
        # Check if it's an Other product (no questions)
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        if selections.get("is_other") or product in OTHER_PRODUCTS:
            # Other products skip questions - go straight to quantity
            await self._ask_quantity(user_id)
            return
        
        if product not in BULK_PRODUCTS:
            logger.error(f"Unknown product: {product}")
            await self.whatsapp_api.send_message(
                user_id,
                "Sorry, there was an error. Please try again."
            )
            return
        
        product_config = BULK_PRODUCTS[product]
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        
        # Find which question to ask next
        for question_config in product_config["questions"]:
            step = question_config["step"]
            
            # Skip if already answered
            if step in selections:
                continue
            
            # Ask this question
            state_data = self.redis_store.get_bulk_order_state(user_id)
            current_state = state_data.get("state", "selecting_specs") if state_data else "selecting_specs"
            step_info = {"flow": "bulk_ordering", "state": current_state, "current_step": step}
            
            if question_config["component"] == "buttons":
                buttons = [{"id": opt["id"], "title": opt["title"]} for opt in question_config["options"]]
                await self.whatsapp_api.send_interactive_buttons(
                    to=user_id,
                    body_text=question_config["question"],
                    buttons=buttons,
                    step_info=step_info
                )
            elif question_config["component"] == "list":
                sections = [{"rows": question_config["options"]}]
                await self.whatsapp_api.send_list_message(
                    to=user_id,
                    body_text=question_config["question"],
                    button_text="Choose Option",
                    sections=sections,
                    step_info=step_info
                )
            
            return
        
        # All questions answered, ask for quantity
        await self._ask_quantity(user_id)
    
    async def _process_selection(self, user_id: str, product: str, selection_id: str, selections: Dict) -> str:
        """Process a selection and determine next step"""
        product_config = BULK_PRODUCTS[product]
        
        # Find which question this selection belongs to
        for question_config in product_config["questions"]:
            step = question_config["step"]
            
            # Check if this selection matches any option in this question
            for opt in question_config["options"]:
                if opt["id"] == selection_id:
                    # This is the answer to this question
                    selections[step] = selection_id
                    state_data_current = self.redis_store.get_bulk_order_state(user_id)
                    self._set_state_with_tracking(
                        user_id,
                        "selecting_specs",
                        {"selections": selections, "discount_offers": state_data_current.get("discount_offers", []) if state_data_current else []}
                    )
                    
                    # Check if there are more questions
                    state_data_updated = self.redis_store.get_bulk_order_state(user_id)
                    all_answered = all(
                        q["step"] in state_data_updated.get("selections", {})
                        for q in product_config["questions"]
                    )
                    
                    if all_answered:
                        # All specs collected, ask for quantity
                        await self._ask_quantity(user_id)
                    else:
                        # Ask next question
                        await self._send_next_question(user_id, product)
                    
                    return "selection_processed"
        
        # Selection doesn't match any question - might be quantity or other
        logger.warning(f"Unknown selection ID: {selection_id}")
        return "unknown_selection"
    
    async def _ask_quantity(self, user_id: str) -> None:
        """Ask user for quantity"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        self._set_state_with_tracking(
            user_id,
            "asking_quantity",
            {"selections": state_data.get("selections", {}) if state_data else {}, "discount_offers": []}
        )
        
        step_info = {"flow": "bulk_ordering", "state": "asking_quantity"}
        await self.whatsapp_api.send_message(
            user_id,
            "How many units would you like to order?\n\n💡 Tip: Reply 'restart' to start a new quote",
            step_info=step_info
        )
    
    async def handle_quantity(self, user_id: str, quantity_text: str) -> None:
        """Handle quantity input and ask for email"""
        try:
            # Try to extract number from text
            numbers = re.findall(r'\d+', quantity_text)
            if not numbers:
                await self.whatsapp_api.send_message(
                    user_id,
                    "Please enter a valid number. For example: 50, 100, etc."
                )
                return
            
            quantity = int(numbers[0])
            
            # Check if quantity is 10 or less
            if quantity <= 10:
                state_data = self.redis_store.get_bulk_order_state(user_id)
                selections = state_data.get("selections", {})
                product = selections.get("product", "")
                
                # Get product URL
                product_url = self._get_product_url(selections)
                
                # Update state to handle quantity response
                self._set_state_with_tracking(
                    user_id,
                    "handling_quantity_limit",
                    {"selections": selections, "discount_offers": []}
                )
                
                # Send message with options
                message = f"Quantity discounts for up to 10 units are available on our website. For bulk orders of more than 10 units, I can help you get a special quote.\n\nWhat would you like to do?"
                
                buttons = [
                    {"id": "quantity_go_to_website", "title": "Go to website"},
                    {"id": "quantity_change", "title": "Change quantity"}
                ]
                
                step_info = {"flow": "bulk_ordering", "state": "handling_quantity_limit"}
                await self.whatsapp_api.send_interactive_buttons(
                    to=user_id,
                    body_text=message,
                    buttons=buttons,
                    step_info=step_info
                )
                return
            
            # Quantity is more than 10, proceed normally
            state_data = self.redis_store.get_bulk_order_state(user_id)
            selections = state_data.get("selections", {})
            selections["quantity"] = quantity
            
            # Track text input action
            self._track_user_action(user_id, "text_input", str(quantity), "asking_quantity")
            
            # Update state and ask for email
            self._set_state_with_tracking(
                user_id,
                "asking_email",
                {"selections": selections, "discount_offers": []}
            )
            
            # Ask for email
            await self._ask_for_email(user_id)
            
        except Exception as e:
            logger.error(f"Error processing quantity: {e}")
            await self.whatsapp_api.send_message(
                user_id,
                "Please enter a valid number. For example: 50, 100, etc."
            )
    
    async def _ask_for_email(self, user_id: str) -> None:
        """Ask user for their email address (optional)"""
        message = """Awesome, we're almost done!

Just send your email address so we can send your discount code (optional).

Send your email address, or type 'skip' to continue without it.

💡 Tip: Reply 'restart' to start a new quote"""
        
        step_info = {"flow": "bulk_ordering", "state": "asking_email"}
        await self.whatsapp_api.send_message(user_id, message, step_info=step_info)
    
    async def handle_email(self, user_id: str, email_text: str) -> None:
        """Handle email input and optionally ask for postcode"""
        email_text = email_text.strip().lower()
        
        # Skip if user wants to skip
        if email_text in ['skip', 'no', 'n', 'none', 'not needed']:
            email = None
        else:
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email_text):
                await self.whatsapp_api.send_message(
                    user_id,
                    "Please enter a valid email address. For example: yourname@example.com\n\nOr type 'skip' to continue without it."
                )
                return
            email = email_text
        
        # Store email
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        if email:
            selections["email"] = email
        
        # Track text input action
        self._track_user_action(user_id, "text_input", email if email else "skip", "asking_email")
        
        # Update state and ask for postcode (optional)
        self._set_state_with_tracking(
            user_id,
            "asking_postcode",
            {"selections": selections, "discount_offers": []}
        )
        
        # Ask for postcode (optional)
        await self._ask_for_postcode(user_id)
    
    async def _ask_for_postcode(self, user_id: str) -> None:
        """Ask user for delivery postcode (optional)"""
        message = """Please provide your delivery postcode (optional):

Send your postcode, or type 'skip' to continue without it."""
        
        step_info = {"flow": "bulk_ordering", "state": "asking_postcode"}
        await self.whatsapp_api.send_message(user_id, message, step_info=step_info)
    
    async def handle_postcode(self, user_id: str, postcode_text: str) -> None:
        """Handle postcode input and generate quote"""
        postcode_text = postcode_text.strip().lower()
        
        # Skip if user wants to skip
        if postcode_text in ['skip', 'no', 'n', 'none', 'not needed']:
            postcode = None
        else:
            postcode = postcode_text.upper()
        
        # Store postcode
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        if postcode:
            selections["postcode"] = postcode
        
        # Track text input action
        self._track_user_action(user_id, "text_input", postcode if postcode else "skip", "asking_postcode")
        
        # Now offer discount
        await self._offer_first_discount(user_id, selections)
    
    async def handle_name_for_escalation(self, user_id: str, name_text: str) -> None:
        """Handle name input for escalation (optional)"""
        name_text = name_text.strip()
        
        # Skip if user wants to skip
        if name_text.lower() in ['skip', 'no', 'n', 'none', 'not needed', '']:
            name = None
        else:
            name = name_text
        
        # Store name if provided
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        if name:
            selections["name"] = name
        
        # Track text input action
        self._track_user_action(user_id, "text_input", name if name else "skip", "asking_name_for_escalation")
        
        # Clear pending escalation flag and proceed with escalation
        state_data["selections"] = selections
        state_data.pop("pending_escalation", None)
        # Don't track transition here as we're proceeding to escalation
        self.redis_store.set_bulk_order_state(user_id, state_data.get("state", "unknown"), state_data)
        
        # Proceed with escalation (don't ask for name again)
        await self._escalate_to_support(user_id, selections, ask_name=False)
    
    async def _offer_first_discount(self, user_id: str, selections: Dict) -> None:
        """Offer first discount code with pricing (shows WORSE discount first)"""
        # Validate that we have required selections for this product
        product = selections.get("product", "")
        
        # Check if product requires fabric/size and we have them
        if product in BULK_PRODUCTS:
            product_config = BULK_PRODUCTS[product]
            required_steps = [q["step"] for q in product_config["questions"]]
            missing_steps = [step for step in required_steps if step not in selections]
            
            if missing_steps:
                logger.warning(f"Missing required selections for {product}: {missing_steps}")
                logger.warning(f"Current selections: {selections}")
                # This shouldn't happen if flow is correct, but log it
        
        # Show the worse discount first (second_offer = price point B)
        discount_code = DISCOUNT_CODES["second_offer"]
        
        # Store offer
        state_data = self.redis_store.get_bulk_order_state(user_id)
        offers = state_data.get("discount_offers", [])
        offers.append("first_offer")
        self._set_state_with_tracking(
            user_id,
            "offering_first_discount",
            {"selections": selections, "discount_offers": offers}
        )
        
        # Get product name (handle Other products)
        if product in OTHER_PRODUCTS:
            product_name = OTHER_PRODUCTS[product]["name"]
        elif product in BULK_PRODUCTS:
            product_name = BULK_PRODUCTS[product]["name"]
        else:
            product_name = product.title()
        
        quantity = selections.get("quantity", 0)
        
        # Log selections for debugging
        logger.info(f"Getting pricing for product={product}, selections={selections}, quantity={quantity}")
        
        # Get pricing information - use second_offer (worse discount) first
        price_info = bulk_pricing_service.get_bulk_price_info(
            selections=selections,
            quantity=quantity,
            offer_type="second_offer"
        )
        
        # Log price info for debugging
        logger.info(f"Price info result: success={price_info.get('success')}, base_price={price_info.get('base_price')}, total_price={price_info.get('total_price')}, error={price_info.get('error_message')}")
        
        # Log quote event to analytics
        try:
            quote_data = {
                "whatsapp_number": user_id,
                "product": product_name,
                "product_key": product,
                "quantity": quantity,
                "discount_code": discount_code,
                "discount_percent": price_info.get("discount_percent"),
                "base_price": price_info.get("base_price"),
                "unit_price": price_info.get("unit_price"),
                "total_price": price_info.get("total_price"),
                "formatted_unit_price": price_info.get("formatted_unit_price"),
                "formatted_total_price": price_info.get("formatted_total_price"),
                "email": selections.get("email"),
                "postcode": selections.get("postcode"),
                "offer_type": "first",
                "selections": {k: v for k, v in selections.items() if k not in ["email", "postcode", "quantity"]}
            }
            logger.info(f"📊 Attempting to save analytics event for user {user_id}, product {product_name}, quantity {quantity}")
            postgres_store.save_analytics_event(
                event_type="bulk_quote_generated",
                user_id=user_id,
                email=selections.get("email"),
                data=quote_data
            )
            logger.info(f"✅ Quote event logged successfully for user {user_id}, product {product_name}, quantity {quantity}")
        except Exception as e:
            logger.error(f"❌ Failed to log quote event: {e}", exc_info=True)
        
        # Build message with pricing
        if price_info["success"] and price_info["total_price"] is not None:
            # Full pricing available - show base price (crossed out) and discounted price
            base_price = price_info.get("base_price", 0)
            unit_price = price_info.get("unit_price", 0)
            formatted_base = f"£{base_price:.2f}"
            formatted_unit = f"£{unit_price:.2f}"
            
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units

Per unit: (was {formatted_base}) - {formatted_unit} each
Total: {price_info["formatted_total_price"]}
Discount: {price_info["discount_percent"]:.1f}% off

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?

💡 Tip: Reply 'restart' to start a new quote"""
        elif price_info["success"] and price_info["discount_percent"] is not None:
            # Discount available but no base price
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units
Discount: {price_info["discount_percent"]:.1f}% off

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?

💡 Tip: Reply 'restart' to start a new quote"""
        else:
            # Pricing unavailable
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?"""
        
        buttons = [
            {"id": "discount_accept", "title": "Start creating"},
            {"id": "discount_reject", "title": "No thanks"}
        ]
        
        step_info = {"flow": "bulk_ordering", "state": "offering_first_discount"}
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons,
            step_info=step_info
        )
    
    async def _handle_discount_acceptance(self, user_id: str, current_state: str) -> None:
        """Handle when user accepts discount"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        # Determine correct discount code based on state
        # offering_first_discount = second_offer (worse), offering_second_discount = first_offer (better)
        if current_state == "offering_first_discount":
            discount_code = DISCOUNT_CODES["second_offer"]  # Worse discount shown first
            offer_type = "second_offer"
        else:
            discount_code = DISCOUNT_CODES["first_offer"]  # Better discount shown second
            offer_type = "first_offer"
        
        # Determine product URL
        product = selections.get("product", "")
        product_url = self._get_product_url(selections)
        
        # Create Freshdesk ticket for accepted bulk order
        await self._create_accepted_order_ticket(user_id, selections, discount_code, offer_type)
        
        message = f"""Perfect! Your discount code *{discount_code}* is ready to use on our website.

Visit: {product_url}

Apply the code at checkout. Happy to help with anything else!"""
        
        # Get current state for step_info
        state_data = self.redis_store.get_bulk_order_state(user_id)
        current_state = state_data.get("state", "completed") if state_data else "completed"
        step_info = {"flow": "bulk_ordering", "state": current_state}
        await self.whatsapp_api.send_message(user_id, message, step_info=step_info)
        
        # Clear bulk ordering state and last message tracking
        self.redis_store.clear_bulk_order_state(user_id)
        self.redis_store.clear_last_message_sent(user_id)
    
    def _get_product_url(self, selections: Dict) -> str:
        """Get the appropriate product URL based on selections"""
        product = selections.get("product", "")
        
        # Check if multiple products selected (future feature)
        # For now, single product selection - return product URL or homepage
        if isinstance(product, list) and len(product) > 1:
            # Multiple products - use homepage
            return HOMEPAGE_URL
        
        # Single product - return product-specific URL
        if product in PRODUCT_URLS:
            return PRODUCT_URLS[product]
        
        # Default to homepage if product not found
        return HOMEPAGE_URL
    
    async def handle_discount_text_response(self, user_id: str, text: str, current_state: str) -> None:
        """Handle text responses when user is in discount offering state"""
        text_lower = text.lower().strip()
        
        # Check for rejection words - including "too expensive"
        rejection_words = ['no', 'not happy', 'not satisfied', 'need better', 'better price', 'too high', 'too expensive', 'expensive', 'cant afford', 'decline', 'reject', 'pass', 'skip', 'no thanks']
        acceptance_words = ['yes', 'accept', 'ok', 'okay', 'sure', 'proceed', 'continue', 'use it', 'i\'ll use', 'take it', 'start creating', 'start']
        
        if any(word in text_lower for word in rejection_words):
            # User is rejecting - treat as button click on "discount_reject"
            logger.info(f"User rejected discount via text: {text}")
            await self._handle_discount_rejection(user_id, current_state)
        elif any(word in text_lower for word in acceptance_words):
            # User is accepting - treat as button click on "discount_accept"
            logger.info(f"User accepted discount via text: {text}")
            await self._handle_discount_acceptance(user_id, current_state)
        else:
            # Unclear response - ask them to use buttons
            await self.whatsapp_api.send_message(
                user_id,
                "Please use the buttons above to respond. Or type 'No thanks' if you don't want to proceed, or 'Start creating' if you're ready."
            )
    
    async def handle_decline_reason_text_response(self, user_id: str, text: str) -> None:
        """Handle text responses when user is in decline reason state"""
        text_lower = text.lower().strip()
        
        # Check for "not ready" responses
        not_ready_words = ['not ready', 'not ready yet', 'later', 'maybe later', 'not now', 'wait', 'waiting']
        too_expensive_words = ['too expensive', 'too high', 'expensive', 'cant afford', 'price', 'cost']
        
        if any(word in text_lower for word in not_ready_words):
            logger.info(f"User said not ready via text: {text}")
            await self._handle_decline_not_ready(user_id)
        elif any(word in text_lower for word in too_expensive_words):
            logger.info(f"User said too expensive via text: {text}")
            await self._handle_decline_too_expensive(user_id)
        else:
            # Unclear response - ask them to use buttons
            await self.whatsapp_api.send_message(
                user_id,
                "Please use the buttons above to respond. Or type 'Not ready yet' or 'Too expensive'."
            )
    
    async def _handle_discount_rejection(self, user_id: str, current_state: str) -> None:
        """Handle when user rejects discount - show follow-up question"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        
        # If rejecting second discount, show new buttons
        if current_state == "offering_second_discount":
            await self._ask_after_second_discount(user_id)
        else:
            # First discount rejection - ask for reason
            await self._ask_decline_reason(user_id, selections, state_data)
    
    async def _ask_decline_reason(self, user_id: str, selections: Dict, state_data: Dict) -> None:
        """Ask user for reason they don't want to proceed"""
        # Ensure selections are in state_data
        state_data["selections"] = selections
        
        # Update state to asking for decline reason
        self._set_state_with_tracking(
            user_id,
            "asking_decline_reason",
            state_data
        )
        
        message = "Is there a reason you don't want to proceed?"
        
        buttons = [
            {"id": "decline_not_ready", "title": "Not ready yet"},
            {"id": "decline_too_expensive", "title": "Too expensive"}
        ]
        
        step_info = {"flow": "bulk_ordering", "state": "asking_decline_reason"}
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons,
            step_info=step_info
        )
    
    async def _ask_after_second_discount(self, user_id: str) -> None:
        """Ask user after showing second discount with new buttons"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        if not state_data:
            state_data = {"selections": {}, "discount_offers": []}
        
        # Update state
        self._set_state_with_tracking(
            user_id,
            "asking_after_second_discount",
            state_data
        )
        
        message = "Is there a reason you don't want to proceed?"
        
        buttons = [
            {"id": "still_not_ready", "title": "Still not ready"},
            {"id": "too_expensive_after_second", "title": "Too expensive"}
        ]
        
        step_info = {"flow": "bulk_ordering", "state": "asking_after_second_discount"}
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons,
            step_info=step_info
        )
    
    async def _handle_decline_not_ready(self, user_id: str) -> None:
        """Handle when user says 'Not ready yet'"""
        message = """No problem! Your quote is valid for 14 days, so you can use it at your convenience.

When you're ready, just use the discount code we provided on our website.

Feel free to reach out if you have any questions! 😊"""
        
        await self.whatsapp_api.send_message(user_id, message)
        
        # Clear bulk ordering state
        self.redis_store.clear_bulk_order_state(user_id)
    
    async def _handle_decline_too_expensive(self, user_id: str) -> None:
        """Handle when user says 'Too expensive' - show better discount"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        if not state_data:
            logger.error(f"No state data found for user {user_id} when handling too expensive")
            await self.whatsapp_api.send_message(
                user_id,
                "I apologize, there was an error processing your request. Please try again."
            )
            return
        
        selections = state_data.get("selections", {})
        logger.info(f"User {user_id} said too expensive - showing better discount")
        await self._offer_second_discount(user_id, selections)
    
    async def _handle_too_expensive_after_second(self, user_id: str) -> None:
        """Handle when user says 'Too expensive' after second discount - create Freshdesk ticket"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        if not state_data:
            logger.error(f"No state data found for user {user_id} when handling too expensive after second")
            await self.whatsapp_api.send_message(
                user_id,
                "I apologize, there was an error processing your request. Please try again."
            )
            return
        
        selections = state_data.get("selections", {})
        logger.info(f"User {user_id} said too expensive after second discount - sending to n8n webhook")
        await self._escalate_to_support(user_id, selections, ask_name=False)
    
    async def _offer_second_discount(self, user_id: str, selections: Dict) -> None:
        """Offer better discount code (first_offer = price point D) when user asks for better price"""
        # Show the better discount (first_offer = price point D)
        discount_code = DISCOUNT_CODES["first_offer"]
        
        # Store offer
        state_data = self.redis_store.get_bulk_order_state(user_id)
        offers = state_data.get("discount_offers", [])
        offers.append("second_offer")
        self._set_state_with_tracking(
            user_id,
            "offering_second_discount",
            {"selections": selections, "discount_offers": offers}
        )
        
        # Get product name (handle Other products)
        product = selections.get("product", "")
        if product in OTHER_PRODUCTS:
            product_name = OTHER_PRODUCTS[product]["name"]
        elif product in BULK_PRODUCTS:
            product_name = BULK_PRODUCTS[product]["name"]
        else:
            product_name = product.title()
        
        quantity = selections.get("quantity", 0)
        
        # Get pricing information - use first_offer (better discount)
        price_info = bulk_pricing_service.get_bulk_price_info(
            selections=selections,
            quantity=quantity,
            offer_type="first_offer"
        )
        
        # Log quote event to analytics
        try:
            quote_data = {
                "whatsapp_number": user_id,
                "product": product_name,
                "product_key": product,
                "quantity": quantity,
                "discount_code": discount_code,
                "discount_percent": price_info.get("discount_percent"),
                "base_price": price_info.get("base_price"),
                "unit_price": price_info.get("unit_price"),
                "total_price": price_info.get("total_price"),
                "formatted_unit_price": price_info.get("formatted_unit_price"),
                "formatted_total_price": price_info.get("formatted_total_price"),
                "email": selections.get("email"),
                "postcode": selections.get("postcode"),
                "offer_type": "second",
                "selections": {k: v for k, v in selections.items() if k not in ["email", "postcode", "quantity"]}
            }
            postgres_store.save_analytics_event(
                event_type="bulk_quote_generated",
                user_id=user_id,
                email=selections.get("email"),
                data=quote_data
            )
            logger.info(f"✅ Logged quote event for user {user_id}, product {product_name}, quantity {quantity}")
        except Exception as e:
            logger.error(f"❌ Failed to log quote event: {e}")
        
        # Build message with pricing
        if price_info["success"] and price_info["total_price"] is not None:
            # Full pricing available - show base price (crossed out) and discounted price
            base_price = price_info.get("base_price", 0)
            unit_price = price_info.get("unit_price", 0)
            formatted_base = f"£{base_price:.2f}"
            formatted_unit = f"£{unit_price:.2f}"
            
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units

Per unit: (was {formatted_base}) - {formatted_unit} each
Total: {price_info["formatted_total_price"]}
Discount: {price_info["discount_percent"]:.1f}% off

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?

💡 Tip: Reply 'restart' to start a new quote"""
        elif price_info["success"] and price_info["discount_percent"] is not None:
            # Discount available but no base price
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units
Discount: {price_info["discount_percent"]:.1f}% off

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?

💡 Tip: Reply 'restart' to start a new quote"""
        else:
            # Pricing unavailable
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?"""

        buttons = [
            {"id": "discount_accept", "title": "Start creating"},
            {"id": "discount_reject", "title": "No thanks"}
        ]
        
        step_info = {"flow": "bulk_ordering", "state": "offering_second_discount"}
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons,
            step_info=step_info
        )
    
    async def _escalate_to_support(self, user_id: str, selections: Dict, ask_name: bool = True) -> None:
        """Escalate to support via Freshdesk ticket when user says too expensive after best offer"""
        # Check if we should ask for name first
        if ask_name and not selections.get("name"):
            # Ask for name (optional - don't block if not provided)
            state_data = self.redis_store.get_bulk_order_state(user_id)
            state_data["selections"] = selections
            state_data["pending_escalation"] = True
            self._set_state_with_tracking(user_id, "asking_name_for_escalation", state_data)
            
            step_info = {"flow": "bulk_ordering", "state": "asking_name_for_escalation"}
            await self.whatsapp_api.send_message(
                user_id,
                "Before I forward your request, may I have your name? (This is optional - you can type 'skip' to continue without it.)",
                step_info=step_info
            )
            return
        
        # Get product name (handle Other products)
        product = selections.get("product", "")
        if product in OTHER_PRODUCTS:
            product_name = OTHER_PRODUCTS[product]["name"]
        elif product in BULK_PRODUCTS:
            product_name = BULK_PRODUCTS[product]["name"]
        else:
            product_name = product.title()
        
        quantity = selections.get("quantity", 0)
        customer_email = selections.get("email", "")  # Customer's actual email
        # Freshdesk email field must be b2b@printerpix.co.uk so emails go there
        freshdesk_email = "b2b@printerpix.co.uk"
        postcode = selections.get("postcode", "")
        user_name = selections.get("name", "")  # Optional name
        
        # Get quote details from state
        state_data = self.redis_store.get_bulk_order_state(user_id)
        offers = state_data.get("discount_offers", [])
        
        # Get the best quote that was offered
        best_price_info = bulk_pricing_service.get_bulk_price_info(
            selections=selections,
            quantity=quantity,
            offer_type="first_offer"  # Best offer
        )
        
        # Determine region from postcode (default to UK)
        region = "UK"  # Default
        if postcode:
            region = self.region_lookup_service.get_region_from_postcode(postcode)
        
        # Get product_id and group_id from Supabase
        product_id, group_id = self.region_lookup_service.get_region_ids(region)
        
        # Build email description (HTML format, no Unix/Windows newlines)
        description_parts = []
        
        if user_name:
            description_parts.append(f"<p><strong>Customer Name:</strong> {user_name}</p>")
        
        # Customer's actual email goes in description (body)
        if customer_email:
            description_parts.append(f"<p><strong>Customer Email Address:</strong> {customer_email}</p>")
        else:
            description_parts.append(f"<p><strong>Customer Email Address:</strong> Not provided</p>")
        description_parts.append(f"<p><strong>Product:</strong> {product_name}</p>")
        description_parts.append(f"<p><strong>Quantity:</strong> {quantity} units</p>")
        
        # Add selections details
        selections_text = []
        if selections.get("fabric"):
            selections_text.append(f"Fabric: {selections.get('fabric')}")
        if selections.get("cover"):
            selections_text.append(f"Cover: {selections.get('cover')}")
        if selections.get("type"):
            selections_text.append(f"Type: {selections.get('type')}")
        if selections.get("size"):
            selections_text.append(f"Size: {selections.get('size')}")
        if selections.get("pages"):
            selections_text.append(f"Pages: {selections.get('pages')}")
        
        if selections_text:
            description_parts.append(f"<p><strong>Selections:</strong> {', '.join(selections_text)}</p>")
        
        # Add quote details
        if best_price_info.get("discount_percent"):
            discount = best_price_info.get("discount_percent", 0)
            description_parts.append(f"<p><strong>Discount Offered:</strong> {discount:.1f}%</p>")
        
        if best_price_info.get("formatted_unit_price"):
            description_parts.append(f"<p><strong>Unit Price:</strong> {best_price_info.get('formatted_unit_price')}</p>")
        
        if best_price_info.get("formatted_total_price"):
            description_parts.append(f"<p><strong>Total Price:</strong> {best_price_info.get('formatted_total_price')}</p>")
        
        if postcode:
            description_parts.append(f"<p><strong>Postcode:</strong> {postcode}</p>")
        
        description_parts.append(f"<p><strong>Region:</strong> {region}</p>")
        
        # Add context about offers shown
        if offers:
            offers_shown = ", ".join(offers)
            description_parts.append(f"<p><strong>Offers Shown:</strong> {offers_shown}</p>")
        
        # Add which quote level was shown when they said too expensive
        quote_level = selections.get("escalation_quote_level", "unknown")
        quote_state = selections.get("escalation_quote_state", "unknown")
        if quote_level != "unknown":
            quote_level_name = "First Quote (Worse Discount)" if quote_level == "second_offer" else "Second Quote (Better Discount)" if quote_level == "first_offer" else quote_level
            description_parts.append(f"<p><strong>Quote Level When Declined:</strong> {quote_level_name}</p>")
        
        description_parts.append("<p><strong>Customer Request:</strong> Requested better pricing after being shown quote.</p>")
        
        description = "".join(description_parts)
        
        # Extract individual data fields for database storage
        discount_percent = best_price_info.get("discount_percent")
        unit_price = best_price_info.get("formatted_unit_price")
        total_price = best_price_info.get("formatted_total_price")
        offers_shown_str = ", ".join(offers) if offers else None
        quote_level = selections.get("escalation_quote_level")
        quote_state = selections.get("escalation_quote_state")
        
        # Send request to n8n webhook
        # email field must be b2b@printerpix.co.uk so emails go there
        # Customer's actual email is in the description field and as separate field
        ticket_result = self.freshdesk_service.create_ticket(
            email=freshdesk_email,  # Always use b2b@printerpix.co.uk for email field
            subject="Bulk order quote request",
            description=description,  # Customer email is in description
            product_id=product_id,
            group_id=group_id,
            # Individual data fields for database storage
            customer_name=user_name if user_name else None,
            customer_email=customer_email if customer_email else None,
            product_name=product_name,
            quantity=quantity,
            postcode=postcode if postcode else None,
            region=region,
            fabric=selections.get("fabric"),
            cover=selections.get("cover"),
            type=selections.get("type"),
            size=selections.get("size"),
            pages=selections.get("pages"),
            discount_percent=discount_percent,
            unit_price=unit_price,
            total_price=total_price,
            offers_shown=offers_shown_str,
            quote_level=quote_level,
            quote_state=quote_state
        )
        
        if ticket_result.get("success"):
            logger.info(f"✅ Support ticket request sent successfully to n8n webhook for user {user_id}")
            
            # Send confirmation message to user (without mentioning specific name)
            await self.whatsapp_api.send_message(
                user_id,
                "I understand. I've forwarded your request to our specialist team who can provide the best rate for your bulk order. They'll reach out to you shortly via email."
            )
        else:
            error = ticket_result.get("error", "Unknown error")
            logger.error(f"❌ Failed to send request to n8n webhook for user {user_id}: {error}")
            
            # Still send a message to user even if ticket creation failed
            await self.whatsapp_api.send_message(
                user_id,
                "I understand. I've noted your request and our specialist team will reach out to you shortly via email to provide the best rate for your bulk order."
            )
        
        # Clear bulk ordering state
        self.redis_store.clear_bulk_order_state(user_id)
    
    async def _create_accepted_order_ticket(self, user_id: str, selections: Dict, discount_code: str, offer_type: str) -> None:
        """Create Freshdesk ticket when customer accepts bulk order quote"""
        try:
            # Get product name
            product = selections.get("product", "")
            if product in OTHER_PRODUCTS:
                product_name = OTHER_PRODUCTS[product]["name"]
            elif product in BULK_PRODUCTS:
                product_name = BULK_PRODUCTS[product]["name"]
            else:
                product_name = product.title()
            
            quantity = selections.get("quantity", 0)
            customer_email = selections.get("email", "")
            postcode = selections.get("postcode", "")
            
            # Get pricing information
            price_info = bulk_pricing_service.get_bulk_price_info(
                selections=selections,
                quantity=quantity,
                offer_type=offer_type
            )
            
            # Determine region from postcode (default to UK)
            region = "UK"  # Default
            if postcode:
                region = self.region_lookup_service.get_region_from_postcode(postcode)
            
            # Get product_id and group_id from Supabase
            product_id, group_id = self.region_lookup_service.get_region_ids(region)
            
            # Build email description
            description_parts = []
            description_parts.append(f"<p><strong>Customer wants to proceed with bulk order</strong></p>")
            
            if customer_email:
                description_parts.append(f"<p><strong>Customer Email Address:</strong> {customer_email}</p>")
            else:
                description_parts.append(f"<p><strong>Customer Email Address:</strong> Not provided</p>")
            
            description_parts.append(f"<p><strong>WhatsApp Number:</strong> {user_id}</p>")
            description_parts.append(f"<p><strong>Product:</strong> {product_name}</p>")
            description_parts.append(f"<p><strong>Quantity:</strong> {quantity} units</p>")
            
            # Add selections details
            selections_text = []
            if selections.get("fabric"):
                selections_text.append(f"Fabric: {selections.get('fabric')}")
            if selections.get("cover"):
                selections_text.append(f"Cover: {selections.get('cover')}")
            if selections.get("type"):
                selections_text.append(f"Type: {selections.get('type')}")
            if selections.get("size"):
                selections_text.append(f"Size: {selections.get('size')}")
            if selections.get("pages"):
                selections_text.append(f"Pages: {selections.get('pages')}")
            
            if selections_text:
                description_parts.append(f"<p><strong>Selections:</strong> {', '.join(selections_text)}</p>")
            
            # Add quote details
            if price_info.get("discount_percent"):
                discount = price_info.get("discount_percent", 0)
                description_parts.append(f"<p><strong>Discount Code:</strong> {discount_code}</p>")
                description_parts.append(f"<p><strong>Discount Offered:</strong> {discount:.1f}%</p>")
            
            if price_info.get("formatted_unit_price"):
                description_parts.append(f"<p><strong>Unit Price:</strong> {price_info.get('formatted_unit_price')}</p>")
            
            if price_info.get("formatted_total_price"):
                description_parts.append(f"<p><strong>Total Price:</strong> {price_info.get('formatted_total_price')}</p>")
            
            if postcode:
                description_parts.append(f"<p><strong>Postcode:</strong> {postcode}</p>")
            
            description_parts.append(f"<p><strong>Region:</strong> {region}</p>")
            description_parts.append(f"<p><strong>Status:</strong> Customer accepted quote and wants to proceed with order</p>")
            
            description = "".join(description_parts)
            
            # Send request to n8n webhook
            freshdesk_email = "b2b@printerpix.co.uk"
            ticket_result = self.freshdesk_service.create_ticket(
                email=freshdesk_email,
                subject="Bulk order - Customer wants to proceed",
                description=description,
                product_id=product_id,
                group_id=group_id,
                customer_name=None,
                customer_email=customer_email if customer_email else None,
                product_name=product_name,
                quantity=quantity,
                postcode=postcode if postcode else None,
                region=region,
                fabric=selections.get("fabric"),
                cover=selections.get("cover"),
                type=selections.get("type"),
                size=selections.get("size"),
                pages=selections.get("pages"),
                discount_percent=price_info.get("discount_percent"),
                unit_price=price_info.get("formatted_unit_price"),
                total_price=price_info.get("formatted_total_price"),
                offers_shown=None,
                quote_level=None,
                quote_state=None
            )
            
            if ticket_result.get("success"):
                logger.info(f"✅ Created Freshdesk ticket for accepted bulk order from user {user_id}")
            else:
                error = ticket_result.get("error", "Unknown error")
                logger.error(f"❌ Failed to create Freshdesk ticket for accepted order: {error}")
        except Exception as e:
            logger.error(f"❌ Error creating Freshdesk ticket for accepted order: {e}", exc_info=True)
    
    async def _handoff_to_agent(self, user_id: str, selections: Dict) -> None:
        """Legacy handoff method - now redirects to escalation"""
        await self._escalate_to_support(user_id, selections)
    
    async def _handle_delivery_time_question(self, user_id: str) -> None:
        """Handle delivery time question using RAG"""
        # Send delivery time info from knowledge base
        # This information is available in our FAQ and policies
        
        delivery_info = """Here's our delivery time information:

*Standard Shipping*: 5-7 business days
*Express Shipping*: 3-5 business days  
*Rush Shipping*: 1-2 business days

Plus 1-2 business days for production.

For bulk orders: Typically 7-10 business days for production plus shipping. Rush options are available!

Need a specific date? Choose rush shipping and contact us with your required date - we'll do our best to accommodate! 🚚"""
        
        await self.whatsapp_api.send_message(user_id, delivery_info)
        
        # Clear bulk ordering state so user can continue conversation or ask follow-up questions
        self.redis_store.clear_bulk_order_state(user_id)
        self.redis_store.clear_last_message_sent(user_id)


# Global instance will be created in main handler
bulk_ordering_service = None

def get_bulk_ordering_service(whatsapp_api: WhatsAppAPI) -> BulkOrderingService:
    """Get or create bulk ordering service instance"""
    global bulk_ordering_service
    if bulk_ordering_service is None:
        bulk_ordering_service = BulkOrderingService(whatsapp_api)
    return bulk_ordering_service

