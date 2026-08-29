# LYC Society API Contract

This is the API contract and implementation guide. Phase 2 implements the API foundation, health endpoint, Telegram session authentication, onboarding-state reads, and official-record claiming. All club, profile-editing, notification, moderation, and Telegram-group routes remain planned until their named phases.

## 1. Conventions

- Base path: `/api/v1/`.
- JSON request/response bodies, UTF-8.
- UUIDs in URL paths.
- UTC ISO-8601 timestamps.
- Cursor or stable page-number pagination; choose one consistently during Phase 1.
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

Official student data is not publicly serializable. There is no public roster list, lyceum directory, profile-editing endpoint, or staff import endpoint.

## 3. Implemented: Authentication and onboarding

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/telegram/` | None | Validate raw Telegram Mini App `initData`, create/update the application user, rotate/create a secure session, and return safe account state |
| `POST` | `/auth/logout/` | Session | End the current session |
| `GET` | `/auth/me/` | Session | Return the current account, onboarding state, safe Telegram display metadata, and own verified fields if any |
| `GET` | `/verification/status/` | Session | Return `UNVERIFIED`, `VERIFIED`, or `SUSPENDED` without exposing the roster |
| `POST` | `/verification/claim/` | Session, active account | Submit an exact roster-match claim using `lyceum_id`, `first_name`, `last_name`, and `group` |

`POST /auth/telegram/` accepts only an `init_data` string. It does not accept a client-supplied Telegram ID or other identity fields. The backend parses the signed query string, verifies Telegram's HMAC, checks a configurable freshness window, and rejects cached replay hashes within that window. A valid request establishes a Django server-side session and returns a CSRF token for subsequent cookie-authenticated writes; no JWT or browser-stored bearer token is issued.

`POST /verification/claim/` uses client input only to locate a candidate record. It normalizes whitespace and case, then claims only one active unclaimed `StudentRecord` matching the supplied active lyceum, first name, last name, and group. Zero matches, ambiguous matches, inactive records, and already-claimed records all return the same generic verification failure, so the route does not reveal roster state. An already verified user receives `409 ALREADY_VERIFIED`; claim reset/re-verification is an administrator-only operation. This lookup is not proof that the Telegram user owns the student identity; see `docs/SECURITY.md` and `docs/DECISIONS.md`.

The own-account responses expose only safe information: account status, display metadata, verification state, own verified name/lyceum/group, and basic editable-profile data. They never return raw Telegram IDs, official-record IDs or keys, verification metadata, or data about another student.

## 4. Planned: Discovery and clubs

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `GET` | `/clubs` | Verified | Active clubs in the current user’s verified lyceum; search/category/tag filters |
| `POST` | `/clubs` | Verified | Create one pending club; lyceum is derived from user |
| `GET` | `/clubs/{club_id}` | Verified | Active same-lyceum club, or own pending/rejected club, with role-based fields |
| `PATCH` | `/clubs/{club_id}` | Owner/admin | Edit allowed content; server checks ownership/status |
| `POST` | `/clubs/{club_id}/submit` | Owner | Submit/resubmit pending or rejected club for review |
| `GET` | `/clubs/{club_id}/members` | Owner/member/admin | Same-lyceum authorized member list; minimize fields |
| `POST` | `/clubs/{club_id}/reports` | Verified | Report the club with controlled reason |

Normal discovery never returns `PENDING`, `REJECTED`, `SUSPENDED`, or `ARCHIVED` clubs. The owner may see their own non-active club; unrelated students receive not-found or forbidden behavior that does not disclose its existence.

## 5. Planned: Join requests and memberships

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `POST` | `/clubs/{club_id}/join-requests` | Verified | Request membership in active same-lyceum club |
| `GET` | `/me/join-requests` | Verified | Own request history with safe club summaries |
| `POST` | `/join-requests/{request_id}/cancel` | Requester | Cancel own pending request |
| `GET` | `/clubs/{club_id}/join-requests` | Owner/admin | View pending/history needed for management |
| `POST` | `/join-requests/{request_id}/accept` | Owner/admin | Transactionally accept if all rules still hold |
| `POST` | `/join-requests/{request_id}/reject` | Owner/admin | Reject with optional/required reason per product decision |
| `GET` | `/me/memberships` | Verified | Own active/history membership summary |
| `POST` | `/clubs/{club_id}/members/{user_id}/remove` | Owner/admin | Remove active member and revoke future access |

The API must not trust a club owner ID, requester ID, role, membership count, or lyceum supplied by the client.

## 6. Planned: Meetings, announcements, and Telegram access

| Method | Route | Auth | Scope/permission |
|---|---|---|---|
| `GET` | `/clubs/{club_id}/meetings` | Same-lyceum authorized user | List visible meetings |
| `POST` | `/clubs/{club_id}/meetings` | Owner/admin | Create meeting |
| `PATCH` | `/meetings/{meeting_id}` | Owner/admin | Edit/cancel meeting |
| `PUT` | `/meetings/{meeting_id}/attendance` | Active member/owner | Set simple attendance status |
| `GET` | `/clubs/{club_id}/announcements` | Active member/same-lyceum viewer | List visible announcements |
| `POST` | `/clubs/{club_id}/announcements` | Owner/admin | Publish announcement and fan out notifications |
| `GET` | `/clubs/{club_id}/telegram-access` | Active member/owner | Return a short-lived or stored gated Telegram invite link, never raw integration metadata |
| `POST` | `/clubs/{club_id}/telegram-connection` | Owner/admin | Begin group-link setup; bot completes identity/capability verification |
| `DELETE` | `/clubs/{club_id}/telegram-connection` | Owner/admin | Disconnect/revoke integration where permitted |

Telegram group operations that require Bot API permissions are asynchronous/capability-dependent. An API response must expose a safe integration status, not imply success before the Bot API confirms it.

## 7. Planned: Notifications and preferences

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/notifications` | Verified | Paginated own notifications |
| `POST` | `/notifications/{id}/read` | Recipient | Mark one notification read |
| `POST` | `/notifications/read-all` | Recipient | Mark own notifications read |
| `GET` | `/notification-preferences` | Verified | Get basic preference state |
| `PATCH` | `/notification-preferences` | Verified | Change allowed in-app/Telegram preferences |

Notification creation is a domain side effect; recipients are derived from membership and account state. Clients cannot choose arbitrary recipients.

## 8. Implemented staff foundation and planned staff boundary

The implemented Django Admin registers users, lyceums, official student records, profiles, and interests with search, filters, and read-only audit fields. It hides the verification-code hash and makes a persisted Telegram ID read-only after account creation.

Use Django Admin plus custom staff views for MVP. If API-backed staff screens are added, keep them under a distinct namespace such as `/api/v1/admin/` and require staff permissions on every route.

Planned staff operations:

- Search/view users without dumping the roster; suspend/restore accounts.
- Create/edit lyceums.
- Import/reconcile official student records.
- Review/approve/reject/suspend/archive clubs.
- View and resolve reports.
- View dashboard counts.
- Inspect audit and integration health records according to least privilege.

Staff endpoints must scope by explicit authorized staff capability, record audit events, and avoid returning raw verification code hashes or Telegram invite links.

## 9. Status codes and authorization behavior

- `200`/`201`: successful read/create/update.
- `204`: successful action with no body.
- `400`: malformed request or invalid transition input.
- `401`: no valid session.
- `403`: authenticated but not allowed; do not use this to reveal unrelated object existence when `404` is safer.
- `404`: object not found within the caller’s permitted scope.
- `409`: conflict such as duplicate pending request, one-club violation, or stale state transition.
- `429`: rate limited.

Use stable machine-readable error codes so the Mini App can present a clear message without inferring business rules from HTTP text.

Phase 2 additionally uses `TELEGRAM_INIT_DATA_INVALID`, `TELEGRAM_INIT_DATA_EXPIRED`, `TELEGRAM_INIT_DATA_REPLAYED`, and `ACCOUNT_UNAVAILABLE` for authentication failures. Roster lookup failures deliberately collapse to `VERIFICATION_FAILED`; `ALREADY_VERIFIED` is returned only for the current user's own already-complete onboarding state. DRF returns `THROTTLED` for the configured authentication or verification rate limit.

## 10. API test contract

For every protected detail/action route, test:

- unauthenticated access;
- unverified/suspended access;
- same-lyceum allowed access;
- other-lyceum denied access;
- wrong role denied access;
- stale/current status behavior;
- concurrent duplicate requests where relevant;
- response does not leak forbidden fields.
