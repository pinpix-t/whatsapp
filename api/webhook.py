from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import WEBHOOK_VERIFY_TOKEN
from bot.whatsapp_api import WhatsAppAPI
from bot.llm_handler import LLMHandler
from rag.vector_store import VectorStore
from utils.error_handler import register_error_handlers
from database.redis_store import redis_store
import asyncio
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WhatsApp RAG Bot",
    version="1.0.0",
    description="Production-ready WhatsApp bot with RAG capabilities"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Initialize components
vector_store = VectorStore()
whatsapp_api = WhatsAppAPI()
llm_handler = LLMHandler(vector_store, whatsapp_api)

# Initialize bulk ordering service
from services.bulk_ordering import get_bulk_ordering_service
bulk_ordering_service = get_bulk_ordering_service(whatsapp_api)

# Auto-ingest documents if vector store is empty (for Railway deployment)
import os
from pathlib import Path

def check_and_ingest_documents():
    """Check if vector store is empty and ingest documents if needed"""
    try:
        # Try to retrieve from vector store - if empty or error, ingest
        try:
            test_results = vector_store.retrieve("test query", k=1)
            if test_results and len(test_results) > 0:
                logger.info("✓ Vector store already has data")
                return
        except:
            pass  # Vector store is empty, continue to ingestion
        
        logger.info("📚 Vector store is empty, ingesting documents...")
        
        # Check if documents directory exists
        docs_dir = Path("./data/documents")
        if docs_dir.exists():
            # Filter out .gitkeep and .DS_Store
            doc_files = [f for f in docs_dir.glob("*.*") if f.name not in ['.gitkeep', '.DS_Store']]
            
            if doc_files:
                logger.info(f"📄 Found {len(doc_files)} document files to ingest")
                chunks_added = vector_store.add_documents(str(docs_dir))
                logger.info(f"✅ Successfully ingested {chunks_added} document chunks into vector store")
            else:
                logger.warning("⚠️ No document files found in data/documents/ - vector store will be empty")
        else:
            logger.warning("⚠️ data/documents/ directory not found - vector store will be empty")
    except Exception as e:
        logger.error(f"❌ Error checking/ingesting documents: {e}", exc_info=True)

# Run on startup
check_and_ingest_documents()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "WhatsApp RAG Bot"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Webhook verification endpoint for WhatsApp
    Meta will call this to verify your webhook
    """
    # Extract query parameters
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logger.info(f"Webhook verification request: mode={mode}, token={token}")

    # Verify token and mode
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        logger.info("✓ Webhook verified successfully")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        logger.error("❌ Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receive incoming WhatsApp messages
    This is called by WhatsApp when someone sends a message
    """
    # CRITICAL: Log FIRST before anything else to confirm POST requests arrive
    logger.info("=" * 80)
    logger.info("🚨 POST /webhook CALLED - Webhook endpoint hit!")
    logger.info("=" * 80)
    
    try:
        # Log raw body first to see if requests are arriving
        body_bytes = await request.body()
        logger.info(f"📦 RAW webhook body received: {len(body_bytes)} bytes")
        
        if len(body_bytes) == 0:
            logger.warning("⚠️ Empty body received!")
            return {"status": "ok"}
        
        import json
        body = json.loads(body_bytes)
        logger.info(f"📦 Webhook parsed successfully")
        logger.info(f"📦 Body keys: {list(body.keys())}")
        logger.info(f"📦 Full body: {body}")

        # Process webhook data directly (no validation needed for demo)
        # webhook_data = WhatsAppWebhook(**body)

        # Extract message data
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ok"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ok"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Could be a status update, not a message
            return {"status": "ok"}

        # Process each message
        for message in messages:
            message_data = {
                "from": message.get("from"),
                "message_id": message.get("id"),
                "timestamp": message.get("timestamp"),
                "type": message.get("type")
            }

            # Handle text messages
            if message_data["type"] == "text":
                message_data["text"] = message.get("text", {}).get("body", "")
                # Process message asynchronously
                asyncio.create_task(process_message(message_data))

            # Handle interactive messages (buttons and lists)
            elif message_data["type"] == "interactive":
                interactive = message.get("interactive", {})
                interactive_type = interactive.get("type")
                
                if interactive_type == "button_reply":
                    button_id = interactive.get("button_reply", {}).get("id")
                    message_data["button_id"] = button_id
                    message_data["interactive_type"] = "button"
                    logger.info(f"🔘 Button clicked: {button_id}")
                    # Process interactive message asynchronously
                    asyncio.create_task(process_message(message_data))
                
                elif interactive_type == "list_reply":
                    list_id = interactive.get("list_reply", {}).get("id")
                    message_data["list_id"] = list_id
                    message_data["interactive_type"] = "list"
                    logger.info(f"📋 List selection: {list_id}")
                    # Process interactive message asynchronously
                    asyncio.create_task(process_message(message_data))

            else:
                logger.info(f"ℹ️ Unsupported message type: {message_data['type']}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}")
        # Return 200 to WhatsApp but log the error
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": "Webhook processing failed"}
        )


