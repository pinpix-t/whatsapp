"""
WhatsApp RAG Bot - Production Version
Uses WhatsApp Business Cloud API with webhook architecture
"""

import uvicorn
import logging
from config.settings import PORT, BOT_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the webhook server"""
    logger.info(f"🚀 Starting {BOT_NAME}...")
    logger.info(f"📡 Webhook server will listen on port {PORT}")
    logger.info("="*60)
    logger.info("⚙️  Configuration:")
    logger.info("  - WhatsApp Business Cloud API: ENABLED")
    logger.info("  - RAG Vector Store: ChromaDB")
    logger.info("  - LLM: OpenAI GPT-3.5-turbo")
    logger.info("="*60)
    logger.info("\n📋 Next steps:")
    logger.info("1. Make sure your .env file has OPENAI_API_KEY set")
    logger.info("2. Run 'python ingest_documents.py' to load your knowledge base")
    logger.info("3. Expose this server to the internet (ngrok, etc.)")
    logger.info("4. Configure webhook URL in Meta Developer Console")
    logger.info(f"   Webhook URL: https://your-domain.com/webhook")
    logger.info(f"   Verify Token: (check your .env file)")
    logger.info("="*60 + "\n")

    # Start the FastAPI webhook server
    uvicorn.run(
        "api.webhook:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
