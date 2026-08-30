# LYC Society Development Plan

Phases 0–7 and **Phase 8A final hardening are complete.** Phase 8A covers security audit, adversarial and concurrency tests, dependency review, cleanup, and CI; deployment remains reserved for Phase 8B.

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

## Phase 3 — Profiles + interests + lyceum isolation (complete)

Deliverables:

- Editable profile fields and media handling.
- Structured tag management and selection.
- Same-lyceum scoped query helpers and object permissions.
- Safe student-facing profile serializers.

The Phase 3 profile API is self-only. It permits plain-text `about` and `hobbies`, an optional HTTPS photo reference, and up to ten active administrator-managed interest tags. Verified identity remains derived from the official record. Shared lyceum-scope helpers derive tenant context from that record rather than request parameters.

Exit criteria:

- Cross-lyceum list and detail IDOR tests pass.
- Client-supplied scope/identity fields are ignored or rejected.
- Sensitive roster fields are absent from ordinary responses.

## Phase 4 — Clubs + approval + join requests + memberships (complete)

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

## Phase 8A — Final hardening (complete)

Deliverables:

- Adversarial authentication, CSRF, authorization, IDOR, mass-assignment, and tenant-isolation coverage.
- PostgreSQL concurrency tests for roster claims, club creation, membership limits, duplicate join requests, and Telegram chat uniqueness.
- Materially expanded React/Vitest coverage for authentication and critical student/owner workflows.
- Dependency and secret scans, logging/privacy review, focused cleanup, and backend/frontend CI using PostgreSQL and fake secrets.
- Security guarantees, residual-risk threat model, and Phase 8B deployment prerequisites.

Exit criteria:

- All local checks, PostgreSQL-backed tests, frontend tests, lint, build, and dependency audits pass.
- No critical/high implementation finding remains without explicit risk acceptance.
- Known deployment and product limitations are documented without weakening controls.

## Phase 8B — Production readiness and deployment (prepared; external gates outstanding)

Deliverables include deployment infrastructure, production origins/headers and shared cache, backup/restore rehearsal, monitoring, runbooks, incident response, privacy/retention approval, Telegram capability verification, and controlled release. Phase 8A must not perform these tasks or deploy the application.

The Phase 8B preparation artifacts are now present in `docs/DEPLOYMENT.md`,
`docs/PRIVACY_RETENTION.md`, `docs/INCIDENT_RESPONSE.md`, and `docs/SMOKE_TEST.md`, with
production settings and a conservative Gunicorn configuration. The inbound Django webhook,
its persistent update dedupe, and safe configuration/status commands are implemented. External
provisioning, secret rotation/configuration, and real Telegram client/group testing remain
operator work before group approval is enabled.

## Cross-phase engineering gates

- Update the relevant source-of-truth document before changing a contract.
- Add tests with every business rule.
- Keep migrations backward-compatible with the deployed release strategy.
- Do not add a dependency without a documented reason, maintenance plan, and security review.
- Do not expand MVP scope to solve a future feature.
Phase 5A adds Telegram group linking/invite integration and the notification
outbox/delivery foundation. Meetings and announcements remain Phase 5B.
Phase 5B adds meetings, announcements, reminders, and preference enforcement.
Phase 7 adds Django Admin roster operations, claim reset, club moderation support,
and a minimal scoped reporting queue.
