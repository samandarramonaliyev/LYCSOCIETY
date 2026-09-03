# LYC Society

LYC Society is a private Telegram Mini App and Django API for verified lyceum students. The MVP includes Telegram session authentication, provisional official-roster verification, profiles and interests, lyceum-scoped clubs and membership workflows, meetings and RSVP, announcements, notifications and preferences, Telegram group linking, reporting, moderation, and Django Admin.

Phases 0–7 and Phase 8A are implemented. Phase 8A adds final security hardening, adversarial and PostgreSQL concurrency coverage, dependency audits, and CI. It does not deploy the application; production work remains Phase 8B.

## Prerequisites

- Python 3.13
- PostgreSQL 18 (any supported local PostgreSQL version using Django's backend is suitable)
- Node.js 24 LTS and npm
- A PostgreSQL role permitted to create/use both the development and test databases

## Backend setup

1. Create and activate the project virtual environment, then install the project:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e ".[audit]"
   ```

2. Copy `.env.example` to the project root `.env`. Development settings load this
   file automatically for every Django command; do not run a PowerShell environment
   loader or re-enter variables per terminal.

   ```powershell
   .\.venv\Scripts\Activate.ps1
   Copy-Item .env.example .env
   ```

   Edit the local Django secret and the PostgreSQL name/user/password. Generate a
   secret without writing it to source control:

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Add a non-production `TELEGRAM_BOT_TOKEN` only when testing real Telegram Mini
   App authentication or Bot API behavior. Local `.env` files are ignored.
   Production never auto-loads `.env`: it must obtain secrets from its deployment
   environment or secret manager. Never use a production bot token in tests.

3. Create the local PostgreSQL role/database as documented in
   [Local Windows development](docs/LOCAL_DEVELOPMENT.md), then initialize Django:

   ```powershell
   python backend/manage.py check
   python backend/manage.py migrate
   python backend/manage.py createsuperuser
   python backend/manage.py runserver 127.0.0.1:8000
   ```

   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-check.ps1`
   performs the Django check and migration-drift check without reading or printing
   secret values. Pass `-Frontend` to include the frontend type check.

## Frontend setup

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev -- --host 0.0.0.0
```

The frontend uses the centralized API client in `frontend/src/api/client.ts`. Cookie credentials and CSRF headers must remain enabled; Telegram `initDataUnsafe` and client-supplied identity or lyceum values are never authoritative.

## Validation

Backend validation requires PostgreSQL; the project intentionally has no SQLite fallback:

```powershell
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py migrate
python backend/manage.py test
python -m pip_audit --local
```

Frontend validation:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run test
npm run build
npm audit
```

GitHub Actions repeats these checks with PostgreSQL and fake test-only secrets. See [the CI workflow](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/.github/workflows/ci.yml:1).
`python backend/manage.py test` automatically uses test settings and fake Telegram
credentials while retaining the local PostgreSQL connection values from `.env`.

## Local Telegram Mini App demo

Use a non-production bot and keep all three terminals open:

```powershell
# Terminal 1: repository root
.\.venv\Scripts\Activate.ps1
python backend/manage.py runserver 127.0.0.1:8000

# Terminal 2
Set-Location frontend
npm.cmd run dev -- --host 0.0.0.0

# Terminal 3
cloudflared tunnel --url http://127.0.0.1:5173
```

Copy the generated `https://…trycloudflare.com` URL into
`DEV_TUNNEL_ORIGIN` in root `.env`, restart Django, and set the BotFather Menu Button
to that URL. Vite already permits only the local host and `*.trycloudflare.com`, and
its `/api` proxy sends requests to Django at `127.0.0.1:8000`. Real Telegram
`initData` validation remains enabled. For an ordinary local browser, explicitly opt
in to the development-only local session in `.env` as documented in
[`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md); it never acts as Telegram
identity or student verification and is unavailable in production.

The tunnel URL changes after restart, so update both `.env` and BotFather each time.
The laptop and all three processes must remain running. This is development/demo only,
not production hosting.

Webhook delivery is optional for normal frontend work. For an intentional non-production
group test, set a real non-production bot token, `TELEGRAM_WEBHOOK_ENABLED=true`, and a
fresh `TELEGRAM_WEBHOOK_SECRET` in `.env`; then run
`python backend/manage.py configure_telegram_webhook --base-url <tunnel-url>` and
`python backend/manage.py telegram_webhook_status`. The same Vite `/api` proxy routes
`/api/v1/telegram/webhook/` to Django. Do not configure a real webhook in automated tests.

See [Local Windows development](docs/LOCAL_DEVELOPMENT.md) for the complete
environment-variable inventory, PostgreSQL test permissions, and tunnel/CSRF details.

## Official roster import

Trusted server operators may import a UTF-8 CSV only through Django's management command:

```powershell
python backend/manage.py import_student_records path\to\students.csv
```

Required headers are `lyceum`, `first_name`, `last_name`, and `group`; `external_student_key` is optional. Any malformed or conflicting row aborts the entire import. Name/surname/group matching is a pilot limitation, not strong identity proof; replace it with a school-issued one-time secret before a wider launch.

Read `AGENTS.md` and the source-of-truth files in `docs/` before modifying the project. Deployment, production headers/origins, shared cache, backups, monitoring, and incident-response work belong to Phase 8B.

For Phase 8B release preparation, use [the deployment runbook](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/DEPLOYMENT.md:1), [the smoke checklist](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/SMOKE_TEST.md:1), [the privacy checklist](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/PRIVACY_RETENTION.md:1), and [the incident runbook](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/INCIDENT_RESPONSE.md:1). The repository includes a secret-protected inbound Telegram webhook; configure it only after HTTPS deployment and non-production client/group permission testing.
