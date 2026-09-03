# LYC Society Security Model

Security is a product requirement, not a frontend feature. The backend and database enforce all identity, lyceum, role, and state rules.

## Phase 8A implementation status

The complete MVP through Phase 7 is implemented. Phase 8A hardens it with adversarial Telegram authentication tests, CSRF verb coverage, explicit IDOR and tenant-isolation tests, PostgreSQL concurrency tests, strict serializer allowlists, sensitive-action throttles, typed report targets, gated Telegram invites, dependency audits, and PostgreSQL-backed CI. Deployment remains out of scope until Phase 8B.

## 1. Trust boundaries

Untrusted inputs:

- Telegram Mini App `initData` and all Telegram update payloads until validated.
- Browser requests, route IDs, filters, body fields, and uploaded media.
- Telegram usernames, display names, and profile photos as identity claims.
- Admin-uploaded roster files until validated and reconciled.
- Bot API responses and delivery callbacks as external-system data.

Trusted sources after validation:

- The application session created from a valid, fresh Telegram payload.
- The database’s verified student binding and role/membership rows.
- Staff actions performed through authenticated staff permissions and audited services.

## 2. Telegram authentication

The implemented login flow is:

1. The same-origin Mini App requests `GET /api/v1/auth/csrf/`, which sets a CSRF cookie and returns a CSRF token.
2. It sends that token in `X-CSRFToken` with raw `Telegram.WebApp.initData` to `POST /api/v1/auth/telegram/`.
3. The backend parses the query-string fields without changing their signed representation.
4. It parses the query string once, rejects duplicate critical fields, derives the Telegram Web App secret as `HMAC_SHA256(key="WebAppData", message=bot_token)`, and validates the HMAC-SHA-256 hash using constant-time comparison.
5. It verifies a configurable bounded `auth_date` freshness window and small future-clock allowance.
6. It extracts the Telegram user ID from the validated payload and looks up the unique application user.
7. It creates/rotates a secure server-side session and returns only account state needed by the client.

For replay-risk reduction, the validated hash is stored only as a SHA-256-derived cache key for the freshness-window lifetime. A duplicate hash is rejected during that window; successful login rotates the Django session key. This cache control is intentionally a bounded mitigation rather than a long-term identity proof and must use a shared production cache when the application is deployed on multiple processes.

Never use `initDataUnsafe` as an authority, accept a frontend-supplied Telegram ID, log raw initialization data, or use a Telegram username as a stable identity. Never accept a normal browser request as proof of verification.

The optional local-browser development login is not an exception to the production
identity boundary. It exists only in `config.settings.development`, requires both
`DEBUG` and an explicit `LOCAL_DEV_AUTH_ENABLED` flag, retains CSRF protection, and
uses one server-configured fake ID rather than client input. Production settings force
the feature off even if the environment contains development variables. It creates an
unverified, non-staff local account and must never be used as verification proof.

Use a short freshness window appropriate for the product and allow re-authentication with newly generated Telegram data when expired. The default is five minutes with 30 seconds of future clock tolerance; both values are environment-configurable and covered by tests.

## 3. Session and browser controls

Prefer Django server-side session authentication for the same-origin production deployment:

- `Secure`, `HttpOnly`, appropriately scoped cookie.
- `SameSite=Lax` where compatible with the deployed Mini App; if deployment requires cross-site cookies, explicitly use `SameSite=None; Secure` and a strict allowlist.
- CSRF tokens on all cookie-authenticated state changes, including the session-creating Telegram login.
- Same-origin production serving or a tightly configured HTTPS frontend origin.
- No authentication tokens in localStorage.
- Session invalidation on suspension, account rebind, or security incident.

Set HTTPS, HSTS, a restrictive Content Security Policy, frame/embedding policy compatible with Telegram, secure referrer policy, and safe content-type headers. Configure CORS only for known development/production origins.

## 4. Verification security

