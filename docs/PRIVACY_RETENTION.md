# Pilot privacy and data-retention checklist

This is an operational checklist, not legal advice. The lyceum administration must approve
the retention periods, student/minor handling, access roles, and deletion process before pilot
launch. Do not claim that an approval exists until it is recorded by the operator.

## Data categories and handling

| Category | Purpose | Access and handling |
|---|---|---|
| Telegram account linkage | Authenticate a Mini App account | Numeric Telegram ID and display metadata stay server-side; never expose raw IDs to students |
| Official student roster | Provisional lyceum verification | Staff/integration only; no public enumeration; name/surname/group matching is weaker than school-issued proof |
| Profile information | Student profile and discovery | Only approved about, hobbies, HTTPS photo reference, interests, and minimum display fields are public |
| Memberships and requests | Club authorization and operations | Same-lyceum and role-scoped; removed members lose future access |
| Meetings and announcements | Club communication | Visible only to authorized active members and owners |
| Reports/moderation | Safety and administration | Reporter identity and internal review data stay staff-only |
| Operational logs | Reliability and incident response | Redact cookies, initData, tokens, invite URLs, chat IDs, roster values, and passwords |

## Required pilot decisions

- Administration-approved retention duration for roster records, profiles, memberships, reports,
  and operational logs.
- Process for correcting or resetting a roster claim, including staff authorization and history.
- Process for student access/correction/deletion requests, subject to administration policy.
- Staff role matrix, access review cadence, and incident notification contacts.
- Backup retention and secure disposal schedule.
- Whether external HTTPS profile-photo hosts are acceptable during the pilot. The application
  does not fetch or proxy these URLs, but the student's browser contacts the external host.

Minimize collection: no age, date of birth, phone number, address, or unrelated contact data
is required by the MVP. Keep the roster out of student API responses and avoid sending student
details to third-party monitoring services.
