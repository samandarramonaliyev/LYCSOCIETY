# LYC Society Database Design

PostgreSQL is the source of truth. The examples below describe logical tables and constraints; Django migrations will define the physical schema.

## 1. Implemented MVP schema

The following foundational schema is implemented; later sections describe the implemented club, membership, meeting, notification, Telegram, and report tables:

- `identity.User` has a UUID primary key, required unique positive `telegram_user_id`, optional Telegram display metadata, `ACTIVE`/`SUSPENDED`/`DEACTIVATED` account status, staff permissions, and timestamps. `is_verified` is a read-only property derived from an active linked official record rather than a duplicate database flag.
- `lyceums.Lyceum` has a UUID primary key, case-insensitively unique normalized code, name, optional city, active/inactive status, and timestamps.
- `lyceums.StudentRecord` is separate sensitive roster data. It owns official first/last name, group, lyceum, optional normalized external student key, normalized first/last/group matching fields, active/inactive state, a nullable one-to-one `verified_user`, and timestamps.
- `profiles.StudentProfile` is a separate one-to-one editable profile with `about`, `hobbies`, optional profile-photo URL, interests, and timestamps. It has no writable lyceum, group, or official-identity column.
- `profiles.Interest` is a reusable staff-managed vocabulary with case-insensitively unique name and slug. The automatic many-to-many join table prevents duplicate profile-interest pairs.

The profile creation signal creates one profile for every normally-created user. `StudentRecord.verified_user` uses `PROTECT`, while a profile uses `CASCADE` because it contains only application-editable data. The official record uses an optional normalized external key when supplied by the administration; name and group are deliberately not identity constraints. Phase 2 nevertheless uses the exact normalized tuple `(lyceum, first_name, last_name, group_name)` only as a provisional claim lookup: it claims a record only when exactly one active unclaimed record matches. Duplicate rows are therefore possible in the schema and must fail verification as ambiguous rather than being silently selected.

Implemented database constraints and indexes:

- unique positive Telegram user ID;
- case-insensitive unique lyceum code;
- unique supplied external student key within a lyceum;
- one official record per user and one user per official record;
- `verified_user` and `verified_at` must be both null or both populated;
- non-negative verification attempts;
- case-insensitive unique interest names/slugs; and
- a scoped roster index on `(lyceum, status, group_name)` and an exact normalized roster-match index; and
- one-to-one record claim integrity enforced by `verified_user` plus an atomic, row-locked claim service.

PostgreSQL is mandatory. The settings have no SQLite fallback, including for tests.

## 2. Data-model details

The remaining sections describe the approved and implemented MVP model. Migrations remain the physical source of truth; future schema changes require the relevant decision and contract documents to be updated first.

### Identifier and timestamp conventions

- Use UUID primary keys for application objects exposed through URLs.
- Use `bigint` for Telegram user and chat IDs; they are opaque identifiers, not public profile data.
- Store timestamps as timezone-aware UTC values.
- Use explicit status/role choices, with application-level transition checks and database checks where possible.
- Keep historical rows for moderation and decisions. Prefer `ARCHIVED`, `REMOVED`, or `INACTIVE` states over destructive deletion.

### Core entities

### `lyceums`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `code` | Unique stable code, normalized lowercase |
| `name` | Display name |
| `status` | `ACTIVE` or `INACTIVE` |
| `created_at`, `updated_at` | UTC timestamps |

### `users`

Use a custom Django user model from the first migration.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `telegram_user_id` | Required, positive, unique; immutable through ordinary/admin edits after creation |
| `telegram_username`, `telegram_first_name`, `telegram_last_name` | Optional current display metadata; never identity proof |
| `status` | `ACTIVE`, `SUSPENDED`, or `DEACTIVATED` |
| `is_verified`, `is_suspended` | Read-only properties derived from roster relation/account status |
| `is_staff` / role membership | For Django admin access; use Django permissions/groups |
| `last_seen_at`, `created_at`, `updated_at` | Operational timestamps |

`about`, hobbies, and profile photo live in `student_profiles`. Do not duplicate editable copies of verified first name, last name, group, or lyceum as user-controlled fields. Phase 3 limits profile interest selections to ten active administrator-managed tags; the existing many-to-many join and database uniqueness prevent duplicate pairs. `profile_photo_url` is an optional HTTPS URL/reference and the server does not fetch or proxy it.

### `student_records`

The imported official roster. This is sensitive staff data.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `lyceum_id` | Required FK to `lyceums` |
| `external_student_key` | Stable official identifier if the administration supplies one; unique per lyceum/import domain |
| `first_name`, `last_name` | Official values |
| `normalized_first_name`, `normalized_last_name`, `normalized_group_name` | Exact normalized matching support; do not expose |
| `group_name` | Official group |
| `verification_code_hash` | Reserved for a future stronger code-based flow; never store raw code |
| `verification_code_expires_at`, `verification_attempts` | Reserved verification metadata; Phase 2 uses API throttling rather than these fields |
| `status` | `ACTIVE` or `INACTIVE` |
| `verified_user_id` | Nullable one-to-one FK to `users` |
| `verified_at`, `created_at`, `updated_at` | Audit/operational timestamps |

