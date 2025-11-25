# Dashboard Deployment Guide

## Backend Deployment (Railway)

The analytics API endpoints have been added to your FastAPI backend. To deploy:

1. **Commit and push your changes:**
```bash
git add api/analytics.py api/webhook.py
git commit -m "Add analytics API endpoints for dashboard"
git push origin main
```

2. **Railway will automatically deploy** if you have auto-deploy enabled.

3. **Verify the endpoints are working:**
   - Visit: `https://your-app.railway.app/api/analytics/stats`
   - You should see JSON response with statistics

## Frontend Deployment (Vercel)

### Option 1: Deploy from GitHub (Recommended)

1. **Push dashboard code to GitHub:**
```bash
git add dashboard/
git commit -m "Add analytics dashboard"
git push origin main
```

2. **Go to Vercel:**
   - Visit [vercel.com](https://vercel.com)
   - Sign in with GitHub
   - Click "Add New Project"
   - Import your repository

3. **Configure the project:**
   - **Root Directory**: Set to `dashboard`
   - **Framework Preset**: Next.js (auto-detected)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)

4. **Add Environment Variable:**
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: Your Railway backend URL (e.g., `https://your-app.railway.app`)
   - Click "Add"

5. **Deploy:**
   - Click "Deploy"
   - Wait for build to complete
   - Your dashboard will be live at `https://your-project.vercel.app`

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI:**
```bash
npm i -g vercel
```

2. **Navigate to dashboard directory:**
```bash
cd dashboard
```

3. **Login to Vercel:**
```bash
vercel login
```

4. **Deploy:**
```bash
vercel
```

5. **Set environment variable:**
```bash
vercel env add NEXT_PUBLIC_API_URL
# Enter your Railway backend URL when prompted
```

6. **Redeploy with environment variable:**
```bash
vercel --prod
```

## Post-Deployment Checklist

- [ ] Backend endpoints are accessible at `/api/analytics/*`
- [ ] Frontend can connect to backend (check browser console)
- [ ] CORS is properly configured (already set to `["*"]` in webhook.py)
- [ ] Environment variable `NEXT_PUBLIC_API_URL` is set in Vercel
- [ ] Dashboard loads and displays data correctly
- [ ] Charts render properly
- [ ] Date filtering works
- [ ] CSV export works

## Troubleshooting

### Dashboard shows "No data available"
- Check that `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Verify backend is accessible and endpoints return data
- Check browser console for API errors

### CORS errors
- Backend CORS is already configured to allow all origins (`["*"]`)
- If issues persist, check Railway logs

### Charts not rendering
- Ensure Recharts is installed: `npm install recharts`
- Check browser console for errors
- Verify data is being fetched correctly

### Build fails on Vercel
- Check that all dependencies are in `package.json`
- Ensure Node.js version is 18+ (Vercel auto-detects)
- Check build logs in Vercel dashboard

## Custom Domain (Optional)

1. In Vercel dashboard, go to your project settings
2. Navigate to "Domains"
3. Add your custom domain
4. Follow DNS configuration instructions

## Monitoring

- Monitor Railway logs for backend errors
- Monitor Vercel logs for frontend errors
- Set up error tracking (e.g., Sentry) if needed



