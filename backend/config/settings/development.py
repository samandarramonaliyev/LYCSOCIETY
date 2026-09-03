from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .environment import env, env_bool, env_int, load_development_environment


# A local .env is a development convenience only. It is loaded before base.py
# reads settings and never overrides explicit PowerShell/IDE environment values.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_development_environment(PROJECT_ROOT / ".env")
os.environ.setdefault("DJANGO_DEBUG", "true")

from .base import *  # noqa: E402,F403


# This local-browser login is intentionally unavailable outside development.py.
LOCAL_DEV_AUTH_AVAILABLE = True
LOCAL_DEV_AUTH_ENABLED = env_bool("LOCAL_DEV_AUTH_ENABLED", default=False)
LOCAL_DEV_TELEGRAM_USER_ID = env_int("LOCAL_DEV_TELEGRAM_USER_ID", default=123_456_789)
if LOCAL_DEV_TELEGRAM_USER_ID <= 0:
    raise ImproperlyConfigured("LOCAL_DEV_TELEGRAM_USER_ID must be a positive integer.")


def _development_tunnel_origin(raw_origin: str) -> str:
    """Return one exact Cloudflare Quick Tunnel origin or reject it safely."""

    try:
        parsed = urlparse(raw_origin)
        hostname = parsed.hostname or ""
        parsed.port  # Validate a supplied port before accepting the origin.
    except ValueError as exc:
        raise ImproperlyConfigured("DEV_TUNNEL_ORIGIN must be a valid HTTPS origin.") from exc

    if not (
        parsed.scheme == "https"
        and hostname.lower().endswith(".trycloudflare.com")
        and not parsed.username
        and not parsed.password
        and not parsed.path.rstrip("/")
        and not parsed.query
        and not parsed.fragment
    ):
        raise ImproperlyConfigured(
            "DEV_TUNNEL_ORIGIN must be one exact https://<name>.trycloudflare.com origin."
        )
    return f"https://{parsed.netloc}"


if raw_tunnel_origin := env("DEV_TUNNEL_ORIGIN", default=""):
    tunnel_origin = _development_tunnel_origin(raw_tunnel_origin)
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, tunnel_origin]))  # noqa: F405