The Phase 2 roster import is a trusted-operator management command. It accepts UTF-8 CSV with `lyceum`, `first_name`, `last_name`, and `group` headers, plus an optional `external_student_key`. `lyceum` is an existing stable lyceum code. Rows are trimmed and normalized; duplicate tuples in a file or an idempotent repeat import are skipped, conflicting external keys and malformed rows are reported with row numbers, and any validation error rolls back the whole import. Existing records, especially claimed records, are never overwritten by an import. In Django Admin, a claimed record's identity fields are read-only; staff reset its claim before correcting those fields.

A user can be bound to one active roster record; a roster record can be bound to at most one user. The exact roster-match claim service locks both the user and candidate record(s), rechecks the claim relationship, and writes `verified_user` and `verified_at` together.

### `student_profiles`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `user_id` | Required one-to-one FK to `users` |
| `about` | User-editable text, max 1,000 characters |
| `hobbies` | User-editable text, max 500 characters |
| `profile_photo_url` | User-editable URL reference, max 500 characters |
| `interests` | Reusable many-to-many interest relation |
| `created_at`, `updated_at` | UTC timestamps |

Verified lyceum, group, and official identity are derived read-only properties that traverse the linked student record; they are not profile columns.

### `interest_tags`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `slug` | Unique normalized key |
| `name` | Display label |
| `is_active` | Staff-controlled availability |

Join tables `user_interest_tags` and `club_interest_tags` use unique `(owner, tag)` pairs. Users and clubs may have configurable small maximum counts, e.g. 10, enforced by service validation.

### Club entities

### `clubs`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `lyceum_id` | Required FK; set from owner’s verified record |
| `owner_id` | Required FK to `users` |
| `name` | Required, maximum 120 characters |
| `short_description`, `description` | Required bounded plain-text content |
| `category` | Controlled category choice or admin-managed taxonomy |
| `status` | `PENDING`, `ACTIVE`, `REJECTED`, `PAUSED`, `ARCHIVED` |
| `rejection_reason` | Required when status is `REJECTED` |
| `created_at`, `updated_at` | UTC timestamps |

Recommended category values: Technology, Science, Business, Sports, Arts, Languages, Academic, Social, Other.

### `memberships`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `user_id` | Required FKs |
| `role` | `OWNER`, `MEMBER` |
| `status` | `ACTIVE` or `REMOVED` |
| `joined_at`, `left_at` | Membership history |

The owner has an active membership row. This makes membership counting and future roles consistent. An active membership is unique per `(club_id, user_id)`; removal preserves history and does not create a second active row.

### `join_requests`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `user_id` | Required FKs |
| `status` | `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED` |
| `rejection_reason` | Optional bounded reason supplied by the owner on rejection |
| `created_at`, `updated_at` | UTC timestamps |

A PostgreSQL partial unique constraint enforces `(club_id, user_id)` uniqueness where `status = 'PENDING'`. A service transaction also rejects new requests for an active membership.

### `meetings`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `created_by` | Required FKs |
| `title` | Required, length-limited |
| `starts_at` | Required UTC instant; UI may collect local date/time and timezone |
| `location` | Optional text |
| `description` | Optional length-limited text |
| `status` | `SCHEDULED`, `CANCELLED` |
| `created_at`, `updated_at` | UTC timestamps |

### `meeting_rsvps`

Unique `(meeting_id, user_id)` with response `GOING` or `NOT_GOING`. The service accepts responses only from current active members, rejects cancelled meetings, and updates the row atomically.

### `announcements`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `created_by` | Required FKs |
| `title`, `message` | Required, length-limited, sanitized |
| `created_at`, `updated_at` | UTC timestamps |

### `telegram_groups`

