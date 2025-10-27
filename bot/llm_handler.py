from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from config.settings import OPENAI_API_KEY, BOT_NAME
from database.redis_store import redis_store
from utils.retry import retry_openai_call
from utils.error_handler import LLMError
from services.order_tracking import order_tracking_service
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMHandler:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY,
            request_timeout=30
        )

        # Use Redis for conversation storage
        self.redis_store = redis_store

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

    @retry_openai_call(max_attempts=2)
    def generate_response(self, user_id: str, message: str):
        """Generate a response - FAST for greetings, detailed for questions"""
        try:
            # Check cache first
            cached_response = self.redis_store.get_cached_response(message)
            if cached_response:
                logger.info("✓ Using cached response")
                return cached_response

            message_lower = message.lower().strip()

            # FAST PATH: Handle greetings without RAG
            greetings = ['hi', 'hello', 'hey', 'hola', 'howdy', 'sup', 'yo', 'greetings', 'hii', 'hellooooo']
            if message_lower in greetings or any(message_lower.startswith(g + ' ') or message_lower == g for g in greetings):
                response = "Hello! Welcome to PrinterPix! How can I help you with your order today?"
                logger.info("✓ Fast greeting response")

            # ORDER TRACKING: Handle order tracking requests
            elif self._is_order_tracking_request(message_lower):
                response = self._handle_order_tracking(user_id, message)
                logger.info("✓ Handled order tracking request")

            # ALL OTHER MESSAGES: Use conversation context and generate proper responses
            else:
                # Get conversation history FIRST (important for context)
                conversation = self.redis_store.get_conversation(user_id)
                history = ""
                if conversation and len(conversation) > 0:
                    recent = conversation[-6:] if len(conversation) >= 6 else conversation
                    history = "\n".join([f"{'Customer' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" for msg in recent])

                # Retrieve context for questions about PrinterPix products/services
                context = ""
                # Expanded keywords to catch more relevant questions
                relevant_keywords = [
                    'order', 'track', 'ship', 'deliver', 'product', 'print', 'photo', 'canvas', 'gift',
                    'mug', 'book', 'calendar', 'card', 'price', 'cost', 'popular', 'best', 'selling',
                    'return', 'refund', 'policy', 'shipping', 'help', 'support', 'question', 'what', 'how',
                    'when', 'where', 'why', 'available', 'have', 'sell', 'offer', 'service'
                ]
                
                if any(word in message_lower for word in relevant_keywords):
                    logger.info(f"Retrieving context for: {message[:50]}...")
                    relevant_docs = self.vector_store.retrieve(message, k=3)
                    if relevant_docs:
                        context = "\n".join([doc.page_content[:300] for doc in relevant_docs])
                        logger.info(f"Retrieved {len(relevant_docs)} relevant documents")

                prompt = self.conversation_prompt.format(
                    message=message,
                    context=context,
                    history=history
                )

                response = self.llm.predict(prompt)
                
                # Validate response to prevent hallucinations
                response = self._validate_response(response, context)
                
                logger.info("✓ Generated conversational response")

            # Save conversation to Redis
            self.redis_store.append_to_conversation(user_id, "user", message)
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
            'track order', 'order tracking', 'my order', 'order info'
        ]
        
        # Check for tracking keywords
        if any(keyword in message_lower for keyword in tracking_keywords):
            return True
            
        # Check if message contains what looks like an order number (8-10 digits)
        order_pattern = r'\b\d{8,10}\b'
        if re.search(order_pattern, message_lower):
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
            logger.error(f"Error in order tracking: {e}")
            if "Invalid order number" in str(e):
                return f"❌ {str(e)}\n\nPlease provide a valid order number (8-10 digits) starting with a country code."
            elif "No tracking information found" in str(e):
                return "📦 No tracking information found for this order number. Please double-check the number or contact support if you need help."
            else:
                return "Sorry, I'm having trouble tracking your order right now. Please try again or contact support at 1-800-PRINTERPIX."

    def _extract_order_number(self, message: str) -> str:
        """Extract order number from message"""
        # Look for 8-10 digit numbers
        order_pattern = r'\b(\d{8,10})\b'
        matches = re.findall(order_pattern, message)
        
        if matches:
            # Return the first match
            return matches[0]
        
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