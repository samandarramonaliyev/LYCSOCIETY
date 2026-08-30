# LYC Society Decisions and Ambiguity Register

This is the decision log for requirements that need an explicit interpretation. A later product decision must update this file and the affected source-of-truth documents before code changes.

## Accepted baseline decisions

### D-001 — Documentation before implementation

**Status:** Superseded by Phase 1
**Decision:** The initial task created only the specification and architecture baseline. Phase 1 now implements only the approved backend foundation.
**Reason:** Documentation remains the prerequisite for code changes; Phase 2+ behavior remains out of scope until requested.

### D-002 — Modular monolith

**Status:** Accepted  
**Decision:** Use Django/DRF/PostgreSQL with React/Vite/Tailwind and an internal Telegram adapter.  
**Reason:** The pilot benefits from simple transactions, one source of truth, and low operational overhead. Internal module boundaries preserve future extraction options without prematurely adding services.

### D-003 — Telegram identity, not username

**Status:** Accepted  
**Decision:** Bind accounts to Telegram’s validated numeric user ID. Usernames and names are display metadata only.  
**Reason:** Telegram usernames can be missing or changed; `initData` validation is the trust boundary.

### D-004 — Server-side sessions for the Mini App

**Status:** Accepted, verify in Phase 2  
**Decision:** Prefer a secure Django session established after validated `initData`, with CSRF protection for writes.  
**Reason:** It avoids storing bearer tokens in browser localStorage and keeps authorization centralized. Same-origin production deployment is the default assumption.

### D-005 — Verified fields are roster-owned

**Status:** Accepted  
**Decision:** First name, last name, group, and lyceum come from the bound official student record. Profile writes cannot change them.  
**Reason:** This prevents frontend tampering and lets administrators update roster data later.

### D-006 — Exact roster matching is the Phase 2 pilot verification method

**Status:** Accepted for Phase 2 by product-owner instruction; high-risk transitional control
**Decision:** After validated Telegram authentication, a user selects a lyceum and submits first name, last name, and group. The backend normalizes those values and claims a record only when exactly one active, unclaimed official record matches. Zero, ambiguous, inactive, and already-claimed candidate states return the same generic failure; an already verified user cannot claim again.
**Reason:** The Phase 2 product instruction explicitly authorizes this method instead of a code. It enables pilot onboarding from the available roster while preserving atomic one-to-one claims and minimizing roster enumeration.

**Security impact:** This is not proof that the Telegram user owns the official identity. Anyone who knows another student's roster details may attempt a claim. Per-account throttling, generic errors, short-lived validated Telegram data, and administrator-only reset reduce risk but do not eliminate it.

**Required follow-up:** Replace this method before wider deployment with an administrator-issued, single-use, expiring verification code or another administration-controlled secret. Do not silently treat roster knowledge as strong identity proof.

### D-007 — Owner membership counts toward the three-club limit

**Status:** Accepted for Phase 4
**Decision:** Creating a club creates an active owner membership, and that row counts toward the maximum of three active memberships. Club creation fails if the student is already at the limit.  
**Reason:** It keeps ownership and membership consistent and prevents a student from bypassing the cap by creating clubs.

### D-008 — Rejected requests may be resubmitted

**Status:** Accepted baseline  
**Decision:** A rejected/cancelled join request remains history; a new pending request may be created later if the student is still eligible.  
**Reason:** Students may correct context or request again without losing moderation history. The partial unique constraint applies only to pending requests.

### D-009 — Club lyceum derives from owner

**Status:** Accepted  
**Decision:** A club belongs to the owner’s verified lyceum at creation. The client cannot select or change it. Cross-lyceum ownership is not supported in MVP.  
**Reason:** It makes the primary product rule unambiguous and closes a common scope-tampering path.

### D-010 — Telegram group access uses gated join requests

**Status:** Accepted baseline; verify Bot API permissions during Phase 5  
**Decision:** The bot generates/owns a join-request invite link and approves requests only after checking the current LYC Society membership. Do not expose a permanent unrestricted link.  
**Reason:** A forwarded link must not grant access to non-members. Existing-member removal remains capability-dependent on Telegram admin rights.

### D-011 — In-app notification is authoritative; Telegram is a delivery channel

**Status:** Accepted  
**Decision:** Save in-app notifications with the domain transaction. Telegram messages use an outbox with retry, deduplication, and failure state.  
**Reason:** Telegram delivery can fail because a user has not started the bot, the bot is blocked, rate limits occur, or permissions change. Domain state must not depend on external delivery.

### D-012 — Django Admin plus custom staff views

**Status:** Accepted baseline  
**Decision:** Use Django Admin and a small custom dashboard/workflow surface rather than a second React admin application.  
**Reason:** MVP staff needs are operational and internal; this keeps effort focused on authorization and workflows. Revisit if staff usability requires a dedicated frontend.

### D-013 — Explicit report targets

**Status:** Accepted  
**Decision:** MVP reports target a club or announcement through explicit nullable foreign keys with a database check that exactly one is set.  
**Reason:** A generic polymorphic target is flexible but weakens referential integrity unnecessarily for the small MVP content set.

### D-014 — No owner self-leave or transfer in MVP

**Status:** Accepted for Phase 4
**Decision:** The owner cannot leave their own club. Administrator-only transfer may be added later.  
**Reason:** The requirement does not define orphaned clubs or transfer rules; silently supporting them would create moderation and ownership gaps.

### D-015 — Minimum public student disclosure

**Status:** Accepted baseline; confirm with administration/privacy review  
**Decision:** Public student-facing profile data is display name, photo, about, and interests. Group is shown to the club owner for a join request and to authorized staff, not as a general directory field.  
**Reason:** Group is useful for owner review but broader exposure is unnecessary for discovery.

### D-016 — Implement only foundational domain apps in Phase 1

**Status:** Accepted
**Decision:** Implement `common`, `identity`, `lyceums`, and `profiles` now. Do not create placeholder `clubs`, `notifications`, `moderation`, or Telegram apps.
**Reason:** Placeholder domain code would imply behavior that Phase 1 is explicitly forbidden to implement. The documented module boundaries remain the contract for later phases.

### D-017 — Account, roster, and profile relationship

**Status:** Accepted
**Decision:** A required unique positive Telegram user ID identifies each `User`; `StudentRecord.verified_user` is the nullable one-to-one official binding; `StudentProfile` is a separate one-to-one editable profile. Verified lyceum and group are derived from the record rather than copied into the profile.
**Reason:** This prevents mass assignment of verified identity data and separates sensitive roster data from user-editable data. An optional normalized external student key is unique only within a lyceum; names and groups are not identities.

### D-018 — PostgreSQL-only configuration without local fallback

**Status:** Accepted
**Decision:** Settings require PostgreSQL environment variables and have no SQLite fallback, including tests.
**Reason:** PostgreSQL constraints and behavior are the production contract. Phase 1 runtime verification is complete; Phase 2 must use the same PostgreSQL-only test environment rather than substitute SQLite.

### D-019 — Telegram initialization freshness and bounded replay mitigation

**Status:** Accepted for Phase 2
**Decision:** Validate raw Mini App `initData` with Telegram's HMAC-SHA-256 data-check-string algorithm, require `auth_date` within a configurable five-minute default window (with 30 seconds of allowed future skew), and store a SHA-256-derived hash key in Django's cache for that same window. A reused signed payload in that window is rejected and successful authentication rotates the Django session key. Persist only the numeric Telegram identity plus current username and name metadata; do not persist Telegram `photo_url` in Phase 2 because profile-photo policy belongs to Phase 3.
**Reason:** Telegram's signed payload establishes identity but can otherwise be presented more than once while fresh. This limits replay without logging raw init data or introducing a new persistent authentication-token table.

**Operational constraint:** Production deployments with multiple application processes must configure a shared cache for replay protection; a process-local cache only reduces replay risk within that process.

### D-020 — Roster CSV import and duplicate policy

**Status:** Accepted for Phase 2
**Decision:** A trusted server operator runs a Django management command on UTF-8 CSV containing `lyceum`, `first_name`, `last_name`, and `group`, with optional `external_student_key`. Lyceum codes must already exist. The command never updates or deletes existing records. A repeated exact normalized tuple is skipped; a conflicting external key or malformed row is an error reported with its CSV row number. Any validation error rolls back the entire import.
**Reason:** It gives administrators a small, auditable operational path without exposing roster data through a normal-user API or adding a Phase 7 custom dashboard.

### D-021 — Administrator-controlled claim reset

**Status:** Accepted for Phase 2
**Decision:** Normal users cannot replace their claimed record. A trusted Django administrator may reset a claim through the official-record administration workflow, clearing both sides of the claim timestamp pair. Identity fields on a claimed record are read-only in that workflow, so staff reset the claim before correcting them. The former user remains an authenticated but unverified account until a subsequent authorized claim.
**Reason:** It prevents account takeover or lyceum-switching through ordinary API calls while allowing staff to correct an onboarding error.

### D-022 — CSRF-protected session creation

**Status:** Accepted for Phase 2
**Decision:** Before posting signed Telegram `initData`, the same-origin Mini App obtains a CSRF cookie/token from `GET /api/v1/auth/csrf/` and sends it in `X-CSRFToken` to the session-creating login endpoint. The login endpoint applies Django CSRF validation even though it otherwise allows anonymous callers.
**Reason:** A signed Telegram payload authenticates the caller but does not by itself prevent a cross-site login request from binding a victim browser to an attacker's account. The bootstrap keeps the documented Django session model and protects against login CSRF without introducing bearer tokens.

### D-023 — Phase 3 profile fields, photo references, and interests

**Status:** Accepted for Phase 3
**Decision:** Self-profile writes accept only plain-text `about` (maximum 1,000 characters), plain-text `hobbies` (maximum 500 characters), an optional HTTPS `profile_photo_url`, and IDs of administrator-managed active interests. At most ten unique interests may be selected. Deactivated interests cannot be newly selected and are omitted from selectable/profile responses; duplicate submitted IDs collapse safely. The server does not fetch or proxy external photo URLs.
**Reason:** This keeps the profile boundary small and auditable while preserving the existing model and avoiding an unplanned media pipeline or uncontrolled tag creation.

### D-024 — Trusted lyceum scope helper

**Status:** Accepted for Phase 3
**Decision:** Future lyceum-scoped queries use `get_verified_lyceum(user)` or `scope_queryset_to_verified_lyceum(...)`. These helpers derive the tenant only from the user's active official student record and active lyceum; client-supplied IDs and query parameters are never authorization context.
**Reason:** A shared service boundary prevents future object-level authorization from accidentally using a request-selected lyceum and provides a single reusable foundation for Phase 4 discovery.

### D-025 — Phase 4 club, membership, and join-request rules

**Status:** Accepted for Phase 4
**Decision:** Each verified student may own exactly one club, regardless of club status; rejected clubs are edited and resubmitted in place. New clubs are `PENDING`, owner membership is created atomically and counts toward a maximum of three active memberships, and only active same-lyceum clubs are discoverable. Owners may keep active clubs active while editing. Members may leave; owners must archive instead. Pending join requests are unique per club/user and are accepted transactionally under user/club locks.
**Reason:** These rules provide a small auditable lifecycle, prevent duplicate ownership and membership-limit races, and keep tenant scope server-derived.

## Open risks and ambiguities

| ID | Requirement gap | Why it matters | Recommendation |
|---|---|---|---|
| A-01 | Roster-detail verification is not strong identity proof | Names/groups can be known by another person; a successful exact match can still be an impersonation | Replace D-006's transitional flow with an administration-controlled secret before wider deployment |
| A-02 | Whether owner membership counts toward three is unspecified | It changes club creation eligibility and database/test rules | Confirm D-007 before Phase 4 |
| A-03 | Club owner transfer/orphan behavior is unspecified | Deleting/leaving an owner could break approvals, group integration, and announcements | Keep owner fixed; confirm D-014 before Phase 4 |
| A-04 | “Where applicable” Telegram group access is underspecified | Bot admin rights and invite/join-request behavior vary by chat configuration | Require explicit setup checks and degraded state; confirm operationally in Phase 5 |
| A-05 | Existing Telegram members after LYC membership removal | Bot may lack rights to remove them | Require at least future-access denial; decide whether stronger bot permissions are acceptable |
| A-06 | “Basic notification preferences” has no exact matrix | Too many toggles create UI and delivery complexity; too few cause unwanted spam | Start with grouped in-app and Telegram toggles for account, club, meeting, and announcement notifications |
| A-07 | Student-record stable identifier is not specified | Duplicate imports and updates cannot be safely reconciled by names alone | Require an administration-provided external key or establish a controlled import reconciliation process |
| A-08 | Admin role model and staff identity source are unspecified | Staff actions are high impact and need strong authentication/audit | Use Django staff accounts/groups for MVP; confirm who may administer which lyceums |
| A-09 | Media storage/retention is unspecified | Profile photos affect privacy, storage, and moderation | Start with validated profile image upload or Telegram photo reference; define retention before Phase 3 |
| A-10 | Local timezone and reminder policy are unspecified | Meeting timestamps and reminders can be wrong across lyceums | Store UTC plus lyceum timezone; define default reminder timing before Phase 5 |
| A-11 | Student age/minor consent/privacy obligations are unspecified | The product is for students and may process minor data | Obtain administration/legal/privacy review before production; do not collect age unless required |
| A-12 | Club edit behavior after approval is unspecified | Unmoderated edits could bypass approval | Either re-review material changes or define owner-editable fields before Phase 4 |

