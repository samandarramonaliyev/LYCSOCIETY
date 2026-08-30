# Local Windows development

This project is PostgreSQL-only. Development settings automatically load
`PROJECT_ROOT/.env`; the file is ignored by Git and never loaded by
`config.settings.production`. Process/IDE environment variables take precedence over
the file, which lets CI and production inject secrets normally. `python
backend/manage.py test` selects test settings automatically, reads only local database
connection values from `.env`, and replaces Telegram credentials/webhook state with fake
test values so tests never contact a real bot.

## Configuration inventory

| Variable | Development behavior | Production behavior |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Defaults to `config.settings.development` via Django entry points | Set explicitly to `config.settings.production` |
| `DJANGO_SECRET_KEY` | Required in `.env` | Required from deployment secrets |
| `DJANGO_DEBUG` | Defaults to `true` in development | Must be `false` |
| `DJANGO_ALLOWED_HOSTS` | Defaults to local hosts while debug is enabled | Required exact hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Configure exact local Vite origins; the tunnel is added by `DEV_TUNNEL_ORIGIN` | Required exact HTTPS origins |
| `DEV_TUNNEL_ORIGIN` | Optional exact `https://<name>.trycloudflare.com` origin, development only | Not used or accepted |
| `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD` | Required PostgreSQL connection values | Required PostgreSQL connection values |
| `DJANGO_DB_HOST`, `DJANGO_DB_PORT` | Default `127.0.0.1` / `5432` | Deployment values required in practice |
| `DJANGO_DB_SSLMODE` | Default `prefer` | Use provider-appropriate TLS, preferably `verify-full` |
| `DJANGO_DB_CONN_MAX_AGE` | Defaults to `60` seconds | Same setting if overridden |
| `DJANGO_DB_TEST_NAME` | Optional explicit test database name | Optional only for controlled test runs |
| `TELEGRAM_BOT_TOKEN` | Optional until real Mini App authentication/Bot API testing; missing token fails authentication closed | Always required, server-side only |
| `TELEGRAM_WEBHOOK_ENABLED` | Defaults to `false` | Set `true` only when the HTTPS webhook is configured |
| `TELEGRAM_WEBHOOK_SECRET` | Required only when webhook runtime is enabled | Required when webhook runtime is enabled; secret-manager supplied |
| `TELEGRAM_INIT_DATA_MAX_AGE_SECONDS`, `TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS` | Defaults `300` / `30` | Same bounded validation controls |
| `TELEGRAM_AUTH_THROTTLE_RATE`, `STUDENT_VERIFICATION_THROTTLE_RATE`, `JOIN_REQUEST_THROTTLE_RATE`, `REPORT_SUBMISSION_THROTTLE_RATE`, `TELEGRAM_INVITE_THROTTLE_RATE` | Optional throttle overrides | Optional approved policy overrides |
| `DJANGO_CACHE_URL`, `DJANGO_CACHE_SOCKET_TIMEOUT_SECONDS` | Local-memory cache is used; neither is needed | Redis-compatible URL is required; timeout defaults to `2` |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS` | Relevant only if debug is explicitly disabled | Security controls, normally left enabled |
| `DJANGO_HSTS_SECONDS`, `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD`, `DJANGO_TRUST_PROXY_SSL_HEADER` | Not needed for normal local development | Strict production-only controls |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_FORWARDED_ALLOW_IPS` | Not used on Windows/Vite development | Gunicorn process settings on the Linux deployment host |
| `VITE_API_BASE_URL` | Optional `frontend/.env` browser-safe API base; defaults to `/api/v1` | Browser-safe build-time value only |

## PostgreSQL setup

Create an ordinary local role/database using an existing local PostgreSQL
administrator account. Substitute a strong local password and put the same value only
in `.env`; never commit it.

```sql
CREATE ROLE lyc_society LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE lyc_society OWNER lyc_society;
```

For Django's default test-database creation, grant the local role `CREATEDB`, or
create a separate test database and set `DJANGO_DB_TEST_NAME`. PostgreSQL 18 is
supported through Django's PostgreSQL backend; SQLite is intentionally not a fallback.

## Quick Tunnel notes

Run a Quick Tunnel against Vite, not Django: `cloudflared tunnel --url
http://127.0.0.1:5173`. Vite proxies every `/api` request, including
`/api/v1/telegram/webhook/`, to `http://127.0.0.1:8000`. With `changeOrigin: true`,
Django receives the local backend host; it therefore needs local `ALLOWED_HOSTS`, while
CSRF must trust the exact public tunnel origin. Set `DEV_TUNNEL_ORIGIN` after each
tunnel restart and restart Django.

Do not place Telegram, Django, database, or webhook secrets in `frontend/.env` or any
`VITE_*` value.
