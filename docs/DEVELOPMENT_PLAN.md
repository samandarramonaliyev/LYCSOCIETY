# LYC Society Development Plan

The repository is currently in **Phase 0: specification and architecture**. This document is the gate for future implementation. No Phase 1 product features should be started from the current task.

## Phase 0 — Documentation baseline (complete for this task)

Deliverables:

- Repository audit.
- Product, architecture, database, API, security, Telegram, and decision documents.
- Agent instructions and phase boundaries.

Exit criteria: all source-of-truth documents exist, contradictions are recorded, and no product code has been implemented.

## Phase 1 — Backend foundation + database

Deliverables:

- Django project, settings separation, environment configuration, health check, logging, error handling, and PostgreSQL connection.
- Custom user model and initial domain apps.
- Initial migrations for lyceums, users, student records, tags, clubs, memberships, requests, meetings, announcements, notifications, reports, audit, and Telegram integration.
- Base API versioning, pagination, validation, permission helpers, and test harness.
- Admin authentication foundation and migration/backup practices.

Exit criteria:

- Clean migrations apply to an empty database.
- Constraints and indexes are tested.
- No endpoint can accidentally return data without the planned auth boundary.
- CI runs checks and tests.

## Phase 2 — Telegram authentication + student verification

Deliverables:

- Bot setup and Mini App login endpoint.
- Exact Telegram `initData` HMAC and freshness validation.
- Secure session creation and logout.
- Staff roster import/reconciliation.
- One-time verification-code flow, unless the product owner approves a different documented mechanism.
- Verification status and notification behavior.

Exit criteria:

- Forged, stale, replayed, duplicate, ambiguous, and brute-force attempts are tested.
- Verified fields are read-only to the student.
- Unverified users cannot reach protected product data.

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
