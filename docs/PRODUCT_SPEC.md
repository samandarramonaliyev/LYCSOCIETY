# LYC Society Product Specification

**Status:** Baseline specification for implementation planning  
**Date:** 2026-08-29  
**Product:** LYC Society

## 1. Product summary

LYC Society is a private student society accessed through a Telegram Bot and Telegram Mini App. A student must first be verified against an official lyceum roster. Once verified, the student primarily discovers and interacts with active clubs belonging to that same lyceum.

The first release is a pilot in one lyceum. Every core entity carries a lyceum boundary so additional lyceums can be enabled without replacing the core model.

The product is a community directory and club-management layer. Telegram remains the communication channel; LYC Society does not implement an internal chat.

## 2. Actors

- **Unverified Telegram user:** Can start the bot and submit the approved verification flow, but cannot access student or club data.
- **Verified student:** Can manage an allowed profile, discover same-lyceum clubs, create one club, request membership, attend meetings, receive notifications, and report content.
- **Club owner:** A verified student who owns one club and can manage its requests, members, meetings, announcements, and Telegram integration.
- **Administrator:** A trusted staff account that manages lyceums, roster data, users, clubs, reports, and suspensions.
- **Telegram Bot:** An integration actor that sends notifications, handles owner actions from Telegram, and mediates group join requests.

## 3. MVP capabilities

The MVP includes:

- Telegram identity authentication with server-side `initData` validation.
- Official-roster student verification and a verified profile.
- First-class lyceums and backend-enforced lyceum isolation.
- Structured interest tags and profile editing for non-verified fields.
- Same-lyceum active-club discovery with search and filters.
- One club per verified student, with administrator approval before publication.
- Club rejection reasons and resubmission after correction.
- Join requests, owner accept/reject actions, rejection reasons, and membership roles.
- A maximum of three active club memberships per student.
- Optional Telegram group integration with approved-member access control.
- Meetings, simple attendance status, announcements, and notifications.
- Basic notification preferences.
- Reporting, administrator resolution, and basic moderation.
- An internal administrator panel and dashboard statistics.
- Automated tests for critical business rules and security boundaries.

## 4. Explicitly out of scope

Do not implement in MVP:

- Internal chat or direct messaging.
- AI recommendations or recommendation ranking.
- Social feed, gamification, points, badges, or competitions.
- Payments, premium clubs, or subscriptions.
- Inter-lyceum discovery or competitions.
- Complex event management or advanced analytics.
- Microservices or a separate real-time messaging platform.

The schema may leave extension points, but no out-of-scope feature should add UI, workflows, dependencies, or operational burden during MVP.

## 5. Core user journeys

### 5.1 Verification

1. The user starts the Telegram Bot or opens the Mini App.
2. The Mini App obtains a same-origin CSRF token, then sends it with the raw Telegram `initData` to the backend.
3. The backend validates the CSRF token, Telegram signature, timestamp, and Telegram user ID.
4. The authenticated user selects a lyceum and submits their first name, last name, and group for the approved Phase 2 roster-match verification method.
5. The backend matches the attempt to one active official student record and binds that record to the Telegram identity.
6. The Mini App receives the safe API verification result; in-app and Telegram notification delivery remain a later Phase 5 concern.
7. Only a verified, non-suspended account may use protected product features.

Phase 2 uses an exact, normalized match on lyceum, first name, last name, and group. A match is accepted only when it identifies exactly one active, unclaimed official record. This is a transitional onboarding check, not strong proof of identity: a person who knows another student's roster details could potentially claim that record. Generic failures, throttling, and administrator-only claim resets reduce disclosure and operational risk; an administrator-issued, single-use verification code remains the recommended stronger replacement. See `docs/DECISIONS.md`.

### 5.2 Discovery and club page

The default club list is `ACTIVE` clubs whose `lyceum_id` equals the current verified student’s lyceum. Search, category filters, and interest-tag filters refine that server-side query. The frontend may not switch the lyceum by adding a request parameter.

A club page displays the club’s approved content, category, tags, owner’s minimum necessary public profile, member count, upcoming meeting, membership/join-request status, and Telegram access only when the current user is an approved member.

### 5.3 Club creation and approval

