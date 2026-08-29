# LYC Society Development Plan

Phases 0 and 1 are complete. **Phase 2 is the active implementation phase.** Its code may be closed only after Django checks, migration consistency checks, and PostgreSQL-backed tests pass in the configured local environment.

## Phase 0 — Documentation baseline (complete for this task)

Deliverables:

- Repository audit.
- Product, architecture, database, API, security, Telegram, and decision documents.
- Agent instructions and phase boundaries.

Exit criteria: all source-of-truth documents exist, contradictions are recorded, and no product code has been implemented.

## Phase 1 — Backend foundation + database

Deliverables:

- Django project, settings separation, environment configuration, health check, logging, error handling, and PostgreSQL-only connection settings.
- Custom user model plus `common`, `identity`, `lyceums`, and `profiles` domain apps.
- Initial migrations for users, lyceums, official student records, student profiles, and interest tags only.
- Base `/api/v1/` routing, JSON error envelope, pagination, a future verified-student permission, and test harness.
- Django Admin foundation and local PostgreSQL setup documentation.

Implementation boundary: clubs, memberships, join requests, meetings, announcements, notifications, reports, audits, and Telegram integration are deliberately not migrated or scaffolded in this phase. This supersedes the earlier broad Phase 1 migration wording to comply with Prompt 01's explicit scope.

Exit criteria:

- Clean migrations apply to an empty database.
- Constraints and indexes are tested.
- No endpoint can accidentally return data without the planned auth boundary.
- CI runs checks and tests.

## Phase 2 — Telegram authentication + student verification

Deliverables:

- Bot-token configuration and Mini App login endpoint.
- Exact Telegram `initData` HMAC and freshness validation.
- CSRF-protected secure session creation, logout, and login-CSRF bootstrap.
- Staff roster import/reconciliation.
- Exact normalized roster-match claim flow using lyceum, first name, last name, and group, with generic failures for no match, ambiguity, and claimed records.
- Verification status endpoint, reusable verified-active-student permission, and administrator-only claim reset.
- Trusted-operator CSV roster import with validation, deterministic duplicate handling, and row-number reporting.

Exit criteria:

- Forged, stale, replayed, duplicate, ambiguous, and throttled attempts are tested.
- Verified fields are read-only to the student.
- Unverified users cannot reach protected product data.
- The documented limitation of roster-detail matching is accepted explicitly; a stronger administration-controlled secret remains recommended before wider deployment.

## Phase 3 — Profiles + interests + lyceum isolation

Deliverables:

- Editable profile fields and media handling.
- Structured tag management and selection.
- Same-lyceum scoped query helpers and object permissions.
- Safe student-facing profile serializers.

Exit criteria:

- Cross-lyceum list and detail IDOR tests pass.
- Client-supplied scope/identity fields are ignored or rejected.
- Sensitive roster fields are absent from ordinary responses.

## Phase 4 — Clubs + approval + join requests + memberships

Deliverables:

- Club create/edit/submit/review state machine.
- One-club-per-owner constraint.
- Owner membership creation and max-three active membership transaction.
- Join-request lifecycle, owner actions, rejection reasons, and notification events.
- Member list and role foundation.

Exit criteria:

- Critical business-rule tests pass, including concurrent membership acceptance and club creation.
- Only active same-lyceum clubs appear in discovery.
- Owner/admin permissions and rejected/pending visibility are tested.

## Phase 5 — Telegram groups + meetings + announcements + notifications

Deliverables:

- Bot webhook/worker adapter.
- Owner group-link setup and capability check.
- Bot-generated gated join-request link and membership-based approval.
- Meeting CRUD, simple attendance, announcement CRUD.
- In-app notifications, preferences, transactional outbox, retry/deduplication, and scheduled reminders.

Exit criteria:

- Telegram actions are idempotent and safe under duplicate updates.
- Missing Bot API permissions fail closed and are visible as degraded integration.
- Removed members cannot obtain new access.
- Notification failures do not roll back domain mutations.

## Phase 6 — React Telegram Mini App

Deliverables:

- Mobile-first React/Vite/Tailwind shell.
- Telegram theme/safe-area integration.
- Verification, profile, discovery, club detail, join, member, meeting, announcement, notification, and report views.
- Accessible loading/error/empty states and deep links.

Exit criteria:

- The frontend uses only documented API contracts.
- It contains no authorization logic relied upon for security.
- Manual Telegram device testing covers supported clients and theme modes.

## Phase 7 — Admin panel + moderation

Deliverables:

- Django Admin/custom staff dashboard.
- User search/suspension, lyceum management, roster import, club review, reports, and basic moderation actions.
- Dashboard counts: verified students, active clubs, pending clubs, open reports.
- Staff audit views and least-privilege permissions.

Exit criteria:

- Staff cross-lyceum access is intentional, permissioned, and audited.
- Sensitive roster fields are limited to the necessary staff roles.
- Every moderation action is reversible where practical and preserves history.

## Phase 8 — Testing + security audit + production readiness

Deliverables:

- Full unit/API/integration/security test suite.
- Migration and rollback rehearsal, backup restore test, load smoke test, and monitoring.
- Manual authorization/IDOR review, dependency scan, secret scan, and Telegram permission audit.
- Privacy/retention review with the lyceum administration.
- Production runbook, incident response, and support procedures.

Exit criteria:

- Definition-of-done checks in `PRODUCT_SPEC.md` pass.
- No critical/high security findings remain without an explicit risk acceptance.
- Telegram delivery, outbox backlog, auth failures, and database health are observable.

## Cross-phase engineering gates

- Update the relevant source-of-truth document before changing a contract.
- Add tests with every business rule.
- Keep migrations backward-compatible with the deployed release strategy.
- Do not add a dependency without a documented reason, maintenance plan, and security review.
- Do not expand MVP scope to solve a future feature.
