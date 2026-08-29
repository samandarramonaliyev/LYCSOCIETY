# LYC Society API Contract

This is the planned boundary for the Django REST Framework API. It is a contract and implementation guide, not an instruction to implement the endpoints in this documentation phase.

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

## 2. Authentication and account

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/telegram` | None | Validate raw Telegram `initData`, create/update the application user, establish a secure session, and return coarse account state |
| `POST` | `/auth/logout` | Session | End the current session |
| `GET` | `/auth/me` | Session | Return current account state, verified display fields allowed to the user, and capabilities |
| `GET` | `/verification/status` | Session | Return `UNVERIFIED`, `PENDING`, `VERIFIED`, `DENIED`, or `SUSPENDED` without exposing the roster |
| `POST` | `/verification/redeem-code` | Session | Submit the approved one-time verification input; exact method remains recorded in `DECISIONS.md` |
| `GET` | `/profile` | Verified | Return own profile |
| `PATCH` | `/profile` | Verified | Edit only photo/about/interests; reject verified identity fields |

The authentication endpoint must not accept `telegram_user_id`, verified name, group, or lyceum as authoritative request fields. The user identity comes from validated `initData`; verified fields come from the roster binding.

## 3. Discovery and clubs

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

## 4. Join requests and memberships

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

## 5. Meetings, announcements, and Telegram access

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

## 6. Notifications and preferences

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/notifications` | Verified | Paginated own notifications |
| `POST` | `/notifications/{id}/read` | Recipient | Mark one notification read |
| `POST` | `/notifications/read-all` | Recipient | Mark own notifications read |
| `GET` | `/notification-preferences` | Verified | Get basic preference state |
| `PATCH` | `/notification-preferences` | Verified | Change allowed in-app/Telegram preferences |

Notification creation is a domain side effect; recipients are derived from membership and account state. Clients cannot choose arbitrary recipients.

## 7. Staff/admin boundary

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

## 8. Status codes and authorization behavior

- `200`/`201`: successful read/create/update.
- `204`: successful action with no body.
- `400`: malformed request or invalid transition input.
- `401`: no valid session.
- `403`: authenticated but not allowed; do not use this to reveal unrelated object existence when `404` is safer.
- `404`: object not found within the caller’s permitted scope.
- `409`: conflict such as duplicate pending request, one-club violation, or stale state transition.
- `429`: rate limited.

Use stable machine-readable error codes so the Mini App can present a clear message without inferring business rules from HTTP text.

## 9. API test contract

For every protected detail/action route, test:

- unauthenticated access;
- unverified/suspended access;
- same-lyceum allowed access;
- other-lyceum denied access;
- wrong role denied access;
- stale/current status behavior;
- concurrent duplicate requests where relevant;
- response does not leak forbidden fields.
