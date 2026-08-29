# LYC Society backend

This repository currently contains Phase 2 of the LYC Society backend: Django project configuration, PostgreSQL settings, foundational identity/lyceum/profile models, Telegram Mini App session authentication, atomic official-record verification, trusted-operator roster import, Django Admin, and tests.

It deliberately does not include the React Mini App, Telegram bot process, clubs, meetings, announcements, notifications, reports, or moderation workflows.

## Prerequisites

- Python 3.12 or 3.13
- PostgreSQL
- A database role permitted to create/use the development database and, when running tests, the test database

## Local setup

1. Create and activate a virtual environment.
2. Install the project dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

3. Copy `.env.example` to `.env`, replace every placeholder, and load it into the current PowerShell session:

   ```powershell
   Copy-Item .env.example .env
   . .\scripts\Load-LycEnvironment.ps1
   ```

   Set `TELEGRAM_BOT_TOKEN` in that environment before running Django. `.env` is a local convenience file. Django reads operating-system environment variables; deployment must use a proper secret manager or deployment environment configuration.

4. Create the PostgreSQL database and run migrations:

   ```powershell
   createdb -U lyc_society lyc_society
   python backend/manage.py migrate
   python backend/manage.py createsuperuser
   python backend/manage.py runserver
   ```

5. Run the test suite against PostgreSQL:

   ```powershell
   python backend/manage.py test --settings=config.settings.test
   python backend/manage.py makemigrations --check --dry-run
   python backend/manage.py check --deploy --settings=config.settings.production
   ```

The application intentionally has no SQLite fallback. If PostgreSQL is unavailable, do not claim the database schema or database-backed tests were verified.

## Useful routes

- `/admin/` — Django Admin for foundational models.
- `/api/v1/health/` — unauthenticated database health check.

- `GET /api/v1/auth/csrf/` then `POST /api/v1/auth/telegram/` — obtain a CSRF token, validate raw Telegram Mini App `initData`, and establish a session.
- `POST /api/v1/auth/logout/` and `GET /api/v1/auth/me/` — session lifecycle and safe onboarding state.
- `GET /api/v1/verification/lyceums/`, `GET /api/v1/verification/status/`, and `POST /api/v1/verification/claim/` — onboarding lyceum choices, verification state, and exact roster-match claim.

## Official roster import

Trusted server operators may import a UTF-8 CSV only through Django's management command:

```powershell
python backend/manage.py import_student_records path\to\students.csv
```

The CSV must include these required headers: `lyceum`, `first_name`, `last_name`, and `group`; `external_student_key` is the only optional additional header. `lyceum` must be an existing lyceum code. The importer reports `Imported`, `Skipped`, and `Errors`; any malformed or conflicting row aborts the whole import without modifying roster data.

Read `AGENTS.md` and the files in `docs/` before modifying the backend.