- The official roster is staff-only data.
- Phase 2's approved transitional method matches a signed-in account to exactly one active, unclaimed record by normalized lyceum, first name, last name, and group. It uses no fuzzy matching.
- Lock or slow repeated failures; the API applies per-authenticated-account throttling and returns generic failures without record-match detail.
- Make claiming atomic: lock the user and candidate record(s), re-check state, then write the one-to-one binding and timestamp together.
- Do not reveal whether a guessed name/group exists. Return coarse verification outcomes.
- Prevent one Telegram identity from binding multiple records and one record from binding multiple accounts.
- Do not let profile PATCH or any public API mutate verified fields. The Phase 3 serializer rejects roster-owned aliases instead of mass-assigning them.
- Profile and interest routes require an active verified account. Their lyceum context is loaded from the active official record; client-supplied lyceum IDs are not authorization input.
- Profile photos are stored only as validated HTTPS references. The backend does not fetch arbitrary URLs or implement a media proxy in this phase.
- Keep verification attempts and staff changes auditable without recording raw authentication payloads or future verification secrets.

This roster-match method is not strong proof of ownership: anyone who knows another student's lyceum, name, and group may attempt a claim. A unique match is necessary but not sufficient proof. It is retained only for the explicit Phase 2 pilot scope, with generic errors, throttling, and administrator-only reset; replace it before wider deployment with an administrator-issued, single-use verification code or another administration-controlled secret. Do not implement a freely enumerable roster lookup.

## 5. Authorization and IDOR prevention

Every protected endpoint must perform:

1. authentication;
2. verified/non-suspended account check;
3. object lookup constrained to the caller’s permitted lyceum and visibility;
4. role/action permission check;
5. state-transition check;
6. transactional re-check for writes.

Never fetch an object by ID and authorize later as a separate convention. Build scoped querysets and repeat the scope inside domain services. A UUID reduces guessing but is not an authorization control.

Cross-lyceum denial applies to clubs, members, requests, meetings, announcements, reports, Telegram access, and any future child entity. Administrators use separate staff permissions and audited cross-lyceum operations.

## 6. Business-rule enforcement

Enforce the following in both service logic and database constraints where possible:

- one club per owner;
- owner membership is created with the club and counts toward the three active-membership limit;
- one active membership per `(club, user)` and one owner membership per club;
- one active verified binding per Telegram identity and roster record;
- one pending join request per user/club;
- no owner self-join;
- active memberships maximum three, including owner membership;
- only active same-lyceum clubs in normal discovery;
- rejection reason required for rejected clubs;
- only permitted roles can change club content or requests;
- a removed member cannot receive new group access.

Lock the user row for club creation, membership acceptance, and other operations that count active memberships. Do not rely on a frontend count.

## 7. Input, output, and content safety

- Apply server-side length, type, enum, and relationship validation.
- Sanitize or escape announcement and club content; do not render arbitrary HTML.
- Validate uploaded images by MIME/content, size, dimensions, and safe storage name. Store media outside executable paths.
- Rate-limit Telegram authentication and student verification now; later phases must also rate-limit reports, profile updates, club creation, join requests, Telegram actions, and notification-triggering actions.
- Club and join-request mutations reject client-supplied owner, lyceum, status, role, membership counts, and moderation fields.
- Use generic error responses that do not disclose roster membership, object existence, or staff-only state.
- Redact authorization headers, cookies, init data, verification codes, invite URLs, and personal data from logs.

## 8. Telegram data protection

- Store bot tokens only in secret management/environment configuration.
- Store Telegram IDs as protected operational identifiers; do not expose them in normal API responses.
- Do not persist generated member invite links. If a future capability requires persistence, document it first, encrypt at the application layer, and restrict decryption to the Telegram integration service.
- Never accept a chat ID from an ordinary client as proof of club ownership; the bot must observe and verify the group setup.
- Grant the bot only the Telegram administrator rights needed for configured operations.
- Treat a missing permission or failed API call as a degraded integration, not as authorization success.
- The webhook has no session authentication and accepts `POST` only. It compares the
  configured `TELEGRAM_WEBHOOK_SECRET` with Telegram's secret-token header in
  constant time, rejects missing/mismatched values generically, and never logs either
  value or raw update data.
- Webhook update IDs have a database uniqueness constraint shared by all workers.
  Unsupported and permanently invalid updates return 2xx after safe deduplication;
  only transient provider failures return 5xx for Telegram retry.

## 9. Staff, audit, and operations

- Require strong staff authentication and separate staff accounts from student roles.
- Use least-privilege Django groups/permissions.
- Audit roster imports, verification overrides, suspensions, club decisions, membership removals, report resolution, group linking, invite-link rotation, and privileged data access.
- Protect backups and restrict production database access.
- Define retention/deletion rules with the lyceum administration and applicable privacy requirements before launch, especially because students may be minors.
- Monitor authentication failures, verification abuse, cross-lyceum denials, Telegram API errors, and outbox backlog without logging secrets.

## 10. Security test plan

The Phase 8A suite covers forged/malformed/stale/future/replayed Telegram data, duplicate roster binding, exact-match ambiguity, claimed-record non-disclosure, frontend-supplied identity/scope tampering, suspension, CSRF, throttling, CSV rollback, tenant IDOR, roles, membership races, Telegram access, reports, notifications, and sensitive-field serialization. Phase 8B must supplement this with controlled manual Telegram-client, reverse-proxy/header, operational permission, backup/restore, and incident-response exercises.

Perform a manual pre-production review of deployment secrets, CORS/CSP, cookie settings, admin exposure, database backups, Telegram webhook validation, and bot permissions.
Phase 5A adds one-time Telegram group-link challenges, owner-only management,
trusted lyceum/member checks for invites, and recipient-scoped notifications.
Telegram delivery is best effort and cannot roll back club transactions.
Phase 5B enforces owner-only meeting/announcement mutations, active-membership
visibility, verified lyceum scoping, preference-aware fan-out, and deduplicated
reminders. Telegram failures remain outside domain transactions.
Phase 7 reporting is restricted to verified active students and same-lyceum
visible targets. Reporter identity and moderation fields are staff-only.

## 11. Phase 8A verified guarantees

- Telegram Mini App login accepts only raw signed `init_data`; malformed, missing-hash,
  invalid-hash, stale, unreasonable-future, replayed, missing-user, malformed-JSON,
  non-object-user, and tampered-user payloads are rejected using fake tokens in tests.
- Session creation and every session-authenticated unsafe verb remain CSRF-protected.
  The frontend always sends cookies and sends the CSRF cookie value on unsafe methods.
- Student object lookups are scoped before role checks. Cross-lyceum clubs, requests,
  meetings, announcements, groups, notifications, and reports return safe not-found or
  permission responses without serializing the target.
- The roster claim, club creation, join acceptance, duplicate join request, and Telegram
  chat-link paths use PostgreSQL transactions and database constraints. Threaded
  `TransactionTestCase` coverage verifies one roster winner, one owned club, at most
  three active memberships, one pending request, and one club per Telegram chat.
- Report rows use explicit club/announcement foreign keys and an exactly-one-target
  check. Hidden clubs and announcements outside the reporter's active membership are
  not reportable by guessed UUID.
- API serializers reject, rather than silently ignore, server-owned meeting,
  announcement, report, preference, club-moderation, and Telegram-action fields.
- Telegram member links expire after ten minutes and set
  `creates_join_request=true`. They are returned only to active members and are never
  stored or logged. Telegram approval must recheck the current membership.
- Notification delivery persists only a safe exception class name, not raw provider
  responses, URLs, or credentials.

## 12. Rate limits

The defaults are intentionally focused on sensitive mutations and are configurable by
environment without weakening browsing:

| Action | Scope | Default |
|---|---|---:|
| Telegram Mini App authentication | Client address | 20/hour |
| Roster verification claim | Authenticated user | 5/hour |
| Join-request submission | Authenticated user | 20/hour |
| Report submission | Authenticated user | 10/hour |
| Telegram invite generation | Authenticated user | 10/hour |

