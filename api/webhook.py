from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
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

# Include analytics router
from api.analytics import router as analytics_router
app.include_router(analytics_router)

# Include extended analytics endpoints (registers additional routes on same router)
import api.analytics_extended

# Include agent console router
from api.agent_console import router as agent_router
app.include_router(agent_router)

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


async def check_abandoned_conversations():
    """Background task to periodically check for abandoned conversations"""
    from datetime import datetime
    from database.postgres_store import postgres_store
    
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            if not redis_store.client:
                continue
            
            # Scan for all last_message keys
            cursor = 0
            abandoned_count = 0
            
            while True:
                cursor, keys = redis_store.client.scan(cursor, match="last_message:*", count=100)
                
                for key in keys:
                    try:
                        data_str = redis_store.client.get(key)
                        if not data_str:
                            continue
                        
                        last_message = json.loads(data_str)
                        last_time = datetime.fromisoformat(last_message["timestamp"])
                        time_diff = (datetime.utcnow() - last_time).total_seconds()
                        
                        # If > 15 minutes, log abandonment
                        if time_diff > 900:  # 15 minutes = 900 seconds
                            user_id = key.replace("last_message:", "")
                            step_info = last_message.get("step_info", {})
                            
                            # Only track bulk ordering flow
                            if step_info.get("flow") == "bulk_ordering":
                                state_data = redis_store.get_bulk_order_state(user_id)
                                selections = state_data.get("selections", {}) if state_data else {}
                                
                                abandonment_data = {
                                    "flow": step_info.get("flow", "bulk_ordering"),
                                    "state": step_info.get("state", "unknown"),
                                    "last_message": last_message.get("content", ""),
                                    "time_since_last_message_seconds": time_diff,
                                    "selections": selections
                                }
                                
                                postgres_store.save_analytics_event(
                                    event_type="conversation_abandoned",
                                    user_id=user_id,
                                    data=abandonment_data
                                )
                                
                                logger.info(f"📊 Background task: Logged abandonment for {user_id} - stopped at: {step_info.get('state', 'unknown')} (after {time_diff:.0f}s)")
                                abandoned_count += 1
                                
                                # Clear the tracking key after logging
                                redis_store.client.delete(key)
                    except Exception as e:
                        logger.error(f"Error processing abandonment for key {key}: {e}")
                        continue
                
                if cursor == 0:
                    break
            
            if abandoned_count > 0:
                logger.info(f"📊 Background task: Found and logged {abandoned_count} abandoned conversations")
                
        except Exception as e:
            logger.error(f"Error in check_abandoned_conversations background task: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait 1 minute before retrying on error


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    asyncio.create_task(check_abandoned_conversations())
    logger.info("✅ Background task started: check_abandoned_conversations (runs every 5 minutes)")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "WhatsApp RAG Bot"}


@app.get("/agent-console")
async def serve_agent_console():
    """Serve the agent console HTML file"""
    from pathlib import Path
    file_path = Path(__file__).parent.parent / "agent_console.html"
    return FileResponse(file_path)


