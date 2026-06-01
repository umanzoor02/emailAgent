# GitHub — manual workflow (nothing uploads by itself)

## Important: your code is safe until YOU push

Cursor, VS Code, and Git **do not** send anything to GitHub automatically.

| Action | Effect on GitHub |
|--------|------------------|
| Edit files locally | Nothing — only on your PC |
| `git add` / `git commit` | Still nothing — only local history |
| **`git push`** | **Only then** GitHub updates |

If you break the app locally, GitHub stays on the last version you pushed — **unless** you push the broken code yourself.

---

## Recommended branch strategy

| Branch | Purpose |
|--------|---------|
| **`main`** | Stable version that works (matches production when you deploy) |
| **`dev`** (optional) | Experiments; merge to `main` when ready |

```powershell
# Create dev branch for risky changes
git checkout -b dev
# ... work ...
git checkout main
git merge dev
git push origin main
```

On GitHub: **Settings → Branches → Add rule** on `main` → require pull request (optional, good practice).

**Do not** enable auto-deploy from GitHub to Render until you want every push to go live. Deploy manually on Render when ready (see [DEPLOYMENT.md](./DEPLOYMENT.md)).

---

## First-time: push this project to GitHub

### 1. Create an empty repo on GitHub

1. [github.com/new](https://github.com/new)
2. Name: e.g. `indeed-email-agent`
3. **Do not** add README, .gitignore, or license (you already have them)
4. Create repository

### 2. Initialize Git locally (once)

In PowerShell, from the project folder:

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor"

git init
git add .
git status
```

Confirm **`backend\.env`** is **not** listed (secrets stay local).

```powershell
git commit -m "Initial commit: Indeed email agent (Django + React)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/indeed-email-agent.git
git push -u origin main
```

Replace `YOUR_USERNAME` and repo name with yours. GitHub may ask you to sign in (browser or token).

---

## Day-to-day: save working code to GitHub

Only when you are happy with local testing:

```powershell
cd "C:\Users\Lubna Manzoor\Documents\tryCursor"
git status
git add .
git commit -m "Describe what you changed"
git push origin main
```

If `git push` fails, fix the error before retrying — nothing partial is uploaded.

---

## What is never committed (protected by `.gitignore`)

- `backend\.env` — Google secrets, API keys
- `backend\.venv\` — Python virtualenv
- `backend\db.sqlite3` — local database
- `frontend\node_modules\` — npm packages

Share secrets only via Render environment variables or `.env.example` (no real keys).

---

## Undo a bad local commit (before push)

```powershell
git reset --soft HEAD~1
```

This removes the last commit but keeps your file changes.

## If you already pushed broken code

```powershell
git log
git revert HEAD
git push origin main
```

Or reset to an older commit (only if you understand `git reset`).

---

## Production vs local

| Environment | Updates when |
|-------------|----------------|
| **Your PC** | You save files |
| **GitHub** | You run `git push` |
| **Render (live site)** | You click Deploy or push *if* you turned on auto-deploy |

Keep production stable: push to GitHub when `main` works, then deploy that commit on Render.
