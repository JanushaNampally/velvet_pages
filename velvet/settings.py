"""Velvet Pages settings. Configure via environment variables (see README)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=""):
    return os.environ.get(name, default)


DEBUG = env("VELVET_DEBUG", "1") == "1"
SETUP_TOKEN = env("VELVET_SETUP_TOKEN")
SECRET_KEY = env("VELVET_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-change-me"
    else:
        raise RuntimeError("Set VELVET_SECRET_KEY when VELVET_DEBUG=0")

ALLOWED_HOSTS = [h for h in env("VELVET_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in env("VELVET_CSRF_ORIGINS").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "reading",
    "diary",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.OwnerOnlyMiddleware",  # every URL requires owner login + unlocked vault
]

ROOT_URLCONF = "velvet.urls"
WSGI_APPLICATION = "velvet.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

if env("VELVET_DB") == "postgres":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("PGDATABASE", "velvet_pages"),
        "USER": env("PGUSER", "postgres"),
        "PASSWORD": env("PGPASSWORD"),
        "HOST": env("PGHOST", "localhost"),
        "PORT": env("PGPORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.Owner"
LOGIN_URL = "/login/"

# The unlocked vault key lives ONLY in process memory (never in the DB).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SESSION_COOKIE_AGE = 12 * 3600          # hard session expiry
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Private storage: NOT served by any URL. Files here are AES-256-GCM ciphertext.
PRIVATE_STORAGE_ROOT = Path(env("VELVET_STORAGE", str(BASE_DIR / "private_storage")))
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 20

# OTP login
OTP_BACKEND = env("VELVET_OTP_BACKEND", "console")   # "console" (dev) or "twilio"
OTP_TTL_SECONDS = 300
REQUIRE_OTP = env("VELVET_REQUIRE_OTP", "1") == "1"   # set 0 to log in with password only
OTP_MAX_ATTEMPTS = 5
OTP_MAX_REQUESTS_PER_HOUR = 5
DEFAULT_COUNTRY_CODE = env("VELVET_COUNTRY_CODE", "+91")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM = env("TWILIO_FROM")

TIME_ZONE = env("VELVET_TZ", "Asia/Kolkata")
USE_TZ = True
LANGUAGE_CODE = "en-us"

# Never log request bodies / content.
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "WARNING"}}