1. A verified student submits one club with name, short description, full description, category, tags, and optional meeting details.
2. The backend derives the club’s lyceum from the owner’s verified record and ignores any client-supplied lyceum.
3. The club is created as `PENDING` and is not in normal discovery.
4. An administrator approves it (`ACTIVE`) or rejects it (`REJECTED`) with a required reason.
5. Approval/rejection creates a notification and an owner Telegram message where delivery is possible.
6. A rejected owner may edit allowed fields and resubmit. The history remains auditable.

### 5.4 Join request and membership

1. A verified student requests to join an active same-lyceum club.
2. The backend rejects requests from a different lyceum, requests to an inactive club, requests from the owner, requests where the student already has an active membership, and requests that would exceed three active memberships.
3. A pending request is unique for the user and club.
4. The owner receives a Telegram action notification containing only the relevant student information.
5. The owner accepts or rejects through an authorized bot action or the Mini App.
6. Acceptance creates one active membership transactionally and notifies the student. Rejection notifies the student and may include a reason.

### 5.5 Group, meetings, and announcements

The owner connects a Telegram group through a bot-mediated setup flow. Members receive a protected group-access action. Telegram join requests are approved only when the bot can map the requesting Telegram identity to an active LYC Society membership for that club.

Club owners create upcoming meetings and announcements. The notification service creates in-app notifications for active members and queues Telegram delivery according to each user’s preferences. Delivery failure must not roll back the saved meeting or announcement.

## 6. Lifecycle definitions

### Club

`PENDING → ACTIVE`  
`PENDING → REJECTED`  
`REJECTED → PENDING` (resubmission)  
`ACTIVE → PAUSED`
`ACTIVE → ARCHIVED`  
`PAUSED → ACTIVE` or `ARCHIVED`

Only administrators may approve, reject, pause, or archive. An owner may edit a pending/rejected club and resubmit; editing active content should be limited to owner-editable fields and preserve moderation history.

### Join request

`PENDING → ACCEPTED`  
`PENDING → REJECTED`  
`PENDING → CANCELLED`

Only the requester may cancel their pending request. Only the club owner or an authorized administrator may accept/reject. A previously rejected or cancelled request may be replaced by a new pending request, subject to all current rules.

### Membership

`ACTIVE → REMOVED`

An owner membership is created with the club. Owners cannot leave their own club in MVP; owner transfer is an administrator-only future operation. Removal stops future member notifications and future group-access approval.

## 7. Privacy and visibility baseline

- Verified first name, last name, lyceum, and group are server-owned.
- A verified student may read and update only their own plain-text `about`, plain-text `hobbies`, HTTPS profile-photo reference, and administrator-managed interest selections. The self-profile API returns verified identity from the official record but never accepts it as writable input.
- Public student-facing profiles show only the minimum approved fields: display name, profile photo if available, about text, and interests. Group is shown to a club owner for a join request and to administrators; it is not a public directory field by default.
- Exact age is never displayed.
- The complete official roster, verification codes, verification history, internal audit data, raw Telegram IDs, and invite links are restricted to authorized staff or integration code.
- A student may only see private club/member data for their own lyceum, and only within the role-specific permissions documented in `docs/API.md`.

## 8. Product-level acceptance criteria

- A forged, stale, or replayed Telegram initialization payload cannot create or use a verified session.
- A frontend request with another lyceum’s ID cannot return that lyceum’s clubs, members, requests, meetings, or announcements.
- One Telegram identity can map to at most one active verified student account and one roster record.
- A verified student cannot own a second club, including through direct API calls or concurrent requests.
- A student cannot have more than three active memberships, including the owner membership, even under concurrent join/creation requests.
- Only active clubs appear in normal discovery.
- Only the club owner or authorized administrator can process that club’s join requests or publish club content.
- A user removed from a club cannot obtain new Telegram group access.
- Admin rejection requires a reason and is visible to the owner but not to unrelated students.
- Every critical side effect is idempotent and auditable.

## 9. Experience direction

The visual direction is academic, literary, warm, and restrained: parchment/cream, ink brown, muted burgundy, forest green, muted gold, serif editorial typography, clean sans-serif support text, thin borders, whitespace, and subtle paper/book details. Avoid neon, cyberpunk, glassmorphism, excessive gradients/3D, and childish school-app styling.

The visual direction does not override security, accessibility, Telegram safe-area behavior, or readable contrast.
