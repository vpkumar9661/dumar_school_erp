# 🚀 Render Deployment Guide — VVM School ERP v2.0

## Quick Deploy (3 Minutes)

1. **Push to GitHub** — `git push origin main`
2. **Render Dashboard** → [render.com](https://render.com) → **"New +"** → **"Blueprint"**
3. **Connect repo** — Render auto-detects `render.yaml`
4. **Set secret env vars** in Dashboard → Environment:
   - `DATABASE_URL` — your Supabase PostgreSQL connection string
   - `SUPABASE_URL` — your Supabase project URL
   - `SUPABASE_ANON_KEY` — Supabase anon/public key
   - `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key
   - `SMTP_PASSWORD` — Gmail app password (for email notifications)
   - `GEMINI_API_KEY` — Google AI key (optional)
5. **Deploy** — Click "Manual Deploy" → "Deploy latest commit"
6. **Visit** — `https://vvm-school-erp.onrender.com`

## Manual Deploy (Without Blueprint)

| Setting | Value |
|---------|-------|
| Runtime | Python |
| Build Command | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120` |
| Plan | Free |

## Files Used by Render

| File | Purpose |
|------|---------|
| `render.yaml` | Blueprint — auto-configures the service |
| `Procfile` | Start command for Gunicorn |
| `requirements.txt` | Python dependencies |
| `runtime.txt` | Python version (3.11.6) |

## Notes

- **Free tier** spins down after 15 min idle → first request takes ~30s
- **File uploads** go to `/tmp` (ephemeral) → use Supabase Storage for persistence
- **Logs** → Render Dashboard → your service → Logs tab