@app.get("/manager-dashboard")
async def serve_manager_dashboard():
    """Serve the manager dashboard HTML file"""
    from pathlib import Path
    file_path = Path(__file__).parent.parent / "manager_dashboard.html"
    return FileResponse(file_path)


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

            # Handle image messages
            elif message_data["type"] == "image":
                image_data = message.get("image", {})
                message_data["media_id"] = image_data.get("id")
                message_data["mime_type"] = image_data.get("mime_type")
                logger.info(f"📷 Image received: media_id={message_data['media_id']}")
                # Process image message asynchronously
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

        # Check if agent has claimed this conversation
        if redis_store.is_agent_handoff(from_number):
            handoff_info = redis_store.get_agent_handoff(from_number)
            agent_id = handoff_info.get("agent_id", "unknown") if handoff_info else "unknown"
            logger.info(f"🤖 Agent handoff active for {from_number} (claimed by agent {agent_id}), skipping bot response")
            
            # Still store incoming message in database
            from datetime import datetime
            from database.postgres_store import postgres_store
            
            # Determine message content based on type
            message_content = text
            if not message_content and interactive_type:
                message_content = f"[{interactive_type}] {button_id or list_id or ''}"
            if not message_content:
                message_content = f"[{message_data.get('type', 'unknown')} message]"
            
            try:
                postgres_store.save_message(
                    message_id=message_id,
                    from_number=from_number,
                    to_number=None,
                    content=message_content,
                    direction="inbound",
                    message_type=message_data.get("type", "text"),
                    status="received"
                )
            except Exception as e:
                logger.error(f"Error storing message during handoff: {e}")
            
            # Broadcast message to connected agents via SSE
            try:
                from api.agent_console import message_broadcaster
                await message_broadcaster.broadcast(from_number, {
                    "type": "new_message",
                    "user_id": from_number,
                    "message_id": message_id,
                    "content": message_content,
                    "message_type": message_data.get("type", "text"),
                    "direction": "inbound",
                    "timestamp": datetime.utcnow().isoformat(),
                    "interactive_type": interactive_type,
                    "button_id": button_id,
                    "list_id": list_id
                })
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
            
            # Mark message as read but don't generate bot response
            await whatsapp_api.mark_message_as_read(message_id)
            return  # Exit early, don't process with bot

        # Save incoming message to database (for all messages, not just handoff)
        from datetime import datetime
        from database.postgres_store import postgres_store
        
        # Determine message content based on type
        message_content = text
        if not message_content and interactive_type:
            message_content = f"[{interactive_type}] {button_id or list_id or ''}"
        if not message_content:
            message_content = f"[{message_data.get('type', 'unknown')} message]"
        
        try:
            postgres_store.save_message(
                message_id=message_id,
                from_number=from_number,
                to_number=None,
                content=message_content,
                direction="inbound",
                message_type=message_data.get("type", "text"),
                status="received"
            )
        except Exception as e:
            logger.error(f"Error storing incoming message: {e}")
        
        # Check for conversation abandonment (15 minute timeout)
        last_message = redis_store.get_last_message_sent(from_number)
        if last_message:
            last_time = datetime.fromisoformat(last_message["timestamp"])
            time_diff = (datetime.utcnow() - last_time).total_seconds()
            
            if time_diff > 900:  # 15 minutes = 900 seconds
                # Log abandonment event
                step_info = last_message.get("step_info", {})
                state_data = redis_store.get_bulk_order_state(from_number)
                selections = state_data.get("selections", {}) if state_data else {}
                
                abandonment_data = {
                    "flow": step_info.get("flow", "unknown"),
                    "state": step_info.get("state", "unknown"),
                    "last_message": last_message.get("content", ""),
                    "time_since_last_message_seconds": time_diff,
                    "selections": selections
                }
                
                postgres_store.save_analytics_event(
                    event_type="conversation_abandoned",
                    user_id=from_number,
                    data=abandonment_data
                )
                logger.info(f"📊 Logged abandonment for {from_number} - stopped at: {step_info.get('state', 'unknown')} (after {time_diff:.0f}s)")
            
            # Clear last message tracking since user is back
            redis_store.clear_last_message_sent(from_number)

        # Mark message as read (async, non-blocking)
        await whatsapp_api.mark_message_as_read(message_id)

        # Handle interactive messages (buttons/lists)
        if interactive_type in ["button", "list"]:
            selection_id = button_id or list_id
            
            # Check if it's a welcome menu button
            if selection_id in ["btn_create", "btn_order", "btn_bulk"]:
                if selection_id == "btn_bulk":
                    # Start bulk ordering flow
                    logger.info("🛒 Starting bulk ordering flow")
                    await bulk_ordering_service.start_bulk_ordering(from_number)
                elif selection_id == "btn_create":
                    # Start image creation flow
                    logger.info("🎨 Starting image creation flow")
                    from services.image_creation import get_image_creation_service
                    image_creation_service = get_image_creation_service(whatsapp_api)
                    await image_creation_service.start_image_creation(from_number)
                elif selection_id == "btn_order":
                    # Track My Order button
                    logger.info("📦 Track My Order button selected")
                    await whatsapp_api.send_message(
                        from_number,
                        "Sure! Just send me your order number and I'll track it for you! 🚚"
                    )
            else:
                # Handle bulk ordering interactive responses
                logger.info(f"🛒 Processing bulk ordering selection: {selection_id}")
                await bulk_ordering_service.handle_interactive_response(from_number, selection_id, list_id)
        
        # Handle image messages
        elif message_data.get("media_id"):
            media_id = message_data["media_id"]
            logger.info(f"🖼️ Image message detected for {from_number}, media_id: {media_id}")
            
            from services.image_creation import get_image_creation_service
            image_creation_service = get_image_creation_service(whatsapp_api)
            
            # Check if user is in image creation flow
            creation_state = redis_store.get_image_creation_state(from_number)
            logger.info(f"🔍 Image creation state for {from_number}: {creation_state}")
            
            if creation_state:
                logger.info(f"📷 Processing image for user {from_number}")
                await image_creation_service.handle_image(from_number, media_id)
            else:
                # Not in creation flow, prompt to start
                logger.info(f"⚠️ User {from_number} not in image creation state, prompting to start")
                await whatsapp_api.send_message(
                    from_number,
                    "Please click 'Start Creating!' first to begin! 🎨"
                )
        
        # Handle text messages
        elif text:
            text_lower = text.lower().strip()
            
            # Check for end commands (bye, end) - send goodbye and stop
            end_commands = ['bye', 'end', 'goodbye', 'see you', 'farewell']
            if any(cmd in text_lower for cmd in end_commands):
                # Clear bulk ordering state if exists
                bulk_state = redis_store.get_bulk_order_state(from_number)
                if bulk_state:
                    redis_store.clear_bulk_order_state(from_number)
                    redis_store.clear_last_message_sent(from_number)
                    logger.info(f"🔄 User {from_number} ended bulk ordering flow")
                
                # Clear conversation history
                redis_store.clear_conversation(from_number)
                logger.info(f"🔄 User {from_number} cleared conversation history")
                
                # Get user's stored language preference (or default to English)
                user_language = redis_store.get_user_language(from_number)
                language_code = user_language.get("language_code", "en") if user_language else "en"
                
                # Send goodbye message in user's language
                from utils.language_detection import get_goodbye_message
                goodbye_message = get_goodbye_message(language_code)
                await whatsapp_api.send_message(
                    to=from_number,
                    message=goodbye_message
                )
                return  # Don't restart - just end
            
            # Check for restart commands (restart, reset, etc.) - restart flow
            restart_commands = ['restart', 'reset', 'cancel', 'stop', 'exit', 'start over', 'new order']
            if any(cmd in text_lower for cmd in restart_commands):
                # Clear bulk ordering state if exists
                bulk_state = redis_store.get_bulk_order_state(from_number)
                bulk_ended = False
                
                if bulk_state:
                    redis_store.clear_bulk_order_state(from_number)
                    redis_store.clear_last_message_sent(from_number)
                    bulk_ended = True
                    logger.info(f"🔄 User {from_number} ended bulk ordering flow")
                
                # Clear conversation history (normal conversations)
                redis_store.clear_conversation(from_number)
                logger.info(f"🔄 User {from_number} cleared conversation history")
                
                # Get user's stored language preference (or default to English)
                user_language = redis_store.get_user_language(from_number)
                language_code = user_language.get("language_code", "en") if user_language else "en"
                
                # Send welcome message in user's language (bulk ordering flow)
                from utils.language_detection import get_bulk_message
                welcome_message = get_bulk_message(language_code, "welcome_bulk")
                await whatsapp_api.send_message(
                    to=from_number,
                    message=welcome_message
                )
                
                # Automatically start bulk ordering flow
                logger.info(f"🔄 Restarting bulk ordering flow for user {from_number}")
                await bulk_ordering_service.start_bulk_ordering(from_number)
                return
            
            # Check if message is a greeting pattern (should restart flow)
            from utils.language_detection import detect_language_from_greeting
            region, detected_language = detect_language_from_greeting(text)
            if region and detected_language:
                # This is a greeting - treat it like restart
                logger.info(f"🔄 Greeting detected: '{text}' - restarting flow")
                
                # Clear bulk ordering state if exists
                bulk_state = redis_store.get_bulk_order_state(from_number)
                if bulk_state:
                    redis_store.clear_bulk_order_state(from_number)
                    redis_store.clear_last_message_sent(from_number)
                
                # Clear conversation history
                redis_store.clear_conversation(from_number)
                
                # Store language preference
                redis_store.set_user_language(from_number, detected_language, region)
                
                # Send welcome message in detected language (bulk ordering flow)
                from utils.language_detection import get_bulk_message
                welcome_message = get_bulk_message(detected_language, "welcome_bulk")
                await whatsapp_api.send_message(
                    to=from_number,
                    message=welcome_message
                )
                
                # Automatically start bulk ordering flow
                await bulk_ordering_service.start_bulk_ordering(from_number)
                return
            
            # Check for bulk order keywords (before checking if already in flow)
            bulk_order_keywords = ['bulk order', 'new quote', 'get quote', 'start bulk', 'bulk ordering', 'bulk quote']
            is_bulk_request = any(keyword in text_lower for keyword in bulk_order_keywords)
            
            # Check if user is in bulk ordering flow
            bulk_state = redis_store.get_bulk_order_state(from_number)
            
            if bulk_state:
                # Check if this is a request to start a new bulk order
                if is_bulk_request:
                    logger.info(f"🔄 User {from_number} requested new bulk order while already in flow")
                    await whatsapp_api.send_message(
                        from_number,
                        "You're already in a bulk ordering flow. You can finish this one or reply 'restart' to start a new quote."
                    )
                    return
                
                # Check if this is an order tracking or FAQ request - allow it
                is_order_tracking = llm_handler._is_order_tracking_request(text_lower)
                is_faq_request = any(keyword in text_lower for keyword in ['faq', 'help', 'question', 'what', 'how', 'when', 'where', 'why', 'tell me', 'explain'])
                
                if is_order_tracking or is_faq_request:
                    # Allow order tracking and FAQs during bulk flow
                    logger.info(f"✅ Allowing {('order tracking' if is_order_tracking else 'FAQ')} request during bulk flow")
                    await whatsapp_api.send_typing_indicator(from_number)
                    response = await llm_handler.generate_response(
                        user_id=from_number,
                        message=text
                    )
                    if response:
                        await whatsapp_api.send_message(from_number, response)
                    return
                
                current_state = bulk_state.get("state")
                
                if current_state == "asking_name":
                    # User is providing name
                    logger.info("👤 Processing name input")
                    await bulk_ordering_service.handle_name(from_number, text)
                elif current_state == "asking_quantity":
                    # User is providing quantity
                    logger.info("🔢 Processing quantity input")
                    await bulk_ordering_service.handle_quantity(from_number, text)
                else:
                    # User is in bulk flow but sent unexpected text
                    logger.info("⚠️ User in bulk flow sent text - asking to continue")
                    await whatsapp_api.send_message(
                        from_number,
                        "Please use the buttons or select from the list to continue with your bulk order. If you need to start over, type 'restart'.\n\n💡 You can also ask me questions about orders, FAQs, or other topics anytime!"
                    )
            else:
                # Not in bulk flow - check if this is a bulk order request
                if is_bulk_request:
                    logger.info(f"🛒 User {from_number} requested bulk ordering via text")
                    await bulk_ordering_service.start_bulk_ordering(from_number)
                    return
                
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
