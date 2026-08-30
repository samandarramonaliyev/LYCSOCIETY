# LYC Society Architecture

**Implementation status:** Phases 0–7 implement the complete MVP as a Django/PostgreSQL modular monolith with a React Mini App. Phase 8A hardens the existing authentication, tenant isolation, domain services, Telegram adapter, reporting, tests, and CI; deployment remains Phase 8B.

## 1. Recommended architecture

Use a modular monolith:

- One Django project and one PostgreSQL database.
- Django REST Framework for the Mini App API.
- A React/Vite/Tailwind frontend for the student Mini App.
- A Telegram integration module using a maintained Python framework such as aiogram.
- A small outbox/worker mechanism for Telegram side effects; keep it in the same repository and database rather than adding a message broker in MVP.
- Django Admin plus small custom staff views for the administrator panel. A separate admin frontend is not required for MVP.

This keeps transactions and business rules close to the data while preserving clear seams for a future bot process, notification worker, or additional client.

## 2. System context

```text
Telegram client
  ├─ opens React Mini App ───────┐
  └─ sends bot messages/actions ─┤
                                 v
                       Django application
                       ├─ DRF API
                       ├─ domain services
                       ├─ Telegram adapter/webhook
                       ├─ notification outbox worker
                       └─ staff admin panel
                                 │
                                 v
                             PostgreSQL

Django/worker ── HTTPS ── Telegram Bot API
```

The React application is a client of the API, not a trust boundary. Bot updates are also untrusted input until the adapter validates their shape and the domain service rechecks authorization.

## 3. Repository structure

The repository contains the implemented MVP boundaries below. They share one database but retain separate services, serializers, and adapters.

```text
backend/
  manage.py
  config/
    settings/
    urls.py
    asgi.py
    wsgi.py
  apps/
    common/              # shared primitives, errors, audit, pagination
    identity/            # users, sessions, Telegram authentication
    lyceums/             # lyceums and official student records
    profiles/            # editable profile data and interest tags
    clubs/               # clubs, memberships, and join requests
    notifications/       # notifications, preferences, outbox delivery
    moderation/          # reports, review actions, suspensions
    telegram_integration/# bot adapters, handlers, group linking
  tests/
    unit/
    api/
    security/
    integration/
  requirements/ or pyproject.toml

frontend/
  src/
    app/
    api/
    features/
    components/
    telegram/
    styles/
  public/
  package.json

docs/
```

Keep domain services in the relevant app or in a small shared service module. Do not create a generic “services” dumping ground.

## 4. Backend request flow

1. Django receives the request and authenticates the session.
2. Authentication resolves the application user from the validated Telegram identity.
3. A request-scoped authorization helper resolves the user’s verified student and lyceum, or rejects the request.
4. The view/serializer validates shape and field-level input.
5. A domain service performs state checks, object-level permissions, and the transaction.
6. The service emits in-app notification rows and/or outbox events after the domain mutation is committed.
7. The response serializer applies role and lyceum visibility rules.

For bot callbacks and commands, the Telegram adapter maps the Telegram actor to the application user, then calls the same domain service used by the API. It must not implement a second copy of join, approval, or membership rules.

## 5. Domain modules

### Implemented in Phases 1–2: Identity and lyceums

Own validated Telegram identity binding, secure server-side sessions, user suspension, official roster imports, exact roster-match verification, atomic record claims, verification throttling, and the derived verified-student/lyceum context.

### Implemented in Phases 1–3: Profiles

Own editable profile fields and structured interest tags. Verified fields are read from the official student record and cannot be updated by the profile API. The profile serializer accepts only plain-text about/hobbies, an HTTPS photo reference, and active interest IDs (maximum ten). The profile API is self-only and uses `IsVerifiedActiveStudent`.

Lyceum isolation is a shared service boundary in `lyceums.services.scoping`. `get_verified_lyceum(user)` derives the active tenant from the user's official record; `scope_queryset_to_verified_lyceum(...)` applies that value to future querysets. Neither helper accepts a client-supplied lyceum identifier.

