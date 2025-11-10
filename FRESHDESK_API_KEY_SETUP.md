# How to Get Freshdesk API Key

## Step-by-Step Instructions

### 1. Log into Freshdesk
1. Go to: https://printerpix-support.freshdesk.com
2. Log in with your Freshdesk account credentials

### 2. Access Profile Settings
1. Click on your **profile picture/avatar** in the top right corner
2. Select **"Profile Settings"** from the dropdown menu

### 3. Navigate to API Section
1. In the left sidebar, look for **"API"** or **"API Key"** section
2. Click on it

### 4. Generate/Copy API Key
1. If you don't have an API key yet:
   - Click **"Generate API Key"** or **"Create API Key"**
   - Give it a name (e.g., "WhatsApp Bot Integration")
   - Click **"Generate"** or **"Create"**
   
2. If you already have an API key:
   - You'll see it displayed (usually masked like `xxxxx...xxxxx`)
   - Click **"Show"** or **"Copy"** to reveal/copy the full key

### 5. Copy the API Key
- Copy the entire API key (it's usually a long string of characters)
- **Important**: Copy it immediately - you might not be able to see it again!

### 6. Add to Railway Environment Variables
1. Go to Railway Dashboard → Your App Service
2. Click **"Variables"** tab
3. Add:
   ```
   FRESHDESK_API_URL=https://printerpix-support.freshdesk.com/api/v2/tickets
   FRESHDESK_API_KEY=<paste-your-api-key-here>
   ```

## Alternative: If API Key Section Not Visible

If you can't find the API section:

1. **Check Permissions**: You might need admin permissions to access API keys
2. **Contact Freshdesk Admin**: Ask your Freshdesk administrator to:
   - Generate an API key for you
   - Or give you access to the API section

## Using the Hardcoded Credential (Temporary)

If you can't get the API key right now, the code will use the hardcoded credential as a fallback:
- `"Basic RmZLSDR4Q0xMb1FTREtMZmFYenU6WA=="`

This is already in the code, so Freshdesk will work even without setting `FRESHDESK_API_KEY`.

However, it's **better to use environment variables** for security.

## Quick Reference

**What you need:**
- `FRESHDESK_API_URL`: `https://printerpix-support.freshdesk.com/api/v2/tickets` (already set as default)
- `FRESHDESK_API_KEY`: Your Freshdesk API key (get from Profile Settings → API)

**Where to add:**
- Railway Dashboard → Your App Service → Variables tab

**Note:** The API key is the username part of the Basic Auth. The code will automatically format it as `{API_KEY}:X` and base64 encode it.

