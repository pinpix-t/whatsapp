# WhatsApp Bot Setup Checklist 📋

## Prerequisites - What You Need Before Running

### 1️⃣ **Meta/WhatsApp Business Setup** ✅
You need these from [Meta Business Platform](https://business.facebook.com):

- [ ] **WhatsApp Business Account** - Already created
- [ ] **Phone Number ID**: `807987205737263` (Already in .env)
- [ ] **Business ID**: `1338118384582683` (Already in .env)
- [ ] **Access Token**: Get a permanent one (current token may expire)
  - Go to: Meta Business Suite → WhatsApp → API Setup → Access Tokens
  - Generate a permanent system user token (not temporary 24hr token)

### 2️⃣ **API Keys** 🔑

#### **WhatsApp Access Token** (CRITICAL)
```bash
# Current token in .env - may expire!
WHATSAPP_TOKEN=your_permanent_token_here

# To get permanent token:
1. Go to: https://business.facebook.com
2. Navigate to: WhatsApp → API Setup
3. Create System User (if not exists)
4. Generate Permanent Token with permissions:
   - whatsapp_business_messaging
   - whatsapp_business_management
```

#### **OpenAI API Key** ✅
```bash
# Already configured in .env
OPENAI_API_KEY=sk-proj-...
```

### 3️⃣ **Webhook Configuration** 🔗

You need to configure the webhook URL in Meta Business:

1. **For Local Development (using ngrok):**
```bash
# Install ngrok
brew install ngrok  # Mac
# or download from: https://ngrok.com

# Start ngrok tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

2. **Configure in Meta Business:**
- Go to: WhatsApp → Configuration → Webhooks
- Set Callback URL: `https://your-domain.com/webhook` or ngrok URL
- Verify Token: `my_secure_verify_token_12345` (matches .env)
- Subscribe to fields:
  - [x] messages
  - [x] messaging_postbacks
  - [x] messaging_optins
  - [x] message_status

### 4️⃣ **Software Requirements** 💻

- [ ] **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- [ ] **Python 3.11+** (if running without Docker)
- [ ] **Git** (already installed)

### 5️⃣ **Environment Variables** (.env)

Create/verify `.env` file with:

```env
# WhatsApp Configuration (REQUIRED)
WHATSAPP_TOKEN=<your_permanent_access_token>
PHONE_NUMBER_ID=807987205737263
BUSINESS_ID=1338118384582683
WEBHOOK_VERIFY_TOKEN=my_secure_verify_token_12345

# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=<your_openai_api_key>

# ChromaDB Configuration (OPTIONAL - has defaults)
CHROMA_DB_PATH=./chroma_db

# Bot Configuration (OPTIONAL - has defaults)
BOT_NAME=PrinterPix Support Assistant
PORT=8000

# Redis Configuration (OPTIONAL - Docker handles this)
REDIS_HOST=redis
REDIS_PORT=6379

# PostgreSQL Configuration (OPTIONAL - Docker handles this)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=whatsapp_bot
POSTGRES_USER=botuser
POSTGRES_PASSWORD=securepassword123
```

## Quick Setup Steps

### Step 1: Clone & Navigate
```bash
cd /Users/tejas/whatsapp
```

### Step 2: Verify Docker is Running
```bash
docker --version
# Should show: Docker version 2x.x.x or higher

# Start Docker Desktop if not running
open -a Docker  # Mac
```

### Step 3: Update Access Token
```bash
# Edit .env file
nano .env

# Update line 5 with permanent token:
WHATSAPP_TOKEN=your_permanent_token_here
```

### Step 4: Start the Bot
```bash
# Clean start (recommended first time)
docker-compose down -v
docker-compose up -d --build

# Check it's running
docker-compose ps
```

### Step 5: Configure Webhook (Production)
1. Get your public URL (or use ngrok for testing)
2. Set webhook in Meta Business Platform
3. Verify webhook is working:
```bash
curl http://localhost:8000/webhook
```

### Step 6: Test the Bot
1. Send a WhatsApp message to your business number
2. Check logs: `docker-compose logs -f app`
3. You should see the message being processed

## Verification Checklist

Run these commands to verify everything is set up:

```bash
# 1. Check Docker is running
docker ps

# 2. Check environment variables are loaded
docker-compose config | grep WHATSAPP_TOKEN

# 3. Check bot health
curl http://localhost:8000/health

# 4. Check webhook is accessible
curl http://localhost:8000/webhook

# 5. View logs for any errors
docker-compose logs app | grep ERROR
```

## Common Setup Issues

### ❌ **"Token Expired" Error**
- Get a permanent token from Meta Business Platform
- Update .env file
- Restart: `docker-compose down && docker-compose up -d --build`

### ❌ **"Webhook Not Verified"**
- Ensure WEBHOOK_VERIFY_TOKEN in .env matches Meta config
- Check ngrok is running (if using locally)
- Verify URL is HTTPS (not HTTP)

### ❌ **"Port Already in Use"**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or change port in .env
PORT=8001
```

### ❌ **"Docker Not Running"**
```bash
# Start Docker Desktop
open -a Docker  # Mac

# Wait for Docker to start, then retry
docker-compose up -d
```

## Ready to Go? 🚀

Once everything above is checked:
```bash
# Start the bot
docker-compose up -d

# Monitor logs
docker-compose logs -f app

# Your bot is ready when you see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Need These From Meta:
1. ✅ Phone Number ID: `807987205737263` (you have this)
2. ✅ Business ID: `1338118384582683` (you have this)
3. ⚠️  **Permanent Access Token** (current may expire - get permanent one)
4. ⚠️  **Webhook URL Configuration** (set in Meta Business Platform)

---

**Note**: Your current token might be temporary. Get a permanent system user token to avoid daily renewals!