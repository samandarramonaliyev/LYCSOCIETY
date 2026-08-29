# LYC Society Security Model

Security is a product requirement, not a frontend feature. The backend and database enforce all identity, lyceum, role, and state rules.

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

The planned login flow is:

1. The Mini App sends the raw `Telegram.WebApp.initData` string to `POST /api/v1/auth/telegram`.
2. The backend parses the query-string fields without changing their signed representation.
3. It derives the Telegram Web App secret from the bot token and validates the HMAC-SHA-256 hash using constant-time comparison.
4. It verifies a bounded `auth_date` freshness window and reasonable clock skew.
5. It extracts the Telegram user ID from the validated payload and looks up the unique application user.
6. It creates/rotates a secure server-side session and returns only account state needed by the client.

Never use `initDataUnsafe` as an authority, accept a frontend-supplied Telegram ID, log raw initialization data, or use a Telegram username as a stable identity. Never accept a normal browser request as proof of verification.

Use a short freshness window appropriate for the product and allow re-authentication when expired. The exact window must be configurable and covered by tests rather than hardcoded in UI behavior.

## 3. Session and browser controls

Prefer Django server-side session authentication for the same-origin production deployment:

- `Secure`, `HttpOnly`, appropriately scoped cookie.
- `SameSite=Lax` where compatible with the deployed Mini App; if deployment requires cross-site cookies, explicitly use `SameSite=None; Secure` and a strict allowlist.
- CSRF tokens on all cookie-authenticated state changes.
- Same-origin production serving or a tightly configured HTTPS frontend origin.
- No authentication tokens in localStorage.
- Session invalidation on suspension, account rebind, or security incident.

Set HTTPS, HSTS, a restrictive Content Security Policy, frame/embedding policy compatible with Telegram, secure referrer policy, and safe content-type headers. Configure CORS only for known development/production origins.

## 4. Verification security

- The official roster is staff-only data.
- Prefer a random, single-use, expiring verification code issued out of band and stored only as a strong hash.
- Bind the code to exactly one student record and the validated Telegram identity.
- Lock or slow repeated failures; rate-limit by Telegram ID, session, and network signal.
- Make redemption atomic and replay-resistant.
- Do not reveal whether a guessed name/group exists. Return coarse verification outcomes.
- Prevent one Telegram identity from binding multiple records and one record from binding multiple accounts.
- Do not let profile PATCH or any public API mutate verified fields.
- Keep verification attempts and staff changes auditable without recording raw codes.

If the administration requires name/last-name/group matching instead of codes, use normalized matching, explicit ambiguity handling, throttling, and a second factor or staff confirmation. Do not implement a freely enumerable roster lookup.

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
- Rate-limit reports, profile updates, club creation, join requests, Telegram actions, and notification-triggering actions.
- Use generic error responses that do not disclose roster membership, object existence, or staff-only state.
- Redact authorization headers, cookies, init data, verification codes, invite URLs, and personal data from logs.

## 8. Telegram data protection

- Store bot tokens only in secret management/environment configuration.
- Store Telegram IDs as protected operational identifiers; do not expose them in normal API responses.
- Encrypt stored invite links at the application layer and restrict decryption to the Telegram integration service.
- Never accept a chat ID from an ordinary client as proof of club ownership; the bot must observe and verify the group setup.
- Grant the bot only the Telegram administrator rights needed for configured operations.
- Treat a missing permission or failed API call as a degraded integration, not as authorization success.

## 9. Staff, audit, and operations

- Require strong staff authentication and separate staff accounts from student roles.
- Use least-privilege Django groups/permissions.
- Audit roster imports, verification overrides, suspensions, club decisions, membership removals, report resolution, group linking, invite-link rotation, and privileged data access.
- Protect backups and restrict production database access.
- Define retention/deletion rules with the lyceum administration and applicable privacy requirements before launch, especially because students may be minors.
- Monitor authentication failures, verification abuse, cross-lyceum denials, Telegram API errors, and outbox backlog without logging secrets.

## 10. Security test plan

Include automated tests for forged hash, stale `auth_date`, replayed code, duplicate binding, IDOR across lyceums, frontend-supplied scope tampering, role escalation, concurrent three-membership attempts, duplicate join requests, rejected-state leaks, unauthorized Telegram access, outbox retry/deduplication, rate limits, CSRF, and sensitive-field serialization.

Perform a manual pre-production review of deployment secrets, CORS/CSP, cookie settings, admin exposure, database backups, Telegram webhook validation, and bot permissions.
