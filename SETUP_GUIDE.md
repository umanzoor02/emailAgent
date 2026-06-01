# Job Email Agent — Setup Guide

Follow these steps in order. Each section has a checklist you can tick off as you go.

---

## Overview: what you are setting up

| Piece | What it does | You need |
|-------|----------------|----------|
| **Google Cloud** | Lets the app read your Gmail (read-only) | Google account, ~15 min one-time setup |
| **Django backend** | OAuth, fetches email, runs the agent | Python 3.11+ |
| **React frontend** | Buttons and results in the browser | Node.js 18+ |
| **`.env` file** | Tells the agent what counts as “job” email | Your job title, company, keywords |
| **Cursor API key** *(optional)* | Smarter AI triage instead of keywords only | [Cursor Integrations](https://cursor.com/dashboard/integrations) |

When everything works, you will:

1. Open **http://localhost:5173**
2. Click **Connect Gmail** and sign in
3. Click **Check important emails**
4. See a summary and a list of flagged messages

---

## Step 0 — Install tools (one time)

### Check Python

Open **PowerShell** and run:

```powershell
python --version
```

You need **3.11 or newer**. If missing, install from [python.org](https://www.python.org/downloads/) and check **“Add Python to PATH”**.

### Check Node.js

```powershell
node --version
npm --version
```

You need **Node 18+**. If missing, install from [nodejs.org](https://nodejs.org/).

### Checklist

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Project folder open: `C:\Users\Lubna Manzoor\Documents\tryCursor`

---

## Step 1 — Google Cloud & Gmail API (required)

The app cannot read email until Google OAuth is configured.

### 1.1 Create or pick a project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Top bar → select a project or **New Project** (e.g. name it `job-email-agent`).

### 1.2 Enable Gmail API

1. **APIs & Services** → **Library**
2. Search **Gmail API** → open it → **Enable**

### 1.3 Configure OAuth consent screen

1. **APIs & Services** → **OAuth consent screen**
2. User type: **External** (fine for personal Gmail) → **Create**
3. Fill required fields:
   - App name: e.g. `Job Email Agent`
   - User support email: your email
   - Developer contact: your email
4. **Save and Continue** through Scopes (you can skip adding scopes here)
5. **Test users** → **Add users** → add **your Gmail address** (required while app is in “Testing”)
6. Finish the wizard

### 1.4 Create OAuth credentials

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Web application**
3. Name: e.g. `Job Email Agent Local`
4. **Authorized redirect URIs** → **Add URI** — paste **exactly**:

   ```
   http://localhost:5173/api/auth/gmail/callback/
   ```

   Include the trailing slash. This goes through the Vite dev server so login state matches the React app (port 8000 alone will show “not connected” after OAuth).

   You can keep `http://localhost:8000/api/auth/gmail/callback/` only if you do **not** use the React dev server (not recommended).

5. **Create** → copy **Client ID** and **Client secret** (you will put them in `.env`)

### Checklist

- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] Your Gmail added as a test user
- [ ] OAuth Web client created
- [ ] Redirect URI matches exactly
- [ ] Client ID and Client secret saved somewhere safe

---

## Step 2 — Configure the backend `.env` (required)

### 2.1 Create the env file

In PowerShell:

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor\backend"
copy .env.example .env
notepad .env
```

(Or open `.env` in Cursor.)

### 2.2 Fill in required values

| Variable | What to put |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | From Google Credentials (Step 1.4) |
| `GOOGLE_CLIENT_SECRET` | From Google Credentials (Step 1.4) |
| `GOOGLE_REDIRECT_URI` | Must be `http://localhost:5173/api/auth/gmail/callback/` (same as Google Console) |

### 2.3 Customize job context (recommended)

These help the agent know what “important for work” means for **you**:

| Variable | Example | Purpose |
|----------|---------|---------|
| `JOB_TITLE` | `Product Manager` | Your role |
| `JOB_COMPANY` | `Contoso Ltd` | Company name in email text |
| `JOB_SENDER_DOMAINS` | `contoso.com,contoso.co.uk` | Emails from work domains score higher |
| `JOB_KEYWORDS` | `interview,deadline,manager,client` | Comma-separated; add words you care about |

### 2.4 Optional: Cursor AI agent

For smarter analysis (not just keywords):

1. Open [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations)
2. Create/copy an API key
3. In `.env`:

   ```
   CURSOR_API_KEY=cursor_your_key_here
   ```

If you skip this, the app still works using **heuristic** rules.

### Checklist

- [ ] `backend\.env` exists (copied from `.env.example`)
- [ ] `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` filled in
- [ ] `JOB_*` fields customized for your job
- [ ] (Optional) `CURSOR_API_KEY` set

---

## Step 3 — Install and run the Django backend

Keep this terminal open while you use the app.

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor\backend"

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate

python manage.py runserver
```

You should see something like: `Starting development server at http://127.0.0.1:8000/`

### Quick test

In a browser, open:

```
http://127.0.0.1:8000/api/health/
```

You should see JSON with `"status": "ok"` and `"gmail_configured": true` after `.env` is set.

### Checklist

- [ ] Virtual environment created (`.venv` folder)
- [ ] Dependencies installed (`pip install` succeeded)
- [ ] `python manage.py migrate` succeeded
- [ ] Server running on port **8000**
- [ ] `/api/health/` shows `gmail_configured: true`

---

## Step 4 — Install and run the React frontend

Open a **second** PowerShell window:

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor\frontend"

npm install

npm run dev
```

You should see a local URL, usually:

```
http://localhost:5173/
```

### Checklist

- [ ] `npm install` completed without errors
- [ ] `npm run dev` running
- [ ] Browser can open **http://localhost:5173**

---

## Step 5 — Use the app (first time)

Both servers must be running:

| Terminal | Command | URL |
|----------|---------|-----|
| 1 | `python manage.py runserver` | http://127.0.0.1:8000 |
| 2 | `npm run dev` | http://localhost:5173 |

### 5.1 Connect Gmail

1. Open **http://localhost:5173**
2. Status should show **OAuth configured** (green) if `.env` is correct
3. Click **Connect Gmail**
4. Sign in with the **same Google account** you added as a test user
5. If Google shows “Google hasn’t verified this app” → **Advanced** → **Go to Job Email Agent (unsafe)** — normal for personal/test apps
6. Allow **read-only** Gmail access
7. You are redirected back to the app; status should show **Gmail connected**

### 5.2 Run the agent

1. Click **Check important emails**
2. Wait while it scans (up to ~40 recent inbox messages by default)
3. Read the **Agent summary** and **Important emails** list

### Checklist

- [ ] Gmail connected in the UI
- [ ] First email check completed
- [ ] Results look reasonable (adjust `JOB_*` in `.env` if needed)

---

## Step 6 — After setup (optional improvements)

### Improve accuracy

Edit `backend\.env` and restart Django (`Ctrl+C`, then `runserver` again):

- Add your real **company domain** to `JOB_SENDER_DOMAINS`
- Add role-specific words to `JOB_KEYWORDS` (e.g. `sprint`, `invoice`, `onboarding`)
- Set `CURSOR_API_KEY` for AI-based triage

### See past checks

The UI shows **Recent checks**. Full history is also in Django admin:

```powershell
cd backend
.venv\Scripts\activate
python manage.py createsuperuser
```

Then open **http://127.0.0.1:8000/admin/** and log in.

---

## Troubleshooting

### “OAuth needs .env” or Connect Gmail does nothing

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` missing or wrong in `backend\.env`
- Restart Django after editing `.env`

### `redirect_uri_mismatch` from Google

- Redirect URI in Google Console must be **exactly**:
  `http://localhost:5173/api/auth/gmail/callback/`
- Must match `GOOGLE_REDIRECT_URI` in `backend\.env`

### “Access blocked” / `Error 403: access_denied` / app not verified

Google shows this when the app is in **Testing** mode and the Google account you sign in with is **not** on the Test users list (or you used the wrong Cloud project).

**Fix (do all of these):**

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select the **same project** where you created the OAuth Client ID in `backend\.env`.
2. **APIs & Services** → **OAuth consent screen**.
3. Confirm **Publishing status** is **Testing** (that is normal for local dev).
4. Scroll to **Test users** → **+ Add users**.
5. Add the **exact** address you use on the Google sign-in page, e.g. `usamamanzoor11147@gmail.com` (must match character-for-character).
6. Click **Save**.
7. Wait **5–10 minutes**, then try again in an **Incognito/InPrivate** window (avoids wrong Google account cached).
8. On the Google chooser, pick **only** that test-user account.

**Common mistakes:**

| Mistake | What happens |
|--------|----------------|
| Test user added in a **different** Cloud project than your Client ID | Still blocked |
| Added `user@gmail.com` but signed in as `user@gmail.com` with another profile | Still blocked |
| Added email under Credentials instead of **OAuth consent screen → Test users** | Still blocked |
| Only filled consent screen app info, never opened **Test users** section | Still blocked |

**Verify Client ID matches project:** In **Credentials**, open your Web client and compare **Client ID** to `GOOGLE_CLIENT_ID` in `backend\.env` — they must be identical.

**Still blocked after 10+ minutes?** On OAuth consent screen → **Edit app** → ensure **User type** is **External**, save, re-add test user, save again.

### `InsecureTransportError` / OAuth 2 MUST utilize https

- In `backend\.env` ensure `DJANGO_DEBUG=true` and `OAUTHLIB_INSECURE_TRANSPORT=1`
- Restart Django after changing `.env`
- This only applies to local **http** development; production must use HTTPS

### Gmail connects but UI still says “not connected”

- Frontend must use the Vite proxy (`/api`), not `http://127.0.0.1:8000/api` directly.
- `GOOGLE_REDIRECT_URI` in `.env` must be `http://localhost:5173/api/auth/gmail/callback/`
- Add that same URI in Google Cloud Console → Credentials → redirect URIs
- Open the app at **http://localhost:5173** (not `127.0.0.1:5173`)
- Restart Django and `npm run dev` after changing `.env`

### Frontend cannot reach API

- Django must be on port **8000**
- Keep both terminals running
- Try **http://localhost:5173/api/health/** in the browser (proxied to Django)

### POST fails / CSRF error

- Refresh the page (loads CSRF cookie via `/api/health/`)
- Use the app at `localhost:5173`, not a different host

### No emails flagged but you expected some

- Broaden `JOB_KEYWORDS` and `JOB_SENDER_DOMAINS`
- Set `CURSOR_API_KEY` for smarter detection
- Increase scan size: `EMAIL_FETCH_MAX=60` in `.env`

### Cursor agent errors

- Verify API key at [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations)
- App falls back to heuristics automatically if Cursor fails

---

## Quick reference — commands to start every day

**Terminal 1 — backend:**

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor\backend"
.venv\Scripts\activate
python manage.py runserver
```

**Terminal 2 — frontend:**

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor\frontend"
npm run dev
```

Then open **http://localhost:5173**.

---

## Files you will touch most

| File | When |
|------|------|
| `backend\.env` | Google keys, job title, company, keywords |
| `SETUP_GUIDE.md` | This guide |
| `README.md` | Architecture and API reference |

---

## Security reminders

- Do **not** commit `backend\.env` to Git (it is in `.gitignore`)
- Gmail access is **read-only**
- For anything beyond local testing, use HTTPS and stronger token storage

---

## Need help?

If something fails, note:

1. Which step you were on
2. The exact error message (browser or PowerShell)
3. Whether `/api/health/` works in the browser

That makes it easy to debug the next issue.
