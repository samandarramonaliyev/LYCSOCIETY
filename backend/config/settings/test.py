from __future__ import annotations

import os
from pathlib import Path

from .environment import load_development_environment


# Local tests use the same ignored database connection values as development.
# Test-only security values below always replace any local Telegram credentials.
load_development_environment(Path(__file__).resolve().parents[3] / ".env")

os.environ["DJANGO_SECRET_KEY"] = "test-only-secret-key-not-for-production"
os.environ["DJANGO_DEBUG"] = "false"
os.environ.setdefault("DJANGO_DB_NAME", "lyc_society")
os.environ.setdefault("DJANGO_DB_USER", "lyc_society")
os.environ.setdefault("DJANGO_DB_PASSWORD", "lyc_society")
os.environ.setdefault("DJANGO_DB_HOST", "127.0.0.1")
os.environ.setdefault("DJANGO_DB_PORT", "5432")
os.environ["TELEGRAM_BOT_TOKEN"] = "test-bot-token"
os.environ["TELEGRAM_WEBHOOK_ENABLED"] = "false"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-webhook-secret"

from .base import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
