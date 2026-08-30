# LYC Society

LYC Society is a private Telegram Mini App and Django API for verified lyceum students. The MVP includes Telegram session authentication, provisional official-roster verification, profiles and interests, lyceum-scoped clubs and membership workflows, meetings and RSVP, announcements, notifications and preferences, Telegram group linking, reporting, moderation, and Django Admin.

Phases 0–7 and Phase 8A are implemented. Phase 8A adds final security hardening, adversarial and PostgreSQL concurrency coverage, dependency audits, and CI. It does not deploy the application; production work remains Phase 8B.

## Prerequisites

- Python 3.12 or 3.13
- PostgreSQL
- Node.js 24 LTS and npm
- A PostgreSQL role permitted to create/use both the development and test databases

## Backend setup

1. Create and activate a virtual environment, then install the project:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e ".[audit]"
   ```

2. Copy `.env.example` to `.env`, replace every placeholder, and load it:

   ```powershell
   Copy-Item .env.example .env
   . .\scripts\Load-LycEnvironment.ps1
   ```

   Local `.env` files are ignored. Production must obtain `DJANGO_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, and database credentials from deployment environment or secret management. Never use a production bot token in tests.

3. Create the PostgreSQL database and initialize Django:

   ```powershell
   createdb -U lyc_society lyc_society
   python backend/manage.py migrate
   python backend/manage.py createsuperuser
   python backend/manage.py runserver
   ```

## Frontend setup

```powershell
Set-Location frontend
npm ci
npm run dev
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

## Official roster import

Trusted server operators may import a UTF-8 CSV only through Django's management command:

```powershell
python backend/manage.py import_student_records path\to\students.csv
```

Required headers are `lyceum`, `first_name`, `last_name`, and `group`; `external_student_key` is optional. Any malformed or conflicting row aborts the entire import. Name/surname/group matching is a pilot limitation, not strong identity proof; replace it with a school-issued one-time secret before a wider launch.

Read `AGENTS.md` and the source-of-truth files in `docs/` before modifying the project. Deployment, production headers/origins, shared cache, backups, monitoring, and incident-response work belong to Phase 8B.

For Phase 8B release preparation, use [the deployment runbook](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/DEPLOYMENT.md:1), [the smoke checklist](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/SMOKE_TEST.md:1), [the privacy checklist](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/PRIVACY_RETENTION.md:1), and [the incident runbook](C:/Users/user/OneDrive/Desktop/LYCSOCIETY/docs/INCIDENT_RESPONSE.md:1). The repository includes a secret-protected inbound Telegram webhook; configure it only after HTTPS deployment and non-production client/group permission testing.
