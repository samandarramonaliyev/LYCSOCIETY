# LYC Society production deployment runbook

This is the Phase 8B release-preparation runbook for a controlled pilot. It describes
configuration and operator actions; it does not provision cloud resources, purchase a
domain, or contact Telegram. The recommended topology is intentionally small:

```text
Telegram Mini App / browser
          |
      HTTPS reverse proxy (one public origin)
          |-- /       -> frontend/dist (static SPA)
          |-- /api/   -> Gunicorn Django WSGI service
          `-- /admin/ -> Gunicorn Django WSGI service
                 |\
                 | `-> managed PostgreSQL (TLS)
                 `---> managed Redis-compatible cache (TLS)
```

Use one backend service and a managed PostgreSQL database plus a managed Redis-compatible
cache. A same-origin reverse proxy keeps cookies, CSRF, CORS, and CSP simple. If a separate
frontend origin is later required, add that exact HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`
and configure credentialed CORS explicitly; never use wildcard origins.

## Required configuration

Set `DJANGO_SETTINGS_MODULE=config.settings.production` and `DJANGO_DEBUG=false`. Required
values are `DJANGO_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `DJANGO_DB_NAME`,
`DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, `DJANGO_DB_PORT`,
`DJANGO_DB_SSLMODE`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
`DJANGO_CACHE_URL`. `DJANGO_ALLOWED_HOSTS` must be exact hostnames and trusted origins must
be exact HTTPS origins. `rediss://` is preferred for the cache and `verify-full` is preferred
for PostgreSQL when the provider supports certificate verification.

When enabling inbound updates, also set `TELEGRAM_WEBHOOK_ENABLED=true` and a newly
generated `TELEGRAM_WEBHOOK_SECRET` from secret management. Production settings refuse
to start if webhook runtime is enabled without that secret. Rotate the BotFather token
before the first production configuration; never reuse a development token.

The production settings reject missing values, wildcard hosts/origins, non-HTTPS trusted
origins, non-Redis cache URLs, and non-positive cache timeouts. They force secure HTTP-only
session cookies, a readable CSRF cookie (required by the current JavaScript bootstrap),
`SameSite=Lax`, `SECURE_CONTENT_TYPE_NOSNIFF`, and a same-origin referrer policy.

`DJANGO_TRUST_PROXY_SSL_HEADER=true` is permitted only when the named reverse proxy strips
and rewrites `X-Forwarded-Proto`; otherwise leave it false and terminate HTTPS directly at
Django's trusted boundary. Do not accept arbitrary forwarded headers.

HSTS starts in staged mode (`DJANGO_HSTS_SECONDS=86400`, include-subdomains and preload false).
After all subdomains are HTTPS-only and verified, increase the max-age and explicitly opt in
to include-subdomains/preload. Do not submit a domain to browser preload casually.

The frontend production value remains `VITE_API_BASE_URL=/api/v1`. Every `VITE_*` value is
public and may contain only browser-safe configuration. The bot token, Django secret,
database credentials, and cache credentials must never be present in frontend variables.

## Build and process

```powershell
Set-Location frontend
npm ci
npm run lint
npm run test
npm run build
Set-Location ..
python -m pip install -e ".[production,audit]"
python backend/manage.py check --deploy --settings=config.settings.production
python backend/manage.py makemigrations --check --dry-run --settings=config.settings.production
python backend/manage.py migrate --settings=config.settings.production
python backend/manage.py collectstatic --noinput --settings=config.settings.production
gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
```

`runserver` and the Vite development server are local-only. The checked-in
`deploy/gunicorn.conf.py` uses two conservative synchronous workers by default, bounded
timeouts, request recycling, stdout/stderr logging, and a non-wildcard forwarded-IP policy.
Tune worker count to the provider's memory and CPU rather than copying a large-host recipe.

The reverse proxy should serve `frontend/dist`, `backend/staticfiles`, and proxy `/api/` and
`/admin/` to Gunicorn. It must set `Host`, `X-Forwarded-For`, and an overwritten
`X-Forwarded-Proto`. Serve the SPA with a history fallback to `index.html`; do not expose
source maps or `.env` files. Add a CSP at the static frontend boundary after Telegram client
testing, starting with a report-only policy. A practical candidate is `default-src 'self';
script-src 'self' https://telegram.org; connect-src 'self'; img-src 'self' https: data:;
style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`.
Do not add `unsafe-eval` or wildcard sources.

