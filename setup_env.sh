#!/bin/bash

echo "🔧 Setting up .env file for deployment"
echo "======================================"
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists"
    read -p "Do you want to overwrite it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled. Using existing .env file"
        exit 0
    fi
fi

# Prompt for OpenAI key
echo "📝 Enter your OpenAI API key:"
read -s OPENAI_KEY
echo ""

# Create .env file
cat > .env << EOF
# WhatsApp Business API Configuration (TODO: Add after Meta setup)
WHATSAPP_TOKEN=YOUR_PERMANENT_TOKEN_HERE
PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID_HERE
BUSINESS_ID=YOUR_BUSINESS_ID_HERE
WEBHOOK_VERIFY_TOKEN=my_secure_verify_token_12345

# OpenAI Configuration
OPENAI_API_KEY=${OPENAI_KEY}

# Database Configuration (Will be updated by Railway)
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://botuser:changeme123@localhost:5432/whatsapp_bot

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db

# Bot Configuration
BOT_NAME=PrinterPix Support Assistant
PORT=8000

# Environment
ENVIRONMENT=production
DEBUG=false

# Security
APP_SECRET=printerpix_secret_key_2025
ALLOWED_IPS=
ENABLE_WEBHOOK_VERIFICATION=true
EOF

echo "✅ .env file created!"
echo ""
echo "📋 Next steps:"
echo "1. ✅ Knowledge base ingested"
echo "2. ⏳ Get WhatsApp credentials from Meta"
echo "3. ⏳ Update .env with WhatsApp credentials"
echo "4. ⏳ Deploy to Railway"
echo ""
echo "Run: bash setup_env.sh to update credentials later"

