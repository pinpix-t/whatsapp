from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from config.settings import OPENAI_API_KEY, BOT_NAME
from database.redis_store import redis_store
from utils.retry import retry_openai_call
from utils.error_handler import LLMError
from services.order_tracking import order_tracking_service
from bot.whatsapp_api import WhatsAppAPI
import logging
import re
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMHandler:
    def __init__(self, vector_store, whatsapp_api: WhatsAppAPI = None):
        self.vector_store = vector_store
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY,
            request_timeout=30
        )

        # Use Redis for conversation storage
        self.redis_store = redis_store
        self.whatsapp_api = whatsapp_api

        # Conversational prompt for all non-greeting messages
        self.conversation_prompt = """You are a professional PrinterPix support assistant on WhatsApp. You MUST be 100% accurate and never hallucinate.

Previous conversation:
{history}

Customer: {message}

Context (use this information to answer):
{context}

CRITICAL RULES - NO EXCEPTIONS:
1. ONLY use information that is explicitly provided in the context above
2. NEVER make up, invent, or assume any product information
3. NEVER mention sales numbers, quantities sold, or internal business data
4. If the context doesn't contain the specific information asked for, say "I don't have that specific information in our current database"
5. If asked about products not in context, say "I don't have information about that product. Let me help you find something from our available range"
6. For "best product" questions, you can mention "best selling" if that data is in context
7. For comparisons, say "It depends on what you're looking for" - don't make up pros/cons
8. For regional questions, only answer if regional data is in context
9. NEVER LIE - if you don't know, say you don't know
10. Be professional and helpful
11. Keep responses SHORT (1-3 sentences max)
12. End with a helpful question or offer assistance

Your response:"""

    async def generate_response(self, user_id: str, message: str):
        """Generate a response - FAST for greetings, detailed for questions"""
        try:
            # ALWAYS show welcome buttons for first message (empty conversation)
            # This MUST be checked FIRST before any other logic
            conversation = self.redis_store.get_conversation(user_id)
            is_first_message = not conversation or len(conversation) == 0
            
            logger.info(f"🔍 First message check: conversation={conversation}, is_first={is_first_message}")
            
            # If this is the first message, ALWAYS send welcome buttons regardless of content
            if is_first_message:
                logger.info(f"✅ FIRST MESSAGE DETECTED - Sending welcome buttons for user {user_id}")
                
                # Save user message first
                self.redis_store.append_to_conversation(user_id, "user", message)
                
                # ALWAYS send buttons on first message
                if self.whatsapp_api:
                    try:
                        buttons = [
                            {"id": "btn_create", "title": "Start Creating!"},
                            {"id": "btn_order", "title": "Order Questions"},
                            {"id": "btn_bulk", "title": "Bulk Ordering"}
                        ]
                        await self.whatsapp_api.send_interactive_buttons(
                            to=user_id,
                            body_text="Hi! Welcome to PrinterPix! How can I help?",
                            buttons=buttons
                        )
                        response = None  # Don't send text message, buttons already sent
                        logger.info("✅ Sent welcome buttons for first message - user will see 3 buttons")
                        
                        # Save assistant response as buttons were sent
                        self.redis_store.append_to_conversation(user_id, "assistant", "[Welcome buttons sent]")
                    except Exception as e:
                        logger.error(f"❌ Failed to send interactive buttons: {e}", exc_info=True)
                        # Fallback to text message
                        response = "Hi! Welcome to PrinterPix! How can I help?\n\n1️⃣ Start Creating!\n2️⃣ Order Questions\n3️⃣ Bulk Ordering\n\nReply with 1, 2, or 3!"
                        logger.info("✓ Sent text fallback for first message")
                        self.redis_store.append_to_conversation(user_id, "assistant", response)
                else:
                    response = "Hi! Welcome to PrinterPix! How can I help?\n\n1️⃣ Start Creating!\n2️⃣ Order Questions\n3️⃣ Bulk Ordering\n\nReply with 1, 2, or 3!"
                    self.redis_store.append_to_conversation(user_id, "assistant", response)
                
                return response
            
            # Check cache first (only for non-first messages)
            cached_response = self.redis_store.get_cached_response(message)
            if cached_response:
                logger.info("✓ Using cached response")
                return cached_response

            message_lower = message.lower().strip()
            logger.info(f"🔍 Checking greeting for message: '{message_lower}'")

            # FAST PATH: Handle greetings without RAG - send welcome buttons
            # Check for greeting patterns (handles hi, hii, hiii, hiiii, etc.)
            exact_greetings = ['hi', 'hello', 'hey', 'hola', 'howdy', 'sup', 'yo', 'greetings']
            
            is_greeting = False
            # Check exact matches first
            if message_lower in exact_greetings:
                is_greeting = True
                logger.info(f"✓ Greeting detected: exact match")
            # Check pattern matches for variations (hi+, hello+, hey+)
            # Match: hi, hii, hiii, hiiii, etc. (exactly one h followed by one or more i's)
            elif re.match(r'^hi+$', message_lower):  # hi, hii, hiii, etc.
                is_greeting = True
                logger.info(f"✓ Greeting detected: hi+ pattern")
            # Match: hello, helloo, hellooo, etc. (hello followed by one or more o's)
            elif re.match(r'^hello+$', message_lower):
                is_greeting = True
                logger.info(f"✓ Greeting detected: hello+ pattern")
            # Match: hey, heyy, heyyy, etc.
            elif re.match(r'^hey+$', message_lower):
                is_greeting = True
                logger.info(f"✓ Greeting detected: hey+ pattern")
            # Check if starts with greeting followed by space
            elif any(message_lower.startswith(g + ' ') for g in exact_greetings):
                is_greeting = True
                logger.info(f"✓ Greeting detected: starts with greeting")
            # Also check if message starts with any greeting word (more flexible)
            elif any(message_lower.startswith(g) for g in exact_greetings):
                is_greeting = True
                logger.info(f"✓ Greeting detected: starts with greeting word")
            
            if is_greeting:
                logger.info(f"✅ Processing greeting: '{message_lower}'")
                # Send interactive buttons instead of text
                if self.whatsapp_api:
                    try:
                        buttons = [
                            {"id": "btn_create", "title": "Start Creating!"},
                            {"id": "btn_order", "title": "Order Questions"},
                            {"id": "btn_bulk", "title": "Bulk Ordering"}
                        ]
                        await self.whatsapp_api.send_interactive_buttons(
                            to=user_id,
                            body_text="Hi! Welcome to PrinterPix! How can I help?",
                            buttons=buttons
                        )
                        response = None  # Don't send text message, buttons already sent
                        logger.info("✓ Sent welcome buttons")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to send interactive buttons: {e}. Falling back to text.")
                        # Fallback to text message if buttons fail
                        response = "Hi! Welcome to PrinterPix! How can I help?\n\n1️⃣ Start Creating!\n2️⃣ Order Questions\n3️⃣ Bulk Ordering\n\nReply with 1, 2, or 3!"
                        logger.info("✓ Sent text fallback")
                else:
                    response = "Hello! Welcome to PrinterPix! How can I help you with your order today?"
                    logger.info("✓ Fast greeting response (no WhatsApp API)")

            # VAGUE/UNCLEAR MESSAGES: Send welcome buttons again
            elif message_lower in ['uhm', 'uh', 'um', 'hm', 'hmm', 'what', '?', '??', 'idk', "i don't know", "i dont know"]:
                # User seems unclear, send welcome buttons to guide them
                if self.whatsapp_api:
                    try:
                        buttons = [
                            {"id": "btn_create", "title": "Start Creating!"},
                            {"id": "btn_order", "title": "Order Questions"},
                            {"id": "btn_bulk", "title": "Bulk Ordering"}
                        ]
                        await self.whatsapp_api.send_interactive_buttons(
                            to=user_id,
                            body_text="Hi! Welcome to PrinterPix! How can I help?",
                            buttons=buttons
                        )
                        response = None
                        logger.info("✓ Sent welcome buttons for vague message")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to send interactive buttons: {e}. Falling back to text.")
                        response = "Hi! Welcome to PrinterPix! How can I help?\n\n1️⃣ Start Creating!\n2️⃣ Order Questions\n3️⃣ Bulk Ordering\n\nReply with 1, 2, or 3!"
                else:
                    response = "Hi! Welcome to PrinterPix! How can I help?\n\n1️⃣ Start Creating!\n2️⃣ Order Questions\n3️⃣ Bulk Ordering\n\nReply with 1, 2, or 3!"

            # ORDER TRACKING: Handle order tracking requests
            elif self._is_order_tracking_request(message_lower):
                response = self._handle_order_tracking(user_id, message)
                logger.info("✓ Handled order tracking request")

            # ALL OTHER MESSAGES: Use conversation context and generate proper responses
            else:
                # PARALLELIZE: Get conversation history and vector store retrieval at the same time
                logger.info(f"🔍 Retrieving context for: {message[:50]}...")
                
                def get_conversation_sync():
                    """Get conversation history (sync)"""
                    return self.redis_store.get_conversation(user_id)
                
                def get_context_sync():
                    """Retrieve vector store context (sync)"""
                    try:
                        relevant_docs = self.vector_store.retrieve(message, k=3)  # Reduced from 5 to 3 for speed
                        if relevant_docs:
                            context = "\n".join([doc.page_content[:500] for doc in relevant_docs])
                            logger.info(f"✅ Retrieved {len(relevant_docs)} relevant documents ({len(context)} chars)")
                            return context
                        else:
                            logger.warning("⚠️ No documents retrieved - vector store might be empty!")
                            return ""
                    except Exception as e:
                        logger.error(f"❌ Error retrieving from vector store: {e}", exc_info=True)
                        return ""
                
                # Run both operations in parallel using threads
                conversation, context = await asyncio.gather(
                    asyncio.to_thread(get_conversation_sync),
                    asyncio.to_thread(get_context_sync)
                )
                
                # Format history from conversation
                history = ""
                if conversation and len(conversation) > 0:
                    recent = conversation[-6:] if len(conversation) >= 6 else conversation
                    history = "\n".join([f"{'Customer' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" for msg in recent])

                prompt = self.conversation_prompt.format(
                    message=message,
                    context=context,
                    history=history
                )

                # Use async LLM call
                response = await self.llm.ainvoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Validate response to prevent hallucinations
                response_text = self._validate_response(response_text, context)
                response = response_text
                
                logger.info("✓ Generated conversational response")

            # Save conversation to Redis (only if response is not None)
            self.redis_store.append_to_conversation(user_id, "user", message)
            if response is not None:
                self.redis_store.append_to_conversation(user_id, "assistant", response)
                # Cache response
                self.redis_store.cache_response(message, response, ttl=3600)

            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Fallback response
            return "Sorry, I'm having trouble right now. Please try again or call us at 1-800-PRINTERPIX for immediate help!"

    def _is_order_tracking_request(self, message_lower: str) -> bool:
        """Check if the message is about order tracking"""
        tracking_keywords = [
            'track', 'tracking', 'order status', 'where is my order',
            'delivery status', 'shipping status', 'order number',
            'track order', 'order tracking', 'my order', 'order info',
            'order nuber', 'ordernumber', 'order no', 'order#'
        ]
        
        # Check for tracking keywords (including common typos)
        if any(keyword in message_lower for keyword in tracking_keywords):
            return True
            
        # Check if message contains what looks like an order number (8-10 digits)
        order_pattern = r'\b\d{8,10}\b'
        if re.search(order_pattern, message_lower):
            return True
        
        # Also check for 7-11 digit numbers (edge cases)
        fallback_pattern = r'\b\d{7,11}\b'
        if re.search(fallback_pattern, message_lower):
            return True
            
        return False

    def _handle_order_tracking(self, user_id: str, message: str) -> str:
        """Handle order tracking requests"""
        try:
            # Extract potential order number from message
            order_number = self._extract_order_number(message)
            
            if order_number:
                # User provided an order number, try to track it
                logger.info(f"Tracking order: {order_number}")
                tracking_data = order_tracking_service.track_order(order_number)
                response = order_tracking_service.format_tracking_response(tracking_data)
                
                # Store the order number in conversation context
                self.redis_store.append_to_conversation(user_id, "system", f"Order tracked: {order_number}")
                
                return response
            else:
                # No order number found, ask for it
                return self._ask_for_order_number()
                
        except Exception as e:
            logger.error(f"Error in order tracking: {e}", exc_info=True)
            error_msg = str(e)
            if "Invalid order number" in error_msg:
                return f"❌ {error_msg}\n\nPlease provide a valid order number (8-10 digits) starting with a country code."
            elif "No tracking information found" in error_msg:
                return "📦 No tracking information found for this order number. Please double-check the number or contact support if you need help."
            elif "Failed to retrieve" in error_msg or "API request failed" in error_msg or "currently unavailable" in error_msg:
                return "⚠️ Sorry, I couldn't reach the tracking system right now. Please try again in a moment, or contact support at 1-800-PRINTERPIX.\n\nIf you have your order confirmation email, you can also check your tracking information there."
            else:
                logger.error(f"Unexpected order tracking error: {error_msg}")
                return f"Sorry, I'm having trouble tracking your order right now. Error: {error_msg[:150]}\n\nPlease try again or contact support at 1-800-PRINTERPIX."

    def _extract_order_number(self, message: str) -> str:
        """Extract order number from message"""
        # Look for 8-10 digit numbers (more flexible - handles numbers anywhere)
        # First try exact pattern
        order_pattern = r'\b(\d{8,10})\b'
        matches = re.findall(order_pattern, message)
        
        if matches:
            # Return the first match
            return matches[0]
        
        # Fallback: look for any sequence of 7-11 digits (handle edge cases)
        fallback_pattern = r'(\d{7,11})'
        fallback_matches = re.findall(fallback_pattern, message)
        
        if fallback_matches:
            # Filter to valid range
            for match in fallback_matches:
                if 8 <= len(match) <= 10:
                    return match
        
        return None

    def _ask_for_order_number(self) -> str:
        """Ask user for their order number"""
        return "📦 Sure! Just send me your order number and I'll track it for you! 🚚"
    
    def _validate_response(self, response: str, context: str) -> str:
        """Validate response to prevent hallucinations and lying"""
        # Only validate if context is empty or very short (indicating no relevant info found)
        if len(context.strip()) < 50:
            return response  # Let the LLM handle it with its own instructions
        
        # Check for specific hallucination patterns only when context is available
        hallucination_indicators = [
            "393 sold", "units sold", "quantity sold", "sales data",
            "3x3 inch", "1x1 inch", "tiny", "micro", "miniature"
        ]
        
        response_lower = response.lower()
        for indicator in hallucination_indicators:
            if indicator in response_lower and indicator not in context.lower():
                return "I don't have that specific information in our current database. Let me help you find something from our available range."
        
        # If response seems to make up product details not in context
        if "inch" in response_lower and "cm" not in context.lower() and "inch" not in context.lower():
            return "I don't have that specific information in our current database. Let me help you find something from our available range."
            
        return response