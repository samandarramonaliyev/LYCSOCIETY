# LYC Society — Agent Instructions

## Project purpose

LYC Society is a private Telegram Bot + Telegram Mini App for verified lyceum students. Students discover and join clubs in their verified lyceum, may create one club, and communicate through Telegram groups. The pilot starts with one lyceum but the data model is multi-lyceum from the beginning.

The repository currently contains the implemented Phase 2 backend foundation. Later-phase product features remain out of scope until their phase is explicitly requested.

## Source of truth

Before changing the project, read the relevant documents in this order:

1. `docs/PRODUCT_SPEC.md` — product behavior and MVP boundaries.
2. `docs/ARCHITECTURE.md` — system boundaries and code structure.
3. `docs/DATABASE.md` — entities, relationships, and constraints.
4. `docs/API.md` — API contracts and permission expectations.
5. `docs/SECURITY.md` — authentication, authorization, privacy, and threat controls.
6. `docs/TELEGRAM.md` — Telegram Bot API and Mini App integration rules.
7. `docs/DEVELOPMENT_PLAN.md` — current phase and exit criteria.
8. `docs/DECISIONS.md` — recorded decisions, assumptions, and open ambiguities.

If code and documentation disagree, stop and update the affected source-of-truth document before implementing behavior. Do not silently change product behavior.

## Stack and architecture

- Backend: Python, Django, Django REST Framework, PostgreSQL.
- Frontend: React, Vite, Tailwind CSS, mobile-first Telegram Mini App.
- Telegram: Telegram Bot API and a maintained Python bot framework such as aiogram.
- Architecture: one modular monolith with clear domain modules; do not introduce microservices, a second database, or a new framework without a documented decision.
- The bot adapter, notification delivery, and domain services are separate boundaries inside the same codebase.

## Non-negotiable rules

- Inspect the existing repository before modifying it and preserve working code unless there is a documented reason to change it.
- The frontend is never the source of truth for identity, lyceum, roles, membership limits, or workflow state.
- Validate Telegram `initData` on the backend. Never trust `initDataUnsafe`, frontend-supplied user/lyceum IDs, or Telegram usernames as identity.
- Enforce object-level authorization and lyceum isolation on every protected endpoint.
- Use database constraints for uniqueness and valid state relationships wherever PostgreSQL can enforce them.
- Do not expose the official student roster, verification codes, raw Telegram chat IDs, invite links, or internal moderation data to ordinary users.
- Keep verified student fields server-owned. Users may edit only explicitly permitted profile fields.
- Treat Telegram side effects as idempotent, retryable, and capability-dependent.
- Do not build internal chat, recommendations, gamification, payments, or other out-of-MVP features.
- Do not implement a later phase while working on an earlier phase unless the plan and decision record are updated.

## Conventions

- Prefer clear domain names and small service functions over generic abstractions.
- Keep serializers/controllers thin; put multi-step business rules in domain services and transactions.
- Use UUIDs for application object identifiers exposed in URLs. Use PostgreSQL `bigint` for Telegram IDs.
- Store all timestamps in UTC with timezone-aware datetimes.
- Use explicit status enums and documented state transitions.
- Return only the minimum data needed for the requesting role and lyceum.
- Validate and length-limit text, sanitize rendered content, and use structured interest tags.

## Testing expectations

Every phase must add tests for its critical business rules. At minimum, test Telegram signature and freshness validation, verification replay/duplication, lyceum isolation and IDOR resistance, one-club-per-owner, maximum-three-active-memberships under concurrency, join-request idempotency, state transitions, role permissions, notification deduplication, and Telegram delivery retries.

Run formatting, linting, migrations/checks, unit tests, API tests, and relevant security tests before declaring a phase complete. Never weaken a test to make an implementation pass without recording why.

## Security expectations

Use HTTPS in deployed environments, secure secrets from environment/secret management, secure HTTP-only sessions, CSRF protection for cookie-authenticated writes, strict CORS/CSP, rate limits on authentication and verification, redacted logs, audit records for privileged actions, and least-privilege Telegram bot permissions. Re-check authorization after every state-changing operation.

## Phase discipline

Read `docs/DEVELOPMENT_PLAN.md` before starting work. Implement only the requested phase. If a requirement is ambiguous or a Telegram capability is unavailable, record the impact and recommended decision in `docs/DECISIONS.md` rather than inventing behavior in code.
