# Deployment Guide - Musication Backend

## Deploy to Render

### 1. Prerequisites
- GitHub account
- Render account (sign up at https://render.com)
- Push your code to GitHub

### 2. Create PostgreSQL Database

1. Go to Render Dashboard
2. Click "New +" → "PostgreSQL"
3. Settings:
   - Name: `musication-db`
   - Database: `musication`
   - User: `musication` (or leave default)
   - Region: Choose closest to you
   - Plan: **Free**
4. Click "Create Database"
5. Wait for it to provision (1-2 minutes)
6. **Important**: Copy the "Internal Database URL" - you'll need this

### 3. Create Web Service

1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Settings:
   - **Name**: `musication-backend`
   - **Region**: Same as database
   - **Branch**: `main` (or your branch)
   - **Root Directory**: `musication-backend` (if backend is in subfolder)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

### 4. Set Environment Variables

In the web service settings, add these environment variables:

| Key | Value |
|-----|-------|
| `FLASK_ENV` | `production` |
| `DATABASE_URL` | Paste the Internal Database URL from step 2 (**Render format is fine - auto-converted**) |
| `BASE_URL` | Your Render service URL (e.g., `https://musication-backend.onrender.com`) |
| `FRONTEND_URL` | Your Netlify URL (e.g., `https://musication.netlify.app`) |
| `UPLOAD_DIR` | `uploads` |

**Note**: 
- Render provides `DATABASE_URL` as `postgresql://...` which is automatically converted to use psycopg v3 (`postgresql+psycopg://`). You don't need to modify it.
- For `BASE_URL`, you won't know the full URL until after first deploy. You can:
- Leave it empty initially and update after deployment
- Or use the format: `https://musication-backend.onrender.com`

### 5. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy
3. Wait 3-5 minutes for first deployment
4. Once live, note your service URL (e.g., `https://musication-backend.onrender.com`)

### 6. Update BASE_URL

1. Go back to Environment Variables
2. Update `BASE_URL` with your actual Render URL
3. Save → service will redeploy automatically

### 7. Test Backend

Visit your backend URL + `/health`:
```
https://musication-backend.onrender.com/health
```

Should return:
```json
{"status": "ok"}
```

---

## Deploy Frontend to Netlify

### 1. Set Environment Variable

In Netlify Dashboard → Site settings → Environment variables:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | Your Render backend URL (e.g., `https://musication-backend.onrender.com`) |

### 2. Deploy

Netlify will auto-deploy from your GitHub repository.

### 3. Update Backend CORS

After getting your Netlify URL:
1. Go to Render → Backend service → Environment
2. Update `FRONTEND_URL` with your Netlify URL
3. Save → backend will redeploy

---

## Important Notes

### File Storage Limitation

⚠️ **Render's free tier has ephemeral filesystem** - uploaded audio files will be deleted when the service restarts (every ~15 days or on redeploy).

**Solutions:**
1. **For testing**: Accept file loss (fine for MVP)
2. **For production**: Use cloud storage (S3, Cloudflare R2, Supabase Storage)
3. **Paid option**: Render Persistent Disk ($7/month for 1GB)

### Database Persistence

✅ PostgreSQL data is persistent (even on free tier)

### Cold Starts

⚠️ Free tier sleeps after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds
- Upgrade to paid ($7/month) for always-on service

### Monitoring

Check logs in Render Dashboard → Your Service → Logs

---

## Troubleshooting

### "Application failed to respond"
- Check logs for errors
- Verify `DATABASE_URL` is set correctly
- Ensure gunicorn is in requirements.txt

### CORS errors in browser
- Verify `FRONTEND_URL` matches your Netlify domain exactly
- Check Render logs for CORS-related messages

### Database connection errors
- Verify `DATABASE_URL` format is correct
- Check database is running in Render dashboard
- Ensure using Internal Database URL, not External

### Files not persisting
- Expected behavior on free tier
- Implement cloud storage or upgrade to persistent disk

---

## Production Checklist

- [ ] Backend deployed to Render
- [ ] PostgreSQL database created and connected
- [ ] All environment variables set
- [ ] Health endpoint returns 200
- [ ] Frontend deployed to Netlify
- [ ] Frontend can fetch from backend (no CORS errors)
- [ ] Upload works end-to-end
- [ ] Delete works
- [ ] Library stats update correctly

---

## Next Steps (Optional)

1. **Set up custom domain** (Netlify + Render both support this)
2. **Add cloud storage** for audio files (S3/R2)
3. **Set up Alembic migrations** for database schema changes
4. **Add monitoring** (Sentry, LogRocket)
5. **Upgrade to paid tier** for always-on backend ($7/month)
