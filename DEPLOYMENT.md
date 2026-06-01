# Deploy free on Render.com (Django + React, one URL)

Render’s **free** web tier hosts this app as one site: React UI + `/api` on HTTPS. Good for learning; the app sleeps after ~15 minutes idle (slow first load).

**GitHub does not deploy by itself** unless you enable auto-deploy on Render. Default: you deploy manually.

---

## Before you deploy

1. Code on GitHub (`main` branch) — see [GITHUB.md](./GITHUB.md)
2. Google Cloud OAuth client with **production** redirect URI (add after you get Render URL)
3. ~20 minutes for first setup

---

## Step 1 — Push to GitHub

Follow [GITHUB.md](./GITHUB.md). You need the repo URL for connecting Render.

---

## Step 2 — Create Render web service

1. Sign up: [render.com](https://render.com) (GitHub login is easiest)
2. **Dashboard → New + → Web Service**
3. Connect your GitHub repo `indeed-email-agent`
4. Settings:

| Field | Value |
|-------|--------|
| **Name** | `indeed-email-agent` (or any name) |
| **Region** | Closest to you |
| **Branch** | `main` |
| **Runtime** | Python 3 |
| **Build Command** | `chmod +x build.sh && ./build.sh` |
| **Start Command** | `cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| **Plan** | **Free** |

5. **Advanced → Add Environment Variables** (required):

| Key | Value |
|-----|--------|
| `DJANGO_DEBUG` | `false` |
| `SERVE_SPA` | `true` |
| `OAUTHLIB_INSECURE_TRANSPORT` | `0` |
| `DJANGO_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `GOOGLE_CLIENT_ID` | From Google Cloud |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud |

Optional (same as local `.env`):

- `EMAIL_SEARCH_DAYS`, `JOB_KEYWORDS`, `CURSOR_API_KEY`, etc.

6. **Do not enable “Auto-Deploy”** yet if you want manual control (you can leave it on later).

7. Click **Create Web Service**. Wait for the first build (5–10 min).

8. Copy your live URL, e.g. `https://indeed-email-agent.onrender.com`

---

## Step 3 — Google OAuth for production

1. [Google Cloud Console](https://console.cloud.google.com/) → your project → **Credentials**
2. Edit your OAuth **Web client**
3. **Authorized redirect URIs** → add:

   ```
   https://YOUR-APP-NAME.onrender.com/api/auth/gmail/callback/
   ```

   Trailing slash required. Keep localhost URIs for local dev.

4. **OAuth consent screen** → keep in **Testing** and add your Gmail as test user (or publish app later)

5. On Render, set (if not auto-filled):

| Key | Value |
|-----|--------|
| `FRONTEND_URL` | `https://YOUR-APP-NAME.onrender.com` |
| `GOOGLE_REDIRECT_URI` | `https://YOUR-APP-NAME.onrender.com/api/auth/gmail/callback/` |
| `CORS_ALLOWED_ORIGINS` | `https://YOUR-APP-NAME.onrender.com` |
| `DJANGO_ALLOWED_HOSTS` | `YOUR-APP-NAME.onrender.com` |

6. **Manual Deploy** on Render (or push to `main` if auto-deploy is on)

---

## Step 4 — Test production

1. Open `https://YOUR-APP-NAME.onrender.com`
2. **Connect Gmail** → Google sign-in (HTTPS)
3. Enter keywords → **Search emails**

---

## Manual deploy workflow (recommended for you)

```text
Local PC: build & test → git commit → git push (when happy)
Render:   click "Manual Deploy" → deploy latest main
```

Broken local code never touches GitHub until you push; GitHub never touches Render until you deploy.

To enable auto-deploy later: Render → your service → **Settings** → Auto-Deploy **Yes** (only when you trust `main`).

---

## Free tier limitations

| Topic | Note |
|-------|------|
| **Sleep** | Service spins down; first visit after idle ~30–60s |
| **SQLite** | Data may reset on redeploy; reconnect Gmail after deploy |
| **Hours** | Free web hours per month (enough for personal use) |
| **Custom domain** | Optional later on Render |

For a persistent database later, add Render PostgreSQL (paid) or another host.

---

## Alternative free options

| Platform | Notes |
|----------|--------|
| **Render** (this guide) | Easiest single-app deploy |
| **Railway** | Free credits/month, similar setup |
| **Fly.io** | Docker, slightly more advanced |
| **Vercel + Render** | Split frontend/backend — harder OAuth cookies |

---

## Troubleshooting production

| Problem | Fix |
|---------|-----|
| `build.sh: No such file or directory` | You pushed only `backend/` to GitHub. Push the **whole** project (`build.sh`, `frontend/`, `backend/`). See **[FIX_RENDER_DEPLOY.md](./FIX_RENDER_DEPLOY.md)** |
| Build fails on `npm` | Check Render logs; Node version in build |
| Python 3.14 on Render | Set env `PYTHON_VERSION` = `3.12.5` |
| `redirect_uri_mismatch` | Redirect URI must match Render URL exactly |
| 502 after deploy | Check start command and logs |
| Gmail connected locally but not prod | Production uses separate session; connect again on live URL |
| Static files 404 | Re-run deploy; ensure `build.sh` copied `frontend/dist` |

---

## Local vs production

| | Local | Production (Render) |
|---|--------|---------------------|
| Frontend | `npm run dev` :5173 | Same domain as API |
| API | `/api` via Vite proxy | `/api` on Render URL |
| OAuth redirect | `localhost:5173/...` | `https://xxx.onrender.com/...` |
| HTTP OAuth | `OAUTHLIB_INSECURE_TRANSPORT=1` | Must be `0` (HTTPS) |
