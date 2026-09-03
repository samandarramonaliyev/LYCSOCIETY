from __future__ import annotations

from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .environment import env, env_bool, env_int, env_list

if DEBUG:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_DEBUG must be false when using production settings.")

# Never read or honor local-browser authentication environment variables in production.
LOCAL_DEV_AUTH_AVAILABLE = False
LOCAL_DEV_AUTH_ENABLED = False

# Development may start without Telegram while a developer works on non-Telegram
# surfaces. Production always requires the real server-side credential.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", required=True)

blocked_host_names = {"localhost", "127.0.0.1", "::1"}


def _is_exact_production_host(host: str) -> bool:
    hostname = urlparse(f"//{host}").hostname or ""
    return bool(
        hostname
        and "*" not in host
        and hostname.lower() not in blocked_host_names
        and "trycloudflare.com" not in hostname.lower()
        and "ngrok" not in hostname.lower()
    )


ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS or any(not _is_exact_production_host(host) for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain exact production hostnames; wildcards are not allowed."
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
def _is_exact_https_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.hostname.lower() not in blocked_host_names
        and "trycloudflare.com" not in parsed.hostname.lower()
        and "ngrok" not in parsed.hostname.lower()
        and "*" not in origin
        and not parsed.username
        and not parsed.password
        and not parsed.path.rstrip("/")
        and not parsed.query
        and not parsed.fragment
    )


if not CSRF_TRUSTED_ORIGINS or any(
    not _is_exact_https_origin(origin) for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS must contain exact HTTPS origins without wildcards."
    )

cache_url = env("DJANGO_CACHE_URL", required=True)
if not cache_url.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("DJANGO_CACHE_URL must be a redis:// or rediss:// URL.")
cache_timeout = env_int("DJANGO_CACHE_SOCKET_TIMEOUT_SECONDS", default=2)
if cache_timeout <= 0:
    raise ImproperlyConfigured("DJANGO_CACHE_SOCKET_TIMEOUT_SECONDS must be positive.")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": cache_url,
        "TIMEOUT": 300,
        "OPTIONS": {
            "socket_timeout": cache_timeout,
            "socket_connect_timeout": cache_timeout,
        },
    }
}

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", default=86_400)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS", default=False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", default=False)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # The Mini App reads the CSRF cookie for X-CSRFToken.
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Only set this when the exact reverse proxy is trusted to overwrite the header.
if env_bool("DJANGO_TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if globals().get("CORS_ALLOW_ALL_ORIGINS", False):
    raise ImproperlyConfigured("Wildcard CORS is not permitted in production.")
