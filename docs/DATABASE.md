# LYC Society Database Design (Phases 1-3)

PostgreSQL is the source of truth. The examples below describe logical tables and constraints; Django migrations will define the physical schema.

## 1. Phases 1–4 implementation

The following schema is implemented by initial migrations today:

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

## 2. Target data-model roadmap

The remaining sections retain the approved full-MVP schema for later phases. They are not a declaration that every table currently exists; the Phases 1–2 implementation section above takes precedence for the current database.

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

### Phase 4 entities

### `clubs`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `lyceum_id` | Required FK; set from owner’s verified record |
| `owner_id` | Required FK to `users` |
| `name` | Length-limited; normalized uniqueness per lyceum |
| `slug` | Optional URL-friendly value, unique per lyceum |
| `short_description`, `full_description` | Validated/sanitized content |
| `category` | Controlled category choice or admin-managed taxonomy |
| `status` | `PENDING`, `ACTIVE`, `REJECTED`, `PAUSED`, `ARCHIVED` |
| `rejection_reason` | Required when status is `REJECTED` |
| `reviewed_by`, `reviewed_at` | Nullable administrator decision metadata |
| `created_at`, `updated_at` | UTC timestamps |

Recommended category values: Technology, Science, Business, Sports, Arts, Languages, Academic, Social, Other.

### `memberships`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `user_id` | Required FKs |
| `role` | `OWNER`, `MEMBER`, future `MODERATOR` |
| `status` | `ACTIVE` or `REMOVED` |
| `joined_at`, `left_at` | Membership history |

The owner has an active membership row. This makes membership counting and future roles consistent. An active membership is unique per `(club_id, user_id)`; removal preserves history and does not create a second active row.

### `join_requests`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `user_id` | Required FKs |
| `status` | `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED` |
| `message` | Optional length-limited request message if product retains it |
| `decision_reason` | Optional for acceptance; expected for rejection when owner supplies one |
| `decided_by`, `decided_at` | Decision metadata |
| `created_at`, `updated_at` | UTC timestamps |

Add a PostgreSQL partial unique constraint on `(club_id, requester_id)` where `status = 'PENDING'`. A service transaction must also reject new requests for an active membership.

### `meetings`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `created_by` | Required FKs |
| `title` | Required, length-limited |
| `starts_at` | Required UTC instant; UI may collect local date/time and timezone |
| `location` | Optional text |
| `description` | Optional length-limited text |
| `status` | `SCHEDULED`, `CANCELLED`, optionally `COMPLETED` |
| `created_at`, `updated_at` | UTC timestamps |

### `meeting_attendance`

Optional but supported in the model for simple responses. Unique `(meeting_id, user_id)` with status `GOING`, `MAYBE`, or `NOT_GOING`. The service accepts responses only from current active members and the owner.

### `announcements`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id`, `author_id` | Required FKs |
| `title`, `message` | Required, length-limited, sanitized |
| `created_at`, `updated_at` | UTC timestamps |

### `telegram_groups`

One active integration per club in MVP.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `club_id` | Unique FK to `clubs` |
| `chat_id` | Required unique Telegram chat ID; never taken from an ordinary client request |
| `chat_type`, `title` | Last verified metadata |
| `invite_link_encrypted` | Bot-generated join-request link; encrypt at application layer and never return to non-members |
| `link_creates_join_request` | Must be true for the gated flow |
| `bot_admin_verified`, `can_invite_users`, `can_restrict_members` | Capability snapshot |
| `connected_by`, `last_checked_at` | Audit/health metadata |
| `status` | `CONNECTED`, `DEGRADED`, `DISCONNECTED` |

### `notifications`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `recipient_id` | Required FK to `users` |
| `type` | Controlled type such as `VERIFICATION_RESULT`, `CLUB_REVIEW`, `JOIN_REQUEST`, `JOIN_DECISION`, `ANNOUNCEMENT`, `MEETING`, `MEETING_REMINDER` |
| `title`, `body` | Rendered notification text without secrets |
| `payload` | Small JSON object containing opaque object IDs, not sensitive roster data |
| `read_at` | Null means unread |
| `dedupe_key` | Optional unique event key for idempotency |
| `created_at` | UTC timestamp |

`notification_preferences` stores per-user, per-type or grouped-channel choices: in-app enabled and Telegram enabled. A small `notification_deliveries`/outbox table stores channel, status, attempts, provider message ID, last error, and next-attempt time.

### `reports`

Use explicit nullable typed targets to retain database referential integrity for MVP.

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `reporter_id` | Required verified user |
| `club_id` or `announcement_id` | Exactly one target, enforced with a check constraint |
| `reason` | `SPAM`, `FAKE_INFORMATION`, `HARASSMENT`, `INAPPROPRIATE_CONTENT`, `OTHER` |
| `details` | Optional length-limited text |
| `status` | `OPEN`, `RESOLVED`, `DISMISSED` |
| `resolved_by`, `resolution_note`, `resolved_at` | Staff decision metadata |
| `created_at`, `updated_at` | UTC timestamps |

### `audit_events`

Append-only staff/security audit records: actor, action, object type/ID, lyceum context, safe metadata, request correlation ID, and timestamp. Never write raw verification codes, `initData`, invite links, or bot tokens.

### Planned constraints and indexes

- `users.telegram_user_id` unique.
- `student_records.verified_user_id` unique and nullable.
- `clubs.owner_id` unique: one club per user.
- Case-insensitive normalized club name unique per lyceum if the product wants name uniqueness; at minimum index `(lyceum_id, status, name)` for discovery.
- `memberships` unique active `(club_id, user_id)`.
- `join_requests` partial unique pending `(club_id, requester_id)`.
- `telegram_groups.club_id` and `telegram_groups.chat_id` unique.
- `reports` check: exactly one typed target is non-null.
- `clubs` check: rejected status requires non-empty rejection reason.
- Foreign keys use restrictive or protective deletion behavior for student, club, and audit history.
- Index discovery by `(lyceum_id, status, category)`, tags, `created_at`, upcoming `meetings.starts_at`, open reports, notification recipient/read state, and outbox status/next-attempt time.

The maximum-three-memberships rule spans rows and cannot be represented by a normal row-level unique constraint. Enforce it in a transaction that locks the user row before counting active memberships. If a deployment requires protection against writes outside Django, add and test a PostgreSQL trigger after measuring the operational cost; application services remain the primary write path.

### Planned transaction boundaries

- Verification binding: lock the roster row and user identity; check both are unbound; bind atomically.
- Club creation: lock the user; check no owned club and membership count; insert club and owner membership together.
- Join acceptance: lock the user and pending request; re-check club, lyceum, membership count, and request status; create membership and mark request accepted in one transaction.
- Club approval/rejection: lock the club; re-check current status; record decision and enqueue notification after commit.
- Membership removal: mark membership removed and enqueue access-revocation/delivery work after commit.

### Planned roster import and updates

Imports are administrator-only, idempotent by the official stable key where available, and produce a reconciliation report. A record becoming inactive prevents new verification and new actions but does not silently rewrite historical club or membership records. If the administration changes a student’s group/name, future reads use the current official record; the audit trail records the change.

Do not import or store fields not needed for verification. In particular, age/date of birth is not required by this product.