### Clubs

Own club lifecycle, ownership, memberships, join requests, and club-scoped authorization. Club creation and join acceptance lock the relevant user rows; discovery and detail querysets derive lyceum from the verified student record.

### Planned: Notifications

Own notification preferences, in-app notification records, delivery outbox records, retry state, and deduplication. It receives domain events or explicit service calls; it does not decide whether a user was allowed to join a club.

### Planned: Moderation

Own reports, report resolution, suspensions, archive actions, and the audit trail for privileged decisions.

### Telegram integration

Own raw update parsing, webhook verification, Bot API calls, callback/action mapping, group-linking setup, and group join-request handling. It stores Telegram-specific identifiers in integration tables and calls domain services for authorization.

## 6. Authorization model

Use layered authorization:

- **Authentication:** Is there a valid session derived from Telegram `initData`?
- **Account state:** Is the user verified and not suspended?
- **Lyceum scope:** Does the target object belong to the user’s verified lyceum?
- **Role/object permission:** Is the user the owner, an active member, a moderator, or an administrator for this object?
- **Action/state permission:** Is this transition valid from the current status?

Administrators are staff accounts with explicit Django permissions/groups. They may operate across lyceums only through staff routes and audited domain services. A normal student never receives a client-controlled scope parameter that can broaden access.

## 7. Data isolation strategy

Every club, membership, join request, meeting, announcement, report target, and Telegram group link resolves to a lyceum through its club or explicit relation. User-facing querysets always begin from the authenticated student’s verified lyceum. Detail endpoints repeat the same scope check; they must not rely on the list endpoint having hidden an object.

Use code review and tests to enforce the rule that any new private entity must either have a direct `lyceum_id` or an unambiguous path to one.

## 8. Current API foundation

DRF is configured with session authentication, an authenticated-by-default permission policy, JSON rendering, page-number pagination (20 default / 100 maximum), throttling, and a non-leaking error envelope. The implemented API also includes verified profile routes, active interest selection, scoped club discovery/creation/detail, owner moderation, memberships, and join-request actions. All club routes derive lyceum from the verified student record.

`IsVerifiedActiveStudent` is the reusable permission for student-facing routes. It requires an authenticated, active account with an active claimed official record and an active lyceum.

## 9. Side effects and consistency

The database transaction is authoritative for verification, club approval, membership, meetings, and announcements. Telegram messages, invite-link creation, and group approvals are external side effects.

Use an outbox row written in the same transaction as the domain change. A worker claims pending rows, performs an idempotent Bot API operation, records success/failure, and retries transient failures with backoff. A permanent failure is visible to administrators and does not undo the committed domain change.

## 10. Deployment baseline

For MVP, deploy the single-service topology and runbook in `docs/DEPLOYMENT.md`:

- Django ASGI/WSGI application behind HTTPS and a reverse proxy.
- PostgreSQL with automated backups and restricted network access.
- Static frontend assets served from the same origin or a tightly configured HTTPS origin.
- The Django application exposes a secret-validated HTTPS webhook for the only required
  inbound updates: `message` for group-link commands and `chat_join_request` for
  approved-member access. It persists update IDs for cross-worker idempotency and
  invokes the existing group-link/invite domain services; it does not duplicate club
  authorization rules.
- A worker/cron process using the same backend code for outbox delivery and scheduled meeting reminders.

Use environment/secret-manager configuration for database credentials, Django secret key, Telegram bot token, webhook secret when the webhook is enabled, allowed origins, cache URL, and operational settings. Never put these values in frontend build variables.

## 11. Explicit non-goals

Do not add WebSockets, Redis/Celery as a job broker, Elasticsearch, a separate identity provider, a recommendation service, or a second frontend until measured requirements justify them and the decision is recorded. A managed Redis-compatible cache is an approved Phase 8B operational dependency for replay/throttle state.
Phase 5A introduces separate `telegram_integration` and `notifications` modules.
Core club services create durable notifications; a management command delivers them
through the focused Telegram client, keeping external failures outside transactions.
