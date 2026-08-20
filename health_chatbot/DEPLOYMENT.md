# Deploying to Render or Railway (Free Tier)

This project is ready to deploy as-is — it now includes a `Procfile`,
`runtime.txt`, and `gunicorn` in `requirements.txt`. Both Render and
Railway auto-detect a Python app from these files, so the steps are
almost identical.

## ⚠️ Read First: Free-Tier Storage Limitation

Both platforms' **free tiers use ephemeral disk storage** — meaning
every time you push a new deploy (or sometimes after long inactivity),
the filesystem resets to what's in your repo. This means:

- `instance/health_chatbot.db` (your SQLite database - all users, chat
  history) would be **wiped** on redeploy.
- `uploads/` (your uploaded PDFs) would be **wiped** on redeploy too.

**For a demo/college-project deployment this is usually fine** — the
app works perfectly between deploys, data just doesn't survive a fresh
deploy. If you need real persistence:

- **Render**: add a "Persistent Disk" (small monthly cost) mounted at
  `/opt/render/project/src/instance` and `/opt/render/project/src/uploads`.
- **Railway**: add a "Volume" mounted at the same paths — Railway's
  volumes are available on some free/trial credit too.
- Or migrate from SQLite to a managed Postgres database (both platforms
  offer a free Postgres add-on) — only requires changing
  `SQLALCHEMY_DATABASE_URI` in `app.py`; SQLAlchemy handles the rest.

---

## Option A: Deploy to Render

1. **Push your project to GitHub** (Render deploys from a Git repo, not
   a zip upload). Create a new repo and push this folder's contents.

2. Go to **[render.com](https://render.com)** → sign up / log in →
   **New +** → **Web Service**.

3. Connect your GitHub repo and select it.

4. Render should auto-detect the settings from your files, but confirm:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
     (this is also already in your `Procfile`, so Render may pick it
     up automatically)
   - **Environment**: Python 3

5. Under **Environment Variables**, add:
   | Key | Value |
   |---|---|
   | `SECRET_KEY` | any long random string (e.g. generate one with `python -c "import secrets; print(secrets.token_hex(32))"`) |
   | `FLASK_DEBUG` | `0` |

6. Click **Create Web Service**. Render will build and deploy — takes
   a few minutes on the first deploy.

7. Once live, Render gives you a URL like
   `https://your-app-name.onrender.com` — that's your public app,
   served over HTTPS automatically (required for the "Find Nearby
   Doctors" browser geolocation feature to work).

8. **Free tier note**: Render's free web services "spin down" after
   ~15 minutes of no traffic and take ~30-60 seconds to wake back up
   on the next request — this is normal, not a bug.

---

## Option B: Deploy to Railway

1. **Push your project to GitHub** (same as above).

2. Go to **[railway.app](https://railway.app)** → sign up / log in →
   **New Project** → **Deploy from GitHub repo** → select your repo.

3. Railway auto-detects Python + your `Procfile` and starts building.

4. Click on the deployed service → **Variables** tab → add:
   | Key | Value |
   |---|---|
   | `SECRET_KEY` | a long random string (same as above) |
   | `FLASK_DEBUG` | `0` |

   Railway sets `PORT` automatically — you don't need to add it.

5. Go to the **Settings** tab → **Networking** → **Generate Domain**
   to get a public HTTPS URL like `https://your-app.up.railway.app`.

6. Redeploy if needed (Railway usually redeploys automatically on
   every GitHub push once connected).

---

## After Deploying: Checklist

- [ ] Visit your public URL and confirm the login/register page loads.
- [ ] Register a test account and confirm login works (if it doesn't,
      check the platform's **Logs** tab — the app prints
      `[HealthBot] Using database file: ...` and login-failure reasons
      to the console, which show up there).
- [ ] Try "Find Nearby Doctors" — it needs HTTPS (which both platforms
      provide) and browser location permission.
- [ ] Try uploading a small PDF and asking a question about it.
- [ ] If you set `FLASK_DEBUG=0`, confirm error pages no longer show
      full stack traces to visitors (they shouldn't in production).

## Local Testing Under Gunicorn (Optional, Before Deploying)

You can test the exact production command locally first:
```bash
pip install -r requirements.txt
PORT=8000 SECRET_KEY=test-secret gunicorn app:app --bind 0.0.0.0:8000
```
Then open `http://127.0.0.1:8000`.