At most one integration row per club and one club per Telegram chat in MVP.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id` | Unique FK to `clubs` |
| `telegram_chat_id` | Required unique Telegram chat ID; never taken from an ordinary client request |
| `telegram_chat_title` | Last verified display metadata |
| `bot_can_invite_members`, `bot_can_send_messages` | Capability snapshot |
| `linked_at`, `unlinked_at` | Link lifecycle timestamps |
| `status` | `PENDING`, `LINKED`, `UNLINKED` |

Invite links are not persisted. The adapter requests a ten-minute Telegram link with `creates_join_request=true` and returns it only to an authorized active member.

### `telegram_link_challenges`

Each linking challenge is single-use and is bound to both the active club and its
current owner. It stores only a SHA-256 token hash, an expiry timestamp, an optional
consumption timestamp, and the expected owner foreign key. The raw setup token is
returned once to the owner and is never stored or logged.

### `telegram_webhook_updates`

Inbound Telegram updates are represented by a minimal persistent idempotency row:
the unique Telegram `update_id`, a processed timestamp, and no raw update payload.
This database uniqueness is shared by all Gunicorn workers and prevents duplicate
delivery from repeating group links or join-request decisions. A failed transient
provider call leaves the row unprocessed so Telegram may retry; permanently invalid
or unsupported updates are marked processed without retaining their contents.

### `notifications`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `recipient_id` | Required FK to `users` |
| `type` | Controlled type such as `VERIFICATION_RESULT`, `CLUB_REVIEW`, `JOIN_REQUEST`, `JOIN_DECISION`, `ANNOUNCEMENT`, `MEETING`, `MEETING_REMINDER` |
| `title`, `body` | Rendered notification text without secrets |
| `is_read` | Recipient-owned read state |
| `delivery_status`, `delivery_attempts`, `delivered_at`, `last_delivery_error` | Bounded delivery state; only a safe exception category may be stored |
| `dedupe_key` | Optional unique event key for idempotency |
| `created_at`, `updated_at` | UTC timestamps |

`notification_preferences` is one-to-one with the user and stores the editable `club_announcements`, `meeting_notifications`, and `meeting_reminders` flags. Security/system authorization decisions do not depend on these preferences.

### `reports`

Use explicit nullable typed targets to retain database referential integrity for MVP.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `reporter_id` | Required verified user |
| `club_id` or `announcement_id` | Exactly one target, enforced with a check constraint |
| `reason` | `SPAM`, `FAKE_INFORMATION`, `HARASSMENT`, `INAPPROPRIATE`, `OTHER` |
| `details` | Optional length-limited text |
| `status` | `OPEN`, `REVIEWED`, `ACTIONED`, `DISMISSED` |
| `reviewed_by`, `reviewed_at` | Staff decision metadata |
| `created_at`, `updated_at` | UTC timestamps |

### `audit_events`

Append-only staff/security audit records: actor, action, object type/ID, lyceum context, safe metadata, request correlation ID, and timestamp. Never write raw verification codes, `initData`, invite links, or bot tokens.

### Implemented constraints and indexes

- `users.telegram_user_id` unique.
- `student_records.verified_user_id` unique and nullable.
- `clubs.owner_id` unique: one club per user.
- `memberships` unique active `(club_id, user_id)`.
- one active owner membership per club and status/`left_at` consistency.
- `join_requests` partial unique pending `(club_id, requester_id)`.
- `meeting_rsvps` unique `(meeting_id, user_id)`.
- `telegram_groups.club_id` and `telegram_groups.chat_id` unique.
- `telegram_link_challenges` are bound to a club and expected owner; token hashes are unique.
- `telegram_webhook_updates.update_id` is unique.
- `reports` check: exactly one typed target is non-null, plus one open report per reporter and typed target.
- `clubs` check: rejected status requires non-empty rejection reason.
- Foreign keys use restrictive or protective deletion behavior for student, club, and audit history.
- Index discovery by `(lyceum_id, status, category)`, tags, `created_at`, upcoming `meetings.starts_at`, open reports, notification recipient/read state, and outbox status/next-attempt time.

The maximum-three-memberships rule spans rows and cannot be represented by a normal row-level unique constraint. Enforce it in a transaction that locks the user row before counting active memberships. If a deployment requires protection against writes outside Django, add and test a PostgreSQL trigger after measuring the operational cost; application services remain the primary write path.

### Implemented transaction boundaries

- Verification binding: lock the roster row and user identity; check both are unbound; bind atomically.
- Club creation: lock the user; check no owned club and membership count; insert club and owner membership together.
- Join acceptance: lock the user and pending request; re-check club, lyceum, membership count, and request status; create membership and mark request accepted in one transaction.
- Club moderation: lock the club; re-check the current status; change it through controlled actions and create the recipient notification.
- Membership removal: mark membership removed and enqueue access-revocation/delivery work after commit.

### Roster import and updates

Imports are administrator-only, idempotent by the official stable key where available, and produce a reconciliation report. A record becoming inactive prevents new verification and new actions but does not silently rewrite historical club or membership records. If the administration changes a student's group/name after resetting a claim, future reads use the current official record and Django Admin retains its normal change history.

Do not import or store fields not needed for verification. In particular, age/date of birth is not required by this product.
Phase 5A adds `ClubTelegramGroup`, owner-bound one-time `TelegramLinkChallenge`,
`Notification`, and `NotificationPreference`. Phase 8B adds persistent
`TelegramWebhookUpdate` deduplication for the inbound webhook. Group chat IDs are
unique and notification dedupe keys are unique when supplied.
Phase 5B adds Meeting, MeetingRSVP, and Announcement entities. Meetings belong to
active clubs, are visible only to active members, and use scheduled/cancelled
states. Reminder notifications are deduplicated per meeting/member.
Phase 7 adds a staff-managed Report queue with controlled reasons, open/reviewed/
actioned/dismissed states, and reviewer audit timestamps.
