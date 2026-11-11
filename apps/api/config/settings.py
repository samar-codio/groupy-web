"""Django settings for the Groupy API.

S1 scope: data model only.
- Env validation at boot (pydantic-settings) and health endpoints are S0.
- DRF, middleware, security headers are S2+.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DEBUG = _env("DEBUG", "false").lower() in ("1", "true", "yes")

# SECURITY (RULES.md §3.1): a real secret only ever comes from the environment.
# The dev-only fallback exists so `manage.py check` works with zero setup;
# staging/prod refuse to boot without SECRET_KEY (enforced in S0).
SECRET_KEY = _env("SECRET_KEY") or ("dev-only-insecure-secret-key" if DEBUG else "")

ALLOWED_HOSTS = [h for h in _env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    # NOTE (ADR-001): django.contrib.auth is deliberately NOT installed in S1.
    # Installing it would pull in contenttypes/perm/group tables that are not
    # part of the frozen PLAN §5.4 schema. Password hashing (hashers) and
    # AbstractBaseUser work without the auth app installed; S4/S5 use our own
    # sessions model and cookie handling, not Django's session framework.
    #
    # django.contrib.postgres IS installed: it registers the OpClass expression
    # wrapper classes required for GinIndex(OpClass(...)) to render valid SQL.
    # It defines no models/tables, so the frozen schema stays untouched.
    "django.contrib.postgres",
    "core",
    "accounts",
    "groups",
    "tasks",
    "notifications",
    "files",
]

# No admin/contenttypes/sessions in the MVP schema (PLAN §5.4 table is the
# frozen contract). Adding Django admin = a change request (RULES.md §1.2).
MIDDLEWARE: list[str] = []  # S2 adds security headers/problem-json middleware.

ROOT_URLCONF = "config.urls"
TEMPLATES: list[dict] = []

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"  # unused: we set explicit PKs everywhere


def _database_config() -> dict:
    """DATABASE_URL=postgres://user:pass@host:port/name (12-factor style)."""
    url = _env("DATABASE_URL", "postgres://groupy:groupy@127.0.0.1:5432/groupy")
    parts = urlsplit(url)
    if parts.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must be a postgres:// URL")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parts.path.lstrip("/"),
        "USER": parts.username or "",
        "PASSWORD": parts.password or "",
        "HOST": parts.hostname or "127.0.0.1",
        "PORT": parts.port or 5432,
        "CONN_MAX_AGE": 60,
    }


DATABASES = {"default": _database_config()}

# Time (RULES.md §4.23): UTC everywhere, timestamptz columns, IANA zone per event.
TIME_ZONE = "UTC"
USE_TZ = True
USE_I18N = False

# S4 configures Argon2id as PASSWORD_HASHERS[0]; keep Django defaults until then.

# Dev-only switch for the seed command (RULES.md §4.28 / §7.38).
SEED_ALLOWED = _env("SEED_ALLOWED", "false").lower() in ("1", "true", "yes")
