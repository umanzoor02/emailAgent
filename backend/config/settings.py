import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

# Production on Render / manual SERVE_SPA: Django serves React build + API on one domain.
SERVE_SPA = os.environ.get("SERVE_SPA", "").lower() in ("1", "true", "yes") or bool(
    os.environ.get("RENDER")
)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-only-change-me-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

# Local dev uses http:// — oauthlib blocks that unless this is set (never in production).
if DEBUG and os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", "1") != "0":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)

_PRODUCTION_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")
if SERVE_SPA and _PRODUCTION_URL.startswith("https://"):
    _host = _PRODUCTION_URL.replace("https://", "").split("/")[0]
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "email_agent",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

FRONTEND_DIST = BASE_DIR / "frontend_dist"
STATIC_URL = "/assets/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if (FRONTEND_DIST / "assets").exists():
    STATICFILES_DIRS = [FRONTEND_DIST / "assets"]
else:
    STATICFILES_DIRS = []

if SERVE_SPA:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if _render_host:
    _default_cors = f"https://{_render_host}"
elif SERVE_SPA and _PRODUCTION_URL:
    _default_cors = _PRODUCTION_URL
else:
    _default_cors = "http://localhost:5173,http://127.0.0.1:5173"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", _default_cors).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG or SERVE_SPA
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
if _render_host:
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# Gmail OAuth (Google Cloud Console → APIs & Services → Credentials)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
if _render_host and not os.environ.get("FRONTEND_URL"):
    FRONTEND_URL = f"https://{_render_host}"
else:
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

if _render_host and not os.environ.get("GOOGLE_REDIRECT_URI"):
    GOOGLE_REDIRECT_URI = f"{FRONTEND_URL.rstrip('/')}/api/auth/gmail/callback/"
else:
    GOOGLE_REDIRECT_URI = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/gmail/callback/"
    )

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Cursor SDK agent (optional; falls back to heuristic scoring)
CURSOR_API_KEY = os.environ.get("CURSOR_API_KEY", "")
CURSOR_MODEL = os.environ.get("CURSOR_MODEL", "composer-2.5")

# Gmail search — base filter for Indeed (combined with newer_than below)
EMAIL_GMAIL_QUERY = os.environ.get(
    "EMAIL_GMAIL_QUERY",
    "from:indeed OR from:indeedemail",
)

# How far back to search: 1 = last 24h, 7 = week, 30 = month (Gmail newer_than:Nd)
EMAIL_SEARCH_DAYS = int(os.environ.get("EMAIL_SEARCH_DAYS", "30"))

# all = entire mailbox (except spam/trash); inbox = INBOX label only
EMAIL_SEARCH_SCOPE = os.environ.get("EMAIL_SEARCH_SCOPE", "all").lower()

# If True, drop messages whose From header does not contain "indeed"
EMAIL_STRICT_SENDER_FILTER = os.environ.get(
    "EMAIL_STRICT_SENDER_FILTER", "false"
).lower() in ("1", "true", "yes")

INDEED_SENDER_HINTS = [
    h.strip().lower()
    for h in os.environ.get("INDEED_SENDER_HINTS", "indeed").split(",")
    if h.strip()
]

# Job context used when ranking Indeed mail importance
JOB_KEYWORDS = [
    k.strip()
    for k in os.environ.get(
        "JOB_KEYWORDS",
        "interview,application,applied,employer,recruiter,offer,"
        "viewed your resume,job alert,new jobs,matched,hiring,"
        "schedule,assessment,phone screen,remote,onsite",
    ).split(",")
    if k.strip()
]
JOB_TITLE = os.environ.get("JOB_TITLE", "")
JOB_COMPANY = os.environ.get("JOB_COMPANY", "Indeed")
JOB_SENDER_DOMAINS = [
    d.strip()
    for d in os.environ.get(
        "JOB_SENDER_DOMAINS", "indeed.com,indeedemail.com,indeed.co.uk"
    ).split(",")
    if d.strip()
]

EMAIL_FETCH_MAX = int(os.environ.get("EMAIL_FETCH_MAX", "100"))
