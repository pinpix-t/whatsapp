# 🚀 Railway Deployment Guide

## Current Status
✅ Knowledge base ingested (46 document chunks loaded)  
✅ Project structure ready  
⏳ Need .env file with credentials  
⏳ Need to deploy to Railway

---

## Step 1: Create .env File

Run the setup script:
```bash
bash setup_env.sh
```

Enter your OpenAI API key when prompted.

---

## Step 2: Railway Setup

### In Railway Dashboard:

1. **Click "+" or "New"** → Select **"Empty Project"** (already done ✅)

2. **Add Services:**
   - Click **"+ New"** → Select **"Postgres"** 
   - Click **"+ New"** again → Select **"Redis"**
   
3. **Add Your App:**
   - Click **"+ New"** → Select **"Deploy from GitHub repo"**
   - Connect your GitHub account
   - Select this repository
   - Railway will auto-detect Dockerfile

4. **Add Environment Variables:**
   - Go to your app service
   - Click **"Variables"** tab
   - Add these variables:

```
OPENAI_API_KEY=<your_key>
WHATSAPP_TOKEN=<get_from_meta>
PHONE_NUMBER_ID=<get_from_meta>
BUSINESS_ID=<get_from_meta>
WEBHOOK_VERIFY_TOKEN=my_secure_verify_token_12345
BOT_NAME=PrinterPix Support Assistant
PORT=8000
ENVIRONMENT=production
DEBUG=false
APP_SECRET=printerpix_secret_key_2025
CHROMA_DB_PATH=/app/chroma_db

# Supabase Configuration (for bulk pricing discounts)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# SQL Server Configuration (for bulk pricing base prices)
SQL_SERVER=10.20.2.6,1433
SQL_DATABASE=printerpix_gb
SQL_USER=readonly_user
SQL_PASSWORD=Pr!nterp!x@123
```

5. **Connect Databases to App:**
   - In your app service settings
   - Under "Databases" section
   - Railway auto-generates connection URLs
   - These are added as `REDIS_URL` and `DATABASE_URL` automatically

6. **Add Volume for ChromaDB:**
   - Go to your app service
   - Add volume: `chroma_db` → mount at `/app/chroma_db`

---

## Step 3: Set Up Webhook (After WhatsApp Meta Setup)

Once you have WhatsApp credentials:

1. **Copy Railway URL:**
   - Your app URL is shown in Railway dashboard (e.g., `https://your-app.railway.app`)
   
2. **Add to Meta:**
   - Go to Meta Business Platform → WhatsApp → Configuration → Webhooks
   - Set Callback URL: `https://your-app.railway.app/webhook`
   - Set Verify Token: `my_secure_verify_token_12345`
   - Subscribe to: `messages`, `message_status`

3. **Update Railway env vars:**
   - Add the WhatsApp credentials you got from Meta
   
4. **Redeploy:**
   - Railway will auto-redeploy when you update env vars
   - Or manually trigger: Settings → Redeploy

---

## Step 4: Test

1. Send WhatsApp message to your business number
2. Check Railway logs for responses
3. Bot should auto-reply!

---

## Troubleshooting

**Bot not responding?**
- Check Railway logs: Click app service → "Deployments" → View logs
- Verify webhook is configured correctly in Meta
- Test health endpoint: `https://your-app.railway.app/health`

**Database connection issues?**
- Verify Redis and Postgres services are running in Railway
- Check connection URLs are auto-generated

**OpenAI errors?**
- Verify API key is correct
- Check OpenAI usage at platform.openai.com

---

## Costs

- Railway: ~$5/month (free $5 credit first month)
- OpenAI: ~$0.50-2 per 1000 messages
- Total: ~$5-10/month for moderate usage

---

## Monitor

- **Health:** https://your-app.railway.app/health
- **Logs:** Railway dashboard → App → Deployments
- **Usage:** platform.openai.com/usage