## Decision maintenance rule

When implementation reveals a new ambiguity, record the requirement, risk, recommendation, and affected documents here. A code change that relies on a new product decision is not complete until the decision is documented.
### D-026 — Phase 5A Telegram groups and notifications

Groups are owner-linked through a short-lived bot-confirmed challenge; the bot does
not create groups. Invite links are limited-use/short-lived. Notifications are an
outbox-like database record delivered separately with bounded retries.
### D-027 — Phase 5B scheduling

Meetings use scheduled/cancelled states and one-hour, deduplicated reminder
notifications via a management command. RSVP is intentionally minimal.

### D-028 — Phase 8A report target integrity and visibility

**Status:** Accepted for Phase 8A
**Decision:** Store report targets as explicit nullable foreign keys to `Club` and
`Announcement`, with a database check requiring exactly one target and partial
uniqueness for one open report per reporter/target. The student API continues to
accept the stable `target_type`/`target_id` contract, but resolves that input to a
server-authorized target before creating the report. A club must be active and
same-lyceum; an announcement must belong to an active club in which the reporter
has an active membership.
**Reason:** The Phase 7 generic UUID implementation disagreed with D-013 and could
allow a guessed same-lyceum UUID to report content the caller could not otherwise
see. Typed foreign keys preserve referential integrity and visibility-scoped lookup
prevents that IDOR.

### D-029 — Phase 8A Telegram invite gating takes precedence over member limits

**Status:** Accepted for Phase 8A
**Decision:** Member access uses a bot-owned invite link that expires after ten
minutes and sets `creates_join_request=true`. It does not set `member_limit` because
Telegram forbids combining that option with join-request links. The bot must still
approve the resulting request only after mapping the Telegram identity and
rechecking the current active club membership. The link is returned only to the
authorized member and is never persisted or logged by LYC Society.
**Reason:** A one-use direct-admission link can be forwarded and bypass the
application membership decision. Join-request gating fails closed and preserves
the product's authoritative membership check; the short expiry limits sharing risk.

### D-030 — Phase 8B pilot deployment topology and external gates

**Status:** Accepted for Phase 8B release preparation

**Decision:** Use one Django/Gunicorn backend behind an HTTPS reverse proxy, serve the
React build from the same public origin, use managed PostgreSQL with TLS and backups,
and use a shared managed Redis-compatible cache for replay/throttle state. Production
settings require exact hosts/origins, secure cookies, environment-only secrets, and
staged HSTS. The Django Telegram webhook handles only `message` linking commands and
`chat_join_request` updates, uses a production-only secret header, and stores unique
update IDs in PostgreSQL. Keep Telegram group approval disabled until the endpoint is
configured and passes non-production client/permission tests.

**Reason:** Same-origin serving reduces cookie/CSRF/CORS complexity while shared cache
is required for multi-worker security state. A database dedupe row is additionally
needed for inbound updates because each Gunicorn worker must observe the same delivery
state. Restricting subscriptions to the two implemented update types minimizes exposed
input surface and keeps group authorization in the established domain services.

### D-031 — Phase 8B inbound webhook policy

**Status:** Accepted for Phase 8B

**Decision:** Configure Telegram with exactly `message` and `chat_join_request`.
`message` is used only for an owner-bound `/connect <token>` command in a group or
supergroup; `chat_join_request` is approved only after a current linked-group, active
club, verified-active account, and active membership check. All other updates are
ignored. The bot must be an administrator with `can_invite_users` when linking;
group-broadcast capability is not required because MVP notifications are direct.

**Failure policy:** A transient Bot API failure returns 503 so Telegram can retry.
Unsupported, malformed-but-safe, invalid challenge, unauthorized, or permanent Bot API
failure returns 2xx after durable idempotency handling, preventing infinite retries.
No raw update payload, token, secret, invite link, or Bot API response body is persisted.
