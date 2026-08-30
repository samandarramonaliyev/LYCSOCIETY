from __future__ import annotations

from pathlib import Path
import re

from django.core.exceptions import ImproperlyConfigured

from .environment import env, env_bool, env_int, env_list

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=("localhost", "127.0.0.1") if DEBUG else (),
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.common.apps.CommonConfig",
    "apps.identity.apps.IdentityConfig",
    "apps.lyceums.apps.LyceumsConfig",
    "apps.profiles.apps.ProfilesConfig",
    "apps.clubs.apps.ClubsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.telegram_integration.apps.TelegramIntegrationConfig",
    "apps.meetings.apps.MeetingsConfig",
    "apps.reports.apps.ReportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# PostgreSQL is mandatory. Do not add a SQLite fallback for local development or tests.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DJANGO_DB_NAME", required=True),
        "USER": env("DJANGO_DB_USER", required=True),
        "PASSWORD": env("DJANGO_DB_PASSWORD", required=True),
        "HOST": env("DJANGO_DB_HOST", default="127.0.0.1"),
        "PORT": env("DJANGO_DB_PORT", default="5432"),
        "CONN_MAX_AGE": env_int("DJANGO_DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": env("DJANGO_DB_SSLMODE", default="prefer")},
    }
}

if database_test_name := env("DJANGO_DB_TEST_NAME", default=""):
    DATABASES["default"]["TEST"] = {"NAME": database_test_name}

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

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Development/test processes use a process-local cache. Production overrides this
# with a shared Redis-compatible backend and refuses to start without it.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "lyc-society-development",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "identity.User"

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_WEBHOOK_ENABLED = env_bool("TELEGRAM_WEBHOOK_ENABLED", default=False)
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
TELEGRAM_INIT_DATA_MAX_AGE_SECONDS = env_int(
    "TELEGRAM_INIT_DATA_MAX_AGE_SECONDS",
    default=300,
)
TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS = env_int(
    "TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS",
    default=30,
)

if TELEGRAM_INIT_DATA_MAX_AGE_SECONDS <= 0:
    raise ImproperlyConfigured("TELEGRAM_INIT_DATA_MAX_AGE_SECONDS must be positive.")
if TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS < 0:
    raise ImproperlyConfigured("TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS cannot be negative.")
if TELEGRAM_WEBHOOK_ENABLED and not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", TELEGRAM_WEBHOOK_SECRET):
    raise ImproperlyConfigured(
        "TELEGRAM_WEBHOOK_SECRET must contain 1-256 letters, numbers, underscores, or hyphens when webhook runtime is enabled."
    )
if TELEGRAM_WEBHOOK_ENABLED and not TELEGRAM_BOT_TOKEN:
    raise ImproperlyConfigured(
        "TELEGRAM_BOT_TOKEN must be set when TELEGRAM_WEBHOOK_ENABLED is true."
    )

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", default=31_536_000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.api.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "telegram_auth": env("TELEGRAM_AUTH_THROTTLE_RATE", default="20/hour"),
        "student_verification": env("STUDENT_VERIFICATION_THROTTLE_RATE", default="5/hour"),
        "join_request": env("JOIN_REQUEST_THROTTLE_RATE", default="20/hour"),
        "report_submission": env("REPORT_SUBMISSION_THROTTLE_RATE", default="10/hour"),
        "telegram_invite": env("TELEGRAM_INVITE_THROTTLE_RATE", default="10/hour"),
    },
    "EXCEPTION_HANDLER": "apps.common.api.exception_handler",
}

TEST_RUNNER = "config.test_runner.BackendDiscoverRunner"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