Production must use a shared cache so replay and throttle state is consistent across
processes. Rate limits are abuse controls, not authorization controls.

## 13. Practical threat model

| Threat | Current mitigation | Residual risk |
|---|---|---|
| Student impersonation | Signed Telegram identity, generic roster errors, per-user throttling, atomic one-to-one claim | Name/surname/group knowledge is not strong identity proof; replace it with a school-issued single-use secret before wider launch |
| Roster enumeration | No roster API, staff-only records, exact matching, generic claim failure | An attacker can still make bounded guesses from known student details |
| Cross-lyceum access / IDOR | Trusted roster-derived lyceum, scoped querysets/services, safe 404 regression tests | A future endpoint can regress without the same review and tests |
| Owner privilege escalation | Server-derived owner/role/status fields, owner-scoped actions, database owner-membership constraints | Compromised owner or staff sessions retain their legitimate authority |
| Membership-limit race | User-row lock before count/write plus threaded PostgreSQL tests | Direct writes outside domain services could bypass the application lock; restrict database write access |
| Telegram invite leakage | Active-member authorization, ten-minute join-request link, approval-time membership recheck, no persistence/logging | A link can be forwarded and create a pending request; it must never grant admission automatically |
| Malicious report spam | Verified/visible targets, controlled reasons, one open report per target, 10/hour throttle | Coordinated verified accounts can still create moderation load |
| Leaked bot token | Environment-only secret, no frontend exposure, generic provider errors | A leaked production token requires immediate BotFather rotation and incident review |
| Compromised admin | Django staff permissions, read-only sensitive fields, moderation attribution | Strong staff MFA/SSO and full privileged audit coverage remain deployment prerequisites |

## 14. Phase 8B deployment prerequisites and known limitations

- Prefer a same-origin HTTPS reverse proxy. If origins differ, allowlist only the exact
  HTTPS frontend origins in CORS and `CSRF_TRUSTED_ORIGINS`; never enable all origins.
- Keep `Secure`, `HttpOnly`, and `SameSite=Lax` session cookies unless an explicitly
  tested Telegram client requires `SameSite=None; Secure`. Keep CSRF cookies scoped to
  the application origin.
- Retain HTTPS redirect, HSTS, `X-Content-Type-Options`, and `Referrer-Policy`.
  Define CSP and frame/embedding directives only after testing all supported Telegram
  clients; do not weaken script or connection sources broadly.
- Production replay/throttle state requires a shared cache; the development local-memory
  cache is process-local.
- Profile photos remain external HTTPS references. Credentials-in-URL and non-HTTPS
  schemes are rejected, but the browser still contacts an external host; uploads,
  proxying, moderation, retention, and allowlisting remain out of scope.
- Configure redaction at the reverse proxy and application observability layers for
  cookies, `initData`, bot URLs/tokens, roster input, chat IDs, and invite links.
- Complete minor/privacy review, staff authentication hardening, backup/restore rehearsal,
  incident response, retention policy, and Telegram permission verification before launch.

## 15. Dependency and CI security status

On 2026-08-30, `npm audit` reported zero known vulnerabilities across the locked
frontend tree. `pip-audit` reported zero known vulnerabilities in the installed Python
environment, including Django 5.2.17, Django REST Framework 3.18.0, and psycopg 3.3.4.
These are point-in-time results, not guarantees. CI repeats both audits, runs migrations
and all backend tests against PostgreSQL, and runs frontend type-checking, Vitest, and
the production build with fake secrets only.

## 16. Phase 8B release boundary

Production configuration, staged HSTS, exact hosts/origins, Redis cache requirements,
Gunicorn, static serving, backups, rollback, privacy retention, incident response, and the
manual smoke matrix are documented in `docs/DEPLOYMENT.md`, `docs/PRIVACY_RETENTION.md`,
`docs/INCIDENT_RESPONSE.md`, and `docs/SMOKE_TEST.md`. The code includes an inbound
Telegram webhook, but deploying its HTTPS route, rotating/configuring secrets, and passing
real Telegram-client/group permission checks remain operator gates.
