import os
from dotenv import load_dotenv

load_dotenv()

# LLM Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# WhatsApp Business API Settings
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
BUSINESS_ID = os.getenv("BUSINESS_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")

# Database Settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://botuser:changeme123@localhost:5432/whatsapp_bot")

# ChromaDB Settings
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Bot Settings
BOT_NAME = os.getenv("BOT_NAME", "RAG Assistant")
MAX_CONTEXT_LENGTH = 4000
RETRIEVAL_TOP_K = 3
PORT = int(os.getenv("PORT", 8000))

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Security
APP_SECRET = os.getenv("APP_SECRET")  # For webhook signature verification
ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",") if os.getenv("ALLOWED_IPS") else []
ENABLE_WEBHOOK_VERIFICATION = os.getenv("ENABLE_WEBHOOK_VERIFICATION", "true").lower() == "true"
