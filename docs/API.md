# LYC Society API Contract

This is the implemented MVP API contract. Phase 8A hardens the existing profile, club, membership, meeting, announcement, notification, Telegram group, report, and moderation boundaries without adding product features.

## 1. Conventions

- Base path: `/api/v1/`.
- JSON request/response bodies, UTF-8.
- UUIDs in URL paths.
- UTC ISO-8601 timestamps.
- Cursor or stable page-number pagination; use the Phase 1-selected page-number policy consistently.
- Search/filter parameters are validated and bounded.
- Public student routes do not accept a client-selected `lyceum_id`.
- All detail routes repeat authorization and scope checks.
- State-changing requests require CSRF protection when using cookie sessions and should be idempotent where a retry is expected.

Example error shape:

```json
{
  "error": {
    "code": "MEMBERSHIP_LIMIT_REACHED",
    "message": "You can belong to at most three active clubs.",
    "fields": {}
  }
}
```

Do not return database exception text, roster data, Telegram tokens, raw chat IDs, or internal stack traces.

## 2. Implemented foundation

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health/` | None | Database liveness/readiness check; returns `200` after `SELECT 1` succeeds and `503` if PostgreSQL is unavailable |

The deployed route is `/api/v1/health/`. DRF currently uses session authentication, `IsAuthenticated` as the default permission, JSON rendering, page-number pagination (20 default / 100 maximum), and a custom error envelope. The health endpoint explicitly overrides the authenticated default.

Official student data is not publicly serializable. Authenticated onboarding users may read the minimal active-lyceum choice list at `/verification/lyceums/`. Verified active students may read and update only their own profile through `/profile/`; clients cannot write roster-owned identity fields or choose a lyceum scope.

## 3. Implemented: verified profiles and interests

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/profile/` | Verified active student | Return the current student's safe profile and roster-derived identity |
| `PATCH` | `/profile/` | Verified active student | Update `about`, `hobbies`, an HTTPS `profile_photo_url`, and administrator-managed `interest_ids` |
| `GET` | `/interests/` | Verified active student | List active interest tags; optional bounded `search` filters by name or slug |

Profile writes reject verified fields (`first_name`, `last_name`, `group`, `lyceum`, and official-record references) with a structured validation error. Interest IDs are deduplicated, must refer to active administrator-managed tags, and are limited to ten per profile.

The profile's lyceum is always derived from the active official student record. Future domain queries should use the shared `get_verified_lyceum(user)` and `scope_queryset_to_verified_lyceum(...)` helpers; request query/body lyceum values are never authorization context.

