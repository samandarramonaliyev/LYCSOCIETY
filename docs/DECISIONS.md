# LYC Society Decisions and Ambiguity Register

This is the decision log for requirements that need an explicit interpretation. A later product decision must update this file and the affected source-of-truth documents before code changes.

## Accepted baseline decisions

### D-001 — Documentation before implementation

**Status:** Accepted  
**Decision:** The current task creates only the specification and architecture baseline.  
**Reason:** The repository is empty and the product has several security- and workflow-sensitive ambiguities. Feature code begins only after the next instruction and the requested phase.

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

### D-006 — One-time verification code is the provisional MVP method

**Status:** Provisional; product owner confirmation required before Phase 2  
**Decision:** Administration issues a random, single-use, expiring code bound to one imported student record. The user redeems it after Telegram authentication.  
**Reason:** “Provided student information matches the official list” does not define the input, and name/group matching alone is enumerable, ambiguous, and vulnerable to impersonation. A code preserves the official roster as private data.

**Alternative requiring an explicit decision:** name + last name + group matching, optionally with a staff confirmation step. Do not implement this alternative silently.

### D-007 — Owner membership counts toward the three-club limit

**Status:** Provisional; product owner confirmation required before Phase 4  
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

**Status:** Provisional; product owner confirmation required before Phase 4  
**Decision:** The owner cannot leave their own club. Administrator-only transfer may be added later.  
**Reason:** The requirement does not define orphaned clubs or transfer rules; silently supporting them would create moderation and ownership gaps.

### D-015 — Minimum public student disclosure

**Status:** Accepted baseline; confirm with administration/privacy review  
**Decision:** Public student-facing profile data is display name, photo, about, and interests. Group is shown to the club owner for a join request and to authorized staff, not as a general directory field.  
**Reason:** Group is useful for owner review but broader exposure is unnecessary for discovery.

## Open risks and ambiguities

| ID | Requirement gap | Why it matters | Recommendation |
|---|---|---|---|
| A-01 | Verification input and issuance process are unspecified | Names/groups can collide; roster enumeration can expose students; code distribution affects operations | Confirm D-006 with lyceum administration before Phase 2 |
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