Gunicorn is a POSIX process server; this Windows development workstation can only compile and
inspect the configuration, not launch Gunicorn. Validate the service command on the selected
Linux/container host as part of the deployment rehearsal.

## Database and cache operations

PostgreSQL is mandatory. Use a non-superuser application role; a separate migration role is
preferred, but using the application role for a small pilot is an accepted operational tradeoff.
Apply committed migrations explicitly during release and never run `makemigrations` in the
deployment process. CI already fails on migration drift.

Enable managed PostgreSQL backups with a documented retention period and point-in-time recovery
where available. Before pilot traffic, restore a recent backup into a separate test database,
run migrations and health checks, and verify a few non-sensitive record counts. Never use the
first restore rehearsal to overwrite production.

Production Redis must be shared by every backend worker. It stores Telegram replay keys and
DRF throttle state. The application fails closed when the replay cache is unavailable and
returns a temporary throttling response when throttle storage fails; logs contain only an
operation and exception category. A cache outage is still an operational incident because
authentication and sensitive writes become unavailable. Do not silently switch production to
the local-memory backend.

## Telegram setup and known runtime boundary

Create a fresh production bot token in BotFather; do not reuse a development token that may
have been exposed. Set the production Mini App Menu Button URL to the stable HTTPS frontend
origin (for example, `https://app.example.com/`) and remove localhost, tunnel, and temporary
URLs from production configuration. Keep the token only in the deployment secret manager.

The Django service includes the inbound webhook at `/api/v1/telegram/webhook/`; Gunicorn
serves it through the same HTTPS reverse proxy as the API. It is still not configured or
deployed by this repository change. After the public HTTPS route and secrets are ready, run
`python backend/manage.py configure_telegram_webhook --base-url https://app.example.com`.
The command sets the secret header separately and subscribes only to `message` and
`chat_join_request`; it does not put the bot token in the URL. Inspect safe operational
status with `python backend/manage.py telegram_webhook_status`. Use `--delete` only for
intentional disablement. Do not run these commands in CI or against a real bot from tests.

Use a non-production test group for real permission testing: add the bot as administrator,
verify `can_invite_users` and message capabilities, complete a link challenge, generate a
join-request invite, verify approval rechecks active membership, and unlink. Test Android,
iOS, Desktop, and a normal browser fallback where available; record unavailable platforms
instead of claiming coverage.

## Release sequence

1. Merge only a green pull request; protect `main` with required CI checks.
2. Create the new BotFather token and store all secrets in the provider secret manager.
3. Provision PostgreSQL with TLS, backups, a non-superuser role, and the pilot database.
4. Provision managed Redis with TLS, authentication, and network restrictions.
5. Configure exact hosts/origins, proxy trust, staged HSTS, and same-origin frontend API path.
6. Deploy the backend service and run `check --deploy`, migration drift check, migrations, and `collectstatic`.
7. Build and publish `frontend/dist` through the HTTPS reverse proxy.
8. Configure the stable BotFather Menu Button URL, then configure the deployed HTTPS
   webhook with the management command and inspect its status.
9. Run the smoke checklist in `docs/SMOKE_TEST.md` using test accounts and a test group.
10. Start with a small verified-student pilot and monitor errors, authentication failures,
    cache health, database health, and Telegram delivery categories.

## Rollback and maintenance

Prefer a version rollback to the prior application artifact. Check migration compatibility
before rolling code back; do not reverse a destructive migration without a verified backup.
If a migration is not backward-compatible, keep the forward schema and roll back only the
application after confirming old code can read it. A short controlled maintenance window is
acceptable for this pilot; zero-downtime orchestration is not required.

The minimum rollback decision is: stop rollout, preserve logs/metrics, identify the last known
good artifact, verify database backup availability, restore application version, and run health
and smoke checks. Database restoration is an exceptional recovery action performed into a safe
target first, never an automatic blanket deletion.

## Release commands and audit

From the repository root, run backend checks/tests with PostgreSQL, frontend lint/tests/build,
`npm audit`, and `pip-audit`. The GitHub workflow repeats these checks with fake secrets and a
PostgreSQL service. Do not use `npm audit fix --force`. Keep `frontend/package-lock.json`
committed and update Python dependencies through reviewed `pyproject.toml` changes.
