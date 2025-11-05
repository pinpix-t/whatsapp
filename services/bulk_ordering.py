"""
Bulk Ordering Service
Handles the complete bulk ordering flow from product selection to discount codes
"""

import logging
import re
from typing import Dict, Optional, Tuple
from config.bulk_products import (
    BULK_PRODUCTS, DISCOUNT_CODES, PRODUCT_SELECTION_LIST, PRODUCT_URLS, HOMEPAGE_URL,
    OTHER_PRODUCTS, OTHER_PRODUCTS_LIST, PRICE_POINT_MAPPING
)
from services.bulk_pricing import bulk_pricing_service
from database.redis_store import redis_store
from bot.whatsapp_api import WhatsAppAPI

logger = logging.getLogger(__name__)


class BulkOrderingService:
    """Service for handling bulk ordering conversations"""
    
    def __init__(self, whatsapp_api: WhatsAppAPI):
        self.whatsapp_api = whatsapp_api
        self.redis_store = redis_store
    
    async def start_bulk_ordering(self, user_id: str) -> None:
        """Start the bulk ordering flow - show product selection"""
        # Reset/clear any existing state first
        self.redis_store.clear_bulk_order_state(user_id)
        
        # Set new state
        self.redis_store.set_bulk_order_state(
            user_id,
            "selecting_product",
            {"selections": {}, "discount_offers": []}
        )
        
        # Send product selection list
        sections = [{"rows": PRODUCT_SELECTION_LIST}]
        await self.whatsapp_api.send_list_message(
            to=user_id,
            body_text="Welcome to Bulk Ordering 👋 I'll get you a quick quote.\n\nWhich product are you interested in?",
            button_text="Choose Product",
            sections=sections
        )
    
    def end_bulk_ordering(self, user_id: str) -> None:
        """End bulk ordering flow and clear state"""
        self.redis_store.clear_bulk_order_state(user_id)
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
        
        # Handle product selection
        if current_state == "selecting_product":
            # Handle Other product item selection (e.g., "other_wall_calendar")
            if button_id.startswith("other_") or list_id and list_id.startswith("other_"):
                selection_id = button_id or list_id
                other_product = selection_id.replace("other_", "")
                selections["product"] = other_product
                selections["is_other"] = True
                # Other products skip questions - go straight to quantity
                self.redis_store.set_bulk_order_state(
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
                    await self.whatsapp_api.send_list_message(
                        to=user_id,
                        body_text="Which product are you interested in?",
                        button_text="Choose Product",
                        sections=sections
                    )
                    # Keep state as selecting_product, waiting for other product selection
                    return "other_product_list_shown"
                
                # Regular product (blankets, canvas, etc.)
                selections["product"] = product
                self.redis_store.set_bulk_order_state(
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
        
        # Handle discount code acceptance/rejection
        elif current_state in ["offering_first_discount", "offering_second_discount"]:
            if button_id == "discount_accept":
                await self._handle_discount_acceptance(user_id, current_state)
                return "discount_accepted"
            elif button_id == "discount_reject":
                await self._handle_discount_rejection(user_id, current_state)
                return "discount_rejected"
        
        # Handle rejection reasons (after showing buttons)
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
            if question_config["component"] == "buttons":
                buttons = [{"id": opt["id"], "title": opt["title"]} for opt in question_config["options"]]
                await self.whatsapp_api.send_interactive_buttons(
                    to=user_id,
                    body_text=question_config["question"],
                    buttons=buttons
                )
            elif question_config["component"] == "list":
                sections = [{"rows": question_config["options"]}]
                await self.whatsapp_api.send_list_message(
                    to=user_id,
                    body_text=question_config["question"],
                    button_text="Choose Option",
                    sections=sections
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
                    self.redis_store.set_bulk_order_state(
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
        self.redis_store.set_bulk_order_state(
            user_id,
            "asking_quantity",
            {"selections": self.redis_store.get_bulk_order_state(user_id).get("selections", {}), "discount_offers": []}
        )
        
        await self.whatsapp_api.send_message(
            user_id,
            "How many units would you like to order?"
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
            state_data = self.redis_store.get_bulk_order_state(user_id)
            selections = state_data.get("selections", {})
            selections["quantity"] = quantity
            
            # Update state and ask for email
            self.redis_store.set_bulk_order_state(
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
        """Ask user for their email address"""
        message = """To send your discount code, we just need one more step: your email address. 👇️

Simply send it as a message in this chat.

_Please avoid quotation marks, emojis and the like - just the email. 🙏_"""
        
        await self.whatsapp_api.send_message(user_id, message)
    
    async def handle_email(self, user_id: str, email_text: str) -> None:
        """Handle email input and optionally ask for postcode"""
        email = email_text.strip()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            await self.whatsapp_api.send_message(
                user_id,
                "Please enter a valid email address. For example: yourname@example.com"
            )
            return
        
        # Store email
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        selections["email"] = email
        
        # Update state and ask for postcode (optional)
        self.redis_store.set_bulk_order_state(
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
        
        await self.whatsapp_api.send_message(user_id, message)
    
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
        
        # Now offer discount
        await self._offer_first_discount(user_id, selections)
    
    async def _offer_first_discount(self, user_id: str, selections: Dict) -> None:
        """Offer first discount code with pricing (shows WORSE discount first)"""
        # Show the worse discount first (second_offer = price point B)
        discount_code = DISCOUNT_CODES["second_offer"]
        
        # Store offer
        state_data = self.redis_store.get_bulk_order_state(user_id)
        offers = state_data.get("discount_offers", [])
        offers.append("first_offer")
        self.redis_store.set_bulk_order_state(
            user_id,
            "offering_first_discount",
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
        
        # Get pricing information - use second_offer (worse discount) first
        price_info = bulk_pricing_service.get_bulk_price_info(
            selections=selections,
            quantity=quantity,
            offer_type="second_offer"
        )
        
        # Build message with pricing
        if price_info["success"] and price_info["total_price"] is not None:
            # Full pricing available
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units
Unit Price: {price_info["formatted_unit_price"]}
Total Price: {price_info["formatted_total_price"]}
Discount: {price_info["discount_percent"]:.1f}% off

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?"""
        elif price_info["success"] and price_info["discount_percent"] is not None:
            # Discount available but no base price
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units
Discount: {price_info["discount_percent"]:.1f}% off

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?"""
        else:
            # Pricing unavailable
            message = f"""Great! Here's your quick quote:

Product: {product_name}
Quantity: {quantity} units

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Ready to proceed?"""
        
        buttons = [
            {"id": "discount_accept", "title": "Yes, I'll use it"},
            {"id": "discount_reject", "title": "Need better price"}
        ]
        
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons
        )
    
    async def _handle_discount_acceptance(self, user_id: str, current_state: str) -> None:
        """Handle when user accepts discount"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        # Determine correct discount code based on state
        # offering_first_discount = second_offer (worse), offering_second_discount = first_offer (better)
        if current_state == "offering_first_discount":
            discount_code = DISCOUNT_CODES["second_offer"]  # Worse discount shown first
        else:
            discount_code = DISCOUNT_CODES["first_offer"]  # Better discount shown second
        
        # Determine product URL
        product = selections.get("product", "")
        product_url = self._get_product_url(selections)
        
        message = f"""Perfect! Your discount code *{discount_code}* is ready to use on our website.

Visit: {product_url}

Apply the code at checkout. Happy to help with anything else!"""
        
        await self.whatsapp_api.send_message(user_id, message)
        
        # Clear bulk ordering state
        self.redis_store.clear_bulk_order_state(user_id)
    
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
        
        # Check for rejection words
        rejection_words = ['no', 'not happy', 'not satisfied', 'need better', 'better price', 'too high', 'expensive', 'cant afford', 'decline', 'reject', 'pass', 'skip']
        acceptance_words = ['yes', 'accept', 'ok', 'okay', 'sure', 'proceed', 'continue', 'use it', 'i\'ll use', 'take it']
        
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
                "Please use the buttons above to respond. Or type 'No' if you need a better price, or 'Yes' if you'll use the code."
            )
    
    async def _handle_discount_rejection(self, user_id: str, current_state: str) -> None:
        """Handle when user rejects discount"""
        state_data = self.redis_store.get_bulk_order_state(user_id)
        selections = state_data.get("selections", {})
        
        if current_state == "offering_first_discount":
            # User asked for better price - show the BETTER discount (first_offer = price point D)
            quantity = selections.get("quantity", 0)
            
            # Get the better discount (first_offer = price point D)
            better_price_info = bulk_pricing_service.get_bulk_price_info(
                selections=selections,
                quantity=quantity,
                offer_type="first_offer"
            )
            
            # Get the worse discount (second_offer = price point B) for comparison logging
            worse_price_info = bulk_pricing_service.get_bulk_price_info(
                selections=selections,
                quantity=quantity,
                offer_type="second_offer"
            )
            
            better_discount = better_price_info.get("discount_percent", 0) or 0
            worse_discount = worse_price_info.get("discount_percent", 0) or 0
            
            # Log what we found for debugging
            logger.info(f"💰 Discount comparison for user {user_id}: Worse (shown first)={worse_discount:.1f}%, Better (offering now)={better_discount:.1f}%")
            
            # Always show the better discount when they ask for better price
            if better_discount > worse_discount:
                logger.info(f"✅ Showing better discount ({better_discount:.1f}%) - was showing {worse_discount:.1f}% before")
                await self._offer_second_discount(user_id, selections)
            else:
                # This shouldn't happen, but handle gracefully
                logger.warning(f"⚠️ Better discount ({better_discount:.1f}%) is not better than worse ({worse_discount:.1f}%) - showing anyway")
                await self._offer_second_discount(user_id, selections)
        elif current_state == "offering_second_discount" or current_state == "offering_best_available":
            # Handoff to human agent
            await self._handoff_to_agent(user_id, selections)
    
    async def _offer_second_discount(self, user_id: str, selections: Dict) -> None:
        """Offer better discount code (first_offer = price point D) when user asks for better price"""
        # Show the better discount (first_offer = price point D)
        discount_code = DISCOUNT_CODES["first_offer"]
        
        # Store offer
        state_data = self.redis_store.get_bulk_order_state(user_id)
        offers = state_data.get("discount_offers", [])
        offers.append("second_offer")
        self.redis_store.set_bulk_order_state(
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
        
        # Build message with pricing
        if price_info["success"] and price_info["total_price"] is not None:
            # Full pricing available
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units
Unit Price: {price_info["formatted_unit_price"]}
Total Price: {price_info["formatted_total_price"]}
Discount: {price_info["discount_percent"]:.1f}% off

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?"""
        elif price_info["success"] and price_info["discount_percent"] is not None:
            # Discount available but no base price
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units
Discount: {price_info["discount_percent"]:.1f}% off

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?"""
        else:
            # Pricing unavailable
            message = f"""I can extend a better bulk incentive today:

Product: {product_name}
Quantity: {quantity} units

⚠️ Live price is temporarily unavailable.

Use discount code: *{discount_code}* for your bulk order on our website.

Want me to update your pay link?"""

        buttons = [
            {"id": "discount_accept", "title": "Yes, I'll use it"},
            {"id": "discount_reject", "title": "Still too high"}
        ]
        
        await self.whatsapp_api.send_interactive_buttons(
            to=user_id,
            body_text=message,
            buttons=buttons
        )
    
    async def _handoff_to_agent(self, user_id: str, selections: Dict) -> None:
        """Handoff to human agent (Talib)"""
        # Get product name (handle Other products)
        product = selections.get("product", "")
        if product in OTHER_PRODUCTS:
            product_name = OTHER_PRODUCTS[product]["name"]
        elif product in BULK_PRODUCTS:
            product_name = BULK_PRODUCTS[product]["name"]
        else:
            product_name = product.title()
        
        quantity = selections.get("quantity", 0)
        email = selections.get("email", "Not provided")
        postcode = selections.get("postcode", "Not provided")
        
        # Create summary for agent
        summary = f"""BULK ORDER LEAD - {user_id}

Product: {product_name}
Quantity: {quantity}
Email: {email}
Postcode: {postcode}
Selections: {selections}

Please contact customer for best rate."""
        
        # Send message to user
        await self.whatsapp_api.send_message(
            user_id,
            "I understand. Let me connect you with our specialist (Talib) who can provide the best rate for your bulk order. They'll reach out to you shortly."
        )
        
        # Log handoff (you can send to database or notification system here)
        logger.info(f"HANDOFF TO AGENT: {summary}")
        
        # Tag in database for Talib (you can implement this with postgres_store)
        # postgres_store.save_analytics_event("bulk_order_handoff", user_id, {"selections": selections})
        
        # Clear bulk ordering state
        self.redis_store.clear_bulk_order_state(user_id)
    
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


# Global instance will be created in main handler
bulk_ordering_service = None

def get_bulk_ordering_service(whatsapp_api: WhatsAppAPI) -> BulkOrderingService:
    """Get or create bulk ordering service instance"""
    global bulk_ordering_service
    if bulk_ordering_service is None:
        bulk_ordering_service = BulkOrderingService(whatsapp_api)
    return bulk_ordering_service

