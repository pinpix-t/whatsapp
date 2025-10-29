from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import WEBHOOK_VERIFY_TOKEN
from bot.whatsapp_api import WhatsAppAPI
from bot.llm_handler import LLMHandler
from rag.vector_store import VectorStore
from utils.error_handler import register_error_handlers
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
llm_handler = LLMHandler(vector_store)
whatsapp_api = WhatsAppAPI()

# Auto-ingest documents if vector store is empty (for Railway deployment)
import os
from pathlib import Path

def check_and_ingest_documents():
    """Check if vector store is empty and ingest documents if needed"""
    try:
        # Check if chroma_db exists and has data
        chroma_db_path = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db"))
        if not chroma_db_path.exists() or not list(chroma_db_path.glob("*.sqlite3")):
            logger.info("📚 Vector store is empty, ingesting documents...")
            
            # Check if documents directory exists
            docs_dir = Path("./data/documents")
            if docs_dir.exists() and list(docs_dir.glob("*.*")):
                chunks_added = vector_store.add_documents(str(docs_dir))
                logger.info(f"✅ Ingested {chunks_added} document chunks")
            else:
                logger.warning("⚠️ No documents found in data/documents/ - vector store will be empty")
        else:
            logger.info("✓ Vector store already has data")
    except Exception as e:
        logger.error(f"❌ Error checking/ingesting documents: {e}")

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

            # Only handle text messages for now
            if message_data["type"] == "text":
                message_data["text"] = message.get("text", {}).get("body", "")

                # Process message asynchronously
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

        logger.info(f"\n{'='*60}")
        logger.info(f"📨 Processing message from {from_number}")
        logger.info(f"Message: {text}")

        # Mark message as read
        whatsapp_api.mark_message_as_read(message_id)

        # Generate response using RAG + LLM
        logger.info("🤖 Generating response...")
        response = llm_handler.generate_response(
            user_id=from_number,
            message=text
        )

        # Send response back
        logger.info(f"📤 Sending response: {response[:100]}...")
        whatsapp_api.send_message(from_number, response)

        duration = time.time() - start_time
        logger.info(f"✅ Successfully responded to {from_number} in {duration:.2f}s")
        logger.info(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")

        # Try to send error message to user
        try:
            whatsapp_api.send_message(
                message_data["from"],
                "Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass


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
