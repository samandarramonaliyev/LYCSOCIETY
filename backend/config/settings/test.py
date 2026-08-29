from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("DJANGO_DEBUG", "false")
os.environ.setdefault("DJANGO_DB_NAME", "lyc_society")
os.environ.setdefault("DJANGO_DB_USER", "lyc_society")
os.environ.setdefault("DJANGO_DB_PASSWORD", "lyc_society")
os.environ.setdefault("DJANGO_DB_HOST", "127.0.0.1")
os.environ.setdefault("DJANGO_DB_PORT", "5432")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")

from .base import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