async def process_message(message_data: dict):
    """
    Process incoming message and generate response
    Runs asynchronously to avoid blocking the webhook
    """
    start_time = time.time()

    try:
        from_number = message_data["from"]
        message_id = message_data["message_id"]
        text = message_data.get("text", "")
        interactive_type = message_data.get("interactive_type")
        button_id = message_data.get("button_id")
        list_id = message_data.get("list_id")

        logger.info(f"\n{'='*60}")
        logger.info(f"📨 Processing message from {from_number}")
        logger.info(f"Type: {message_data.get('type')}")
        logger.info(f"Interactive Type: {interactive_type}")
        logger.info(f"Text: {text}")
        logger.info(f"Button ID: {button_id}")
        logger.info(f"List ID: {list_id}")

        # Mark message as read (async, non-blocking)
        await whatsapp_api.mark_message_as_read(message_id)

        # Handle interactive messages (buttons/lists)
        if interactive_type in ["button", "list"]:
            selection_id = button_id or list_id
            
            # Check if it's a welcome menu button
            if selection_id in ["btn_faq", "btn_order", "btn_bulk"]:
                if selection_id == "btn_bulk":
                    # Start bulk ordering flow
                    logger.info("🛒 Starting bulk ordering flow")
                    await bulk_ordering_service.start_bulk_ordering(from_number)
                elif selection_id == "btn_faq":
                    # General FAQ - continue normal flow
                    logger.info("❓ FAQ selected - continuing normal flow")
                    await whatsapp_api.send_message(
                        from_number,
                        "I'm here to help with any questions! Ask me anything about our products, policies, or services. 😊"
                    )
                elif selection_id == "btn_order":
                    # Order questions
                    logger.info("📦 Order questions selected")
                    await whatsapp_api.send_message(
                        from_number,
                        "I can help with order tracking, delivery status, returns, and any order-related questions. What would you like to know? 📦"
                    )
            else:
                # Handle bulk ordering interactive responses
                logger.info(f"🛒 Processing bulk ordering selection: {selection_id}")
                await bulk_ordering_service.handle_interactive_response(from_number, selection_id, list_id)
        
        # Handle text messages
        elif text:
            text_lower = text.lower().strip()
            
            # Check for end/restart/cancel commands
            end_commands = ['restart', 'reset', 'cancel', 'end', 'stop', 'exit', 'start over', 'new order', 'bye']
            if any(cmd in text_lower for cmd in end_commands):
                # Clear bulk ordering state if exists
                bulk_state = redis_store.get_bulk_order_state(from_number)
                bulk_ended = False
                
                if bulk_state:
                    redis_store.clear_bulk_order_state(from_number)
                    bulk_ended = True
                    logger.info(f"🔄 User {from_number} ended bulk ordering flow")
                
                # Clear conversation history (normal conversations)
                redis_store.clear_conversation(from_number)
                logger.info(f"🔄 User {from_number} cleared conversation history")
                
                # Send appropriate goodbye message
                if bulk_ended:
                    await whatsapp_api.send_message(
                        from_number,
                        "Got it! I've reset your bulk ordering and cleared our conversation. Feel free to start fresh anytime. 👋"
                    )
                else:
                    await whatsapp_api.send_message(
                        from_number,
                        "Goodbye! I've cleared our conversation. Feel free to reach out anytime if you need help. 👋"
                    )
                return
            
            # Check if user is in bulk ordering flow
            bulk_state = redis_store.get_bulk_order_state(from_number)
            
            if bulk_state:
                current_state = bulk_state.get("state")
                
                if current_state == "asking_quantity":
                    # User is providing quantity
                    logger.info("🔢 Processing quantity input")
                    await bulk_ordering_service.handle_quantity(from_number, text)
                elif current_state == "asking_email":
                    # User is providing email
                    logger.info("📧 Processing email input")
                    await bulk_ordering_service.handle_email(from_number, text)
                elif current_state == "asking_postcode":
                    # User is providing postcode
                    logger.info("📮 Processing postcode input")
                    await bulk_ordering_service.handle_postcode(from_number, text)
                elif current_state == "asking_name_for_escalation":
                    # User is providing name for escalation (optional)
                    logger.info("👤 Processing name input for escalation")
                    await bulk_ordering_service.handle_name_for_escalation(from_number, text)
                elif current_state in ["offering_first_discount", "offering_second_discount", "offering_best_available"]:
                    # User is responding to discount offer - check for rejection words
                    logger.info(f"💰 Processing discount response in state: {current_state}")
                    await bulk_ordering_service.handle_discount_text_response(from_number, text, current_state)
                elif current_state == "asking_decline_reason":
                    # User is responding to decline reason question
                    logger.info("❓ Processing decline reason response")
                    await bulk_ordering_service.handle_decline_reason_text_response(from_number, text)
                else:
                    # User is in bulk flow but sent unexpected text
                    logger.info("⚠️ User in bulk flow sent text - asking to continue")
                    await whatsapp_api.send_message(
                        from_number,
                        "Please use the buttons or select from the list to continue with your bulk order. If you need to start over, type 'restart'."
                    )
            else:
                # Normal text message - process with LLM
                # Send typing indicator immediately for user feedback
                await whatsapp_api.send_typing_indicator(from_number)
                
                logger.info("🤖 Generating response...")
                response = await llm_handler.generate_response(
                    user_id=from_number,
                    message=text
                )

                # Send response back (if not None - buttons might have been sent)
                if response:
                    logger.info(f"📤 Sending response: {response[:100]}...")
                    await whatsapp_api.send_message(from_number, response)

        duration = time.time() - start_time
        logger.info(f"✅ Successfully processed message from {from_number} in {duration:.2f}s")
        logger.info(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}", exc_info=True)

        # Try to send error message to user
        try:
            await whatsapp_api.send_message(
                message_data["from"],
                "Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass


@app.get("/test-vector-store")
async def test_vector_store():
    """Test endpoint to check if vector store has data"""
    try:
        # Try to retrieve documents
        results = vector_store.retrieve("products", k=3)
        
        return {
            "vector_store_status": "loaded" if results else "empty",
            "documents_found": len(results) if results else 0,
            "sample_docs": [doc.page_content[:200] for doc in results[:2]] if results else []
        }
    except Exception as e:
        return {
            "vector_store_status": "error",
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Detailed health check with dependency verification"""
    import redis
    from config.settings import REDIS_URL, OPENAI_API_KEY

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }

    # Check Vector Store
    try:
        if vector_store.vector_store:
            health_status["components"]["vector_store"] = "healthy"
        else:
            health_status["components"]["vector_store"] = "not_initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["vector_store"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis
    try:
        redis_client = redis.from_url(REDIS_URL, socket_connect_timeout=2)
        redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check OpenAI API Key
    if OPENAI_API_KEY:
        health_status["components"]["openai"] = "configured"
    else:
        health_status["components"]["openai"] = "not_configured"
        health_status["status"] = "unhealthy"

    # Check WhatsApp API
    try:
        if whatsapp_api.token and whatsapp_api.phone_number_id:
            health_status["components"]["whatsapp_api"] = "configured"
        else:
            health_status["components"]["whatsapp_api"] = "not_configured"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["components"]["whatsapp_api"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


if __name__ == "__main__":
    import uvicorn
    from config.settings import PORT

    logger.info(f"🚀 Starting WhatsApp RAG Bot on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