## 4. Implemented: Authentication and onboarding

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/auth/csrf/` | None | Establish a CSRF cookie and return the token required before the session-creating Telegram login request |
| `POST` | `/auth/telegram/` | CSRF bootstrap token | Validate raw Telegram Mini App `initData`, create/update the application user, rotate/create a secure session, and return safe account state |
| `POST` | `/auth/logout/` | Session | End the current session |
| `GET` | `/auth/me/` | Session | Return the current account, onboarding state, safe Telegram display metadata, and own verified fields if any |
| `GET` | `/verification/lyceums/` | Session | List only active lyceum IDs, codes, and names needed to choose an onboarding scope |
| `GET` | `/verification/status/` | Session | Return `UNVERIFIED`, `VERIFIED`, or `SUSPENDED` without exposing the roster |
| `POST` | `/verification/claim/` | Session, active account | Submit an exact roster-match claim using `lyceum_id`, `first_name`, `last_name`, and `group` |

Before `POST /auth/telegram/`, the same-origin Mini App calls `GET /auth/csrf/` and sends the returned token in `X-CSRFToken`; this protects the session-creating login from login CSRF. `POST /auth/telegram/` accepts only an `init_data` string. It does not accept a client-supplied Telegram ID or other identity fields. The backend parses the signed query string, verifies Telegram's HMAC, checks a configurable freshness window, and rejects cached replay hashes within that window. A valid request establishes a Django server-side session and returns a fresh CSRF token for subsequent cookie-authenticated writes; no JWT or browser-stored bearer token is issued.

`POST /verification/claim/` uses client input only to locate a candidate record. It normalizes whitespace and case, then claims only one active unclaimed `StudentRecord` matching the supplied active lyceum, first name, last name, and group. Zero matches, ambiguous matches, inactive records, and already-claimed records all return the same generic verification failure, so the route does not reveal roster state. An already verified user receives `409 ALREADY_VERIFIED`; claim reset/re-verification is an administrator-only operation. This lookup is not proof that the Telegram user owns the student identity; see `docs/SECURITY.md` and `docs/DECISIONS.md`.

The own-account responses expose only safe information: account status, display metadata, verification state, own verified name/lyceum/group, and basic editable-profile data. They never return raw Telegram IDs, official-record IDs or keys, verification metadata, or data about another student.

## 5. Implemented: clubs and discovery

Implemented routes use trailing slashes: `GET/POST /clubs/`, `GET/PATCH /clubs/{club_id}/`, `GET /clubs/mine/`, `POST /clubs/{club_id}/resubmit/`, `POST /clubs/{club_id}/moderate/` for staff, and `GET /clubs/{club_id}/members/`. Discovery is limited to active clubs in the authenticated student's trusted lyceum.

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `GET` | `/clubs` | Verified | Active clubs in the current user’s verified lyceum; search/category/tag filters |
| `POST` | `/clubs` | Verified | Create one pending club; lyceum is derived from user |
| `GET` | `/clubs/{club_id}` | Verified | Active same-lyceum club, or own pending/rejected club, with role-based fields |
| `PATCH` | `/clubs/{club_id}` | Owner/admin | Edit allowed content; server checks ownership/status |
| `POST` | `/clubs/{club_id}/resubmit` | Owner | Resubmit a rejected club for review |
| `GET` | `/clubs/{club_id}/members` | Owner/member/admin | Same-lyceum authorized member list; minimize fields |

Normal discovery never returns `PENDING`, `REJECTED`, `PAUSED`, or `ARCHIVED` clubs. The owner may see their own non-active club through `/clubs/mine/`; unrelated students receive not-found behavior that does not disclose its existence.

## 6. Implemented: join requests and memberships

Join-request routes are `POST/GET /clubs/{club_id}/join-requests/`, `POST /join-requests/{request_id}/accept/`, `POST /join-requests/{request_id}/reject/`, `POST /join-requests/{request_id}/cancel/`, and `POST /clubs/{club_id}/leave/`. Owner membership counts toward the three-active-membership maximum.

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `POST` | `/clubs/{club_id}/join-requests` | Verified | Request membership in active same-lyceum club |
| `POST` | `/join-requests/{request_id}/cancel` | Requester | Cancel own pending request |
| `GET` | `/clubs/{club_id}/join-requests` | Owner/admin | View pending/history needed for management |
| `POST` | `/join-requests/{request_id}/accept` | Owner | Transactionally accept if all rules still hold |
| `POST` | `/join-requests/{request_id}/reject` | Owner | Reject with an optional bounded reason |
| `POST` | `/clubs/{club_id}/leave` | Active non-owner member | Leave while preserving membership history |

The API must not trust a club owner ID, requester ID, role, membership count, or lyceum supplied by the client.

## 7. Implemented: Meetings and announcements

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `GET` | `/clubs/{club_id}/meetings` | Active member/owner | List visible meetings |
| `POST` | `/clubs/{club_id}/meetings` | Owner | Create meeting |
| `GET` | `/meetings/{meeting_id}` | Active member/owner | Read a visible meeting |
| `PATCH`/`POST` | `/meetings/{meeting_id}` | Owner | Cancel a meeting; the request body must not assign authority or status |
| `POST` | `/meetings/{meeting_id}/rsvp` | Active member/owner | Set `GOING` or `NOT_GOING` RSVP status |
| `GET` | `/clubs/{club_id}/announcements` | Active member/owner | List visible announcements |
| `POST` | `/clubs/{club_id}/announcements` | Owner | Publish announcement and fan out notifications |
| `POST` | `/clubs/{club_id}/telegram/link/start` | Owner | Begin a short-lived group-link challenge; bot confirmation verifies chat identity and capability |
| `GET`/`DELETE` | `/clubs/{club_id}/telegram` | Owner | Read safe link status or disconnect the group |
| `POST` | `/clubs/{club_id}/telegram/invite` | Active member/owner | Return a ten-minute join-request invite; never persist it |

`POST /telegram/webhook/` is a Telegram-to-server integration endpoint, not a
student API. It has no session authentication, accepts only a valid JSON Telegram
Update with `X-Telegram-Bot-Api-Secret-Token`, and returns generic responses. It
processes only `message` (`/connect <challenge>` in a group) and
`chat_join_request`; other update types are safely ignored. It must never be called
by the Mini App.

Telegram group operations that require Bot API permissions are asynchronous/capability-dependent. An API response must expose a safe integration status, not imply success before the Bot API confirms it.

## 8. Implemented: Notifications and preferences

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/notifications` | Verified | Paginated own notifications |
| `POST` | `/notifications/{id}/read` | Recipient | Mark one notification read |
| `GET` | `/notification-preferences` | Verified | Get basic preference state |
| `PATCH` | `/notification-preferences` | Verified | Change allowed in-app/Telegram preferences |

