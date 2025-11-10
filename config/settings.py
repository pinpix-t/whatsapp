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

# Supabase Settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# SQL Server Settings (Azure SQL Database)
SQL_SERVER = os.getenv("SQL_SERVER", "YOUR_SERVER_HOST,1433")
SQL_DATABASE = os.getenv("SQL_DATABASE", "printerpix_gb")
SQL_USER = os.getenv("SQL_USER", "readonly_user")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# Freshdesk Settings
FRESHDESK_API_URL = os.getenv("FRESHDESK_API_URL", "https://printerpix-support.freshdesk.com/api/v2/tickets")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
