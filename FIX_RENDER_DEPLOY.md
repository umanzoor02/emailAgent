# Fix Render build: `build.sh: No such file or directory`

## What went wrong

Your GitHub repo [umanzoor02/emailAgent](https://github.com/umanzoor02/emailAgent) looks like this:

```text
emailAgent/          ← repo root on GitHub
  manage.py          ← only backend files
  config/
  email_agent/
  requirements.txt
  .venv/             ← should NOT be on GitHub
  (no build.sh)
  (no frontend/)
```

Render expects the **full project** from your PC:

```text
emailAgent/          ← repo root
  build.sh           ← required
  render.yaml
  frontend/          ← React app
  backend/
    manage.py
    config/
    email_agent/
    requirements.txt
  README.md
  .gitignore
```

You pushed only the contents of `backend/`, not the whole `tryCursor` folder.

---

## Fix (push the correct folder)

Run these in PowerShell from the **tryCursor** folder (parent of `backend` and `frontend`):

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor"

git init
git add .
git status
```

**Check the list.** You should see:

- `build.sh`
- `frontend/src/App.jsx`
- `backend/manage.py`

You should **NOT** see:

- `backend/.env`
- `backend/.venv/`
- `frontend/node_modules/`

Then:

```powershell
git commit -m "Full project for Render: backend, frontend, build.sh"
git branch -M main
git remote remove origin 2>$null
git remote add origin https://github.com/umanzoor02/emailAgent.git
git push -u origin main --force
```

`--force` replaces the old incomplete repo on GitHub with the correct layout.  
(Only do this if you are the only one using the repo.)

---

## Render settings (after push)

| Setting | Value |
|---------|--------|
| **Root Directory** | *(leave empty)* |
| **Build Command** | `chmod +x build.sh && ./build.sh` |
| **Start Command** | `cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| **PYTHON_VERSION** | `3.12.5` (add env var — avoid 3.14) |

Environment variable:

| Key | Value |
|-----|--------|
| `PYTHON_VERSION` | `3.12.5` |

Then **Manual Deploy**.

---

## Verify on GitHub

Open: https://github.com/umanzoor02/emailAgent

You should see **`build.sh`** and folders **`backend/`** and **`frontend/`** at the top level.

If you only see `manage.py` at the root, the push was from the wrong folder again.