Notification creation is a domain side effect; recipients are derived from membership and account state. Clients cannot choose arbitrary recipients.

## 9. Implemented staff boundary

The implemented Django Admin registers users, lyceums, official student records, profiles, interests, clubs, memberships, join requests, meetings, RSVP rows, announcements, notifications/preferences, Telegram group state/challenges, and reports. Sensitive identity and timestamp fields are read-only where appropriate; persisted Telegram identity cannot be changed through ordinary account editing, claimed roster identity must be reset before correction, club moderation uses controlled actions, and report reviews derive the reviewer from the staff session.

Use Django Admin plus custom staff views for MVP. If API-backed staff screens are added, keep them under a distinct namespace such as `/api/v1/admin/` and require staff permissions on every route.

Implemented staff operations include:

- Search/view users without dumping the roster; suspend/restore accounts.
- Create/edit lyceums.
- Import/reconcile official student records.
- Review/approve/reject/suspend/archive clubs.
- View and resolve reports.

Dashboard counts, a general audit-event model, and integration-health views are not implemented. These remain operational/admin limitations rather than student API capabilities.

Staff endpoints must scope by explicit authorized staff capability, record audit events, and avoid returning raw verification code hashes or Telegram invite links.

## 10. Status codes and authorization behavior

- `200`/`201`: successful read/create/update.
- `204`: successful action with no body.
- `400`: malformed request or invalid transition input.
- `401`: no valid session.
- `403`: authenticated but not allowed; do not use this to reveal unrelated object existence when `404` is safer.
- `404`: object not found within the caller’s permitted scope.
- `409`: conflict such as duplicate pending request, one-club violation, or stale state transition.
- `429`: rate limited.

Use stable machine-readable error codes so the Mini App can present a clear message without inferring business rules from HTTP text.

Phase 2 additionally uses `CSRF_FAILED`, `TELEGRAM_INIT_DATA_INVALID`, `TELEGRAM_INIT_DATA_EXPIRED`, `TELEGRAM_INIT_DATA_REPLAYED`, and `ACCOUNT_UNAVAILABLE` for authentication failures. Invalid Telegram credentials return `401` with `WWW-Authenticate: Telegram`; CSRF failures and unavailable accounts return `403`. Roster lookup failures deliberately collapse to `VERIFICATION_FAILED`; `ALREADY_VERIFIED` is returned only for the current user's own already-complete onboarding state. DRF returns `THROTTLED` for the configured authentication or verification rate limit.

Phase 3 profile validation returns `400` for roster-owned field writes, invalid HTTPS photo references, unavailable interest IDs, and selections over the ten-interest limit. Profile and interest routes return `403` for anonymous, unverified, suspended, or inactive accounts.

## 11. API test contract

For every protected detail/action route, test:

- unauthenticated access;
- unverified/suspended access;
- same-lyceum allowed access;
- other-lyceum denied access;
- wrong role denied access;
- stale/current status behavior;
- concurrent duplicate requests where relevant;
- response does not leak forbidden fields.
### Telegram groups and notifications

- `POST /api/v1/clubs/{id}/telegram/link/start/` — owner-only short-lived link challenge.
- `GET`/`DELETE /api/v1/clubs/{id}/telegram/` — owner group status/unlink.
- `POST /api/v1/clubs/{id}/telegram/invite/` — active members receive a short-lived join-request invite.
- `GET /api/v1/notifications/` and `POST /api/v1/notifications/{id}/read/` — recipient-only notifications.
### Meetings and announcements

Meetings: `GET/POST /api/v1/clubs/{id}/meetings/`, `GET/PATCH/POST /api/v1/meetings/{id}/`, and `POST /api/v1/meetings/{id}/rsvp/`.
Announcements: `GET/POST /api/v1/clubs/{id}/announcements/`.
Preferences: `GET/PATCH /api/v1/notification-preferences/`.
### Reports

Verified students may submit `POST /api/v1/reports/` with `target_type` (`CLUB`
or `ANNOUNCEMENT`), `target_id`, controlled `reason`, and bounded `details`.
Reporter, status, reviewer, and lyceum are server-controlled.

## 12. Sensitive-operation throttles

Default DRF rates are 20/hour per client address for Telegram authentication, 5/hour per authenticated user for roster claims, 20/hour per authenticated user for join-request submission, 10/hour per authenticated user for report submission, and 10/hour per authenticated user for Telegram invite generation. Browsing endpoints are not broadly throttled. Production must use shared cache storage for consistent replay and throttle state across processes.
