# Railway SQL Server Setup Guide

## ✅ What's Been Updated

1. **Dockerfile** - Added ODBC drivers for SQL Server
2. **Code** - Added SQL Server connection and bulk pricing integration
3. **Requirements** - Added `pyodbc==5.0.1`

## 📋 What You Need to Do on Railway

### Step 1: Add SQL Server Environment Variables

1. Go to your Railway project dashboard
2. Click on your **app service**
3. Go to the **"Variables"** tab
4. Add these new environment variables:

```
SQL_SERVER=10.20.2.6,1433
SQL_DATABASE=printerpix_gb
SQL_USER=readonly_user
SQL_PASSWORD=Pr!nterp!x@123
```

**Important:** Make sure you also have Supabase variables set:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Step 2: Deploy Changes

1. **Commit and push your changes to GitHub:**
   ```bash
   git add .
   git commit -m "Add SQL Server support for bulk pricing"
   git push origin main
   ```

2. **Railway will automatically:**
   - Detect the changes
   - Rebuild the Docker image (with ODBC drivers)
   - Redeploy your app

3. **Or manually trigger deployment:**
   - Go to Railway dashboard → Your app service
   - Click **"Deployments"** tab
   - Click **"Redeploy"** button

### Step 3: Verify Deployment

1. **Check Railway logs:**
   - Go to your app service → **"Deployments"** → Latest deployment → **"View Logs"**
   - Look for: `✓ SQL Server connection pool established`

2. **Test the connection:**
   - Check if bulk pricing is working
   - Try a bulk order quote

## 🔍 Troubleshooting

### If SQL Server connection fails:

1. **Check environment variables:**
   - Verify `SQL_SERVER`, `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD` are set correctly
   - Make sure there are no extra spaces or quotes

2. **Check Railway logs:**
   - Look for ODBC driver errors
   - Check if `msodbcsql18` installed successfully

3. **Check network connectivity:**
   - Railway needs to be able to reach `10.20.2.6:1433`
   - Make sure SQL Server allows connections from Railway's IP addresses

### If ODBC driver errors:

The Dockerfile now installs ODBC drivers automatically. If you see errors:
- Check Railway build logs for ODBC installation
- Verify the Dockerfile changes were deployed

## 📝 Summary

**What changed:**
- ✅ Dockerfile now installs Microsoft ODBC Driver 18 for SQL Server
- ✅ Code now uses SQL Server for base prices (primary source)
- ✅ Supabase still used for discounts (pricing_b_d table)

**What you need to do:**
1. ✅ Add SQL Server environment variables to Railway
2. ✅ Push code changes to GitHub (Railway auto-deploys)
3. ✅ Verify deployment in Railway logs

**No code changes needed** - everything is already updated! Just add the environment variables and deploy.

