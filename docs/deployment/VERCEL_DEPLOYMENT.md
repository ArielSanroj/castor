# Vercel Deployment Guide for Castor Elecciones

This guide explains how to deploy the frontend to Vercel while using ngrok for the backend.

## Prerequisites

1. Vercel account
2. ngrok account with auth token
3. Backend running locally on port 80

## Setup Steps

### 1. Ngrok Backend Setup

1. Install ngrok if not already installed:
   ```bash
   # macOS
   brew install ngrok/ngrok/ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. Authenticate ngrok:
   ```bash
   ngrok config add-authtoken 2mtkS18m9XOwl8cFgBxpWHyXgio_4wLygqUmXu7Fqz43DhN2w
   ```

3. Start ngrok tunnel:
   ```bash
   ngrok http --url=castorelecciones.ngrok.app 80
   ```

   Or use the config file:
   ```bash
   ngrok start --config=ngrok.yml castor-backend
   ```

4. Verify the tunnel is running and note the HTTPS URL (should be `https://castorelecciones.ngrok.app`)

### 2. Vercel Frontend Deployment

1. Install Vercel CLI (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Set environment variable in Vercel:
   - Go to your Vercel project settings
   - Navigate to Environment Variables
   - Add: `NEXT_PUBLIC_API_BASE_URL` = `https://castorelecciones.ngrok.app`

   Or via CLI:
   ```bash
   vercel env add NEXT_PUBLIC_API_BASE_URL
   # Enter: https://castorelecciones.ngrok.app
   ```

4. Deploy to Vercel:
   ```bash
   vercel --prod
   ```

   Or connect your GitHub repository to Vercel for automatic deployments.

### 3. Update HTML Templates for Production

Before deploying, you may need to update the HTML templates to use the ngrok URL. The templates currently use Flask's `url_for` which won't work in static deployment.

For production, update the API_BASE_URL script tag in each HTML template:

```html
<script>
    window.API_BASE_URL = 'https://castorelecciones.ngrok.app';
</script>
```

Or use Vercel's environment variable injection (recommended).

### 4. File Structure for Vercel

Vercel will serve:
- `/templates/*.html` - HTML pages
- `/static/*` - Static assets (CSS, JS, images)

The `vercel.json` configuration handles routing:
- `/` → `/templates/index.html`
- `/webpage` → `/templates/webpage.html`
- `/media` → `/templates/media.html`
- `/campaign` → `/templates/campaign.html`
- `/forecast` → `/templates/forecast.html`

## Environment Variables

### Vercel Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: The ngrok backend URL (e.g., `https://castorelecciones.ngrok.app`)

### Backend Environment Variables

Keep your backend `.env` file with all necessary variables:
- `TWITTER_BEARER_TOKEN`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- etc.

## Troubleshooting

### CORS Issues

If you encounter CORS errors, make sure your backend allows requests from your Vercel domain. Update `CORS_ORIGINS` in your backend config to include your Vercel URL.

### API Not Found

- Verify ngrok tunnel is running: `https://castorelecciones.ngrok.app/api/health`
- Check that `NEXT_PUBLIC_API_BASE_URL` is set correctly in Vercel
- Verify the API base URL is being injected correctly in the browser console

### Static Files Not Loading

- Ensure `vercel.json` routes are correct
- Check that static files are committed to git
- Verify file paths in HTML templates use `/static/` prefix

## Development Workflow

1. Start backend locally: `cd backend && python run.py`
2. Start ngrok tunnel: `ngrok http --url=castorelecciones.ngrok.app 80`
3. Update Vercel environment variable if ngrok URL changes
4. Deploy frontend: `vercel --prod`

## Notes

- Ngrok free tier has limitations (request limits, session timeouts)
- Consider upgrading to ngrok paid plan for production
- For production, consider using a proper backend hosting solution instead of ngrok

