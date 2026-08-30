# Controlled pilot smoke checklist

Use a non-production test account and, for Telegram integration, a non-production test group.
Record date, platform, build version, and any unavailable client platform.

## Browser and Mini App

- [ ] HTTPS URL loads the built SPA; no Vite dev server is exposed.
- [ ] Normal browser without Telegram data cannot bypass authentication.
- [ ] Telegram Android authentication and safe-area layout work.
- [ ] Telegram iOS and Desktop are tested or explicitly marked unavailable.
- [ ] BackButton, keyboard, bottom navigation, and viewport behavior are usable.

## Verification and profile

- [ ] Valid roster details verify once and show generic failure for invalid details.
- [ ] Profile displays immutable verified fields.
- [ ] About, hobbies, and interests save; the ten-interest limit is enforced.

## Clubs and membership

- [ ] Student creates one pending club; client cannot select owner, lyceum, role, or status.
- [ ] Staff approval exposes the club only in its trusted lyceum.
- [ ] Student submits/cancels a join request; owner accepts/rejects the correct request only.
- [ ] Two additional memberships succeed; a fourth active membership is rejected.

## Meetings, announcements, notifications, reports

- [ ] Owner creates a future meeting; active member sets GOING and NOT_GOING RSVP.
- [ ] Owner creates an announcement; authorized members can read it.
- [ ] Notification arrives for the correct recipient; read state and preferences work.
- [ ] Verified student submits a visible club/announcement report; reporter identity is hidden.

## Telegram group and webhook

- [ ] `telegram_webhook_status` reports a configured webhook with only `message` and `chat_join_request` allowed; no secret is displayed.
- [ ] Owner links a test group through the challenge, from the same Telegram account, with the bot as administrator and `can_invite_users`.
- [ ] Active member receives a ten-minute join-request invite; it is not persisted.
- [ ] Bot approval rechecks Telegram identity, verified-active account, linked group, active club, and current active membership; unknown, removed, suspended, and unverified accounts are declined.
- [ ] Removed member cannot obtain new access; owner can unlink the group.

## Mandatory Telegram client/frame test

- [ ] On Android, iOS, and Desktop (or with each unavailable client recorded), open the
  Mini App from the configured bot and verify authentication and navigation work while
  `X-Frame-Options=DENY` and the documented frame-denying CSP are active.

## Admin and operations

- [ ] Staff can moderate a club and reset a claim with least privilege.
- [ ] Health endpoint returns only minimal application/database state.
- [ ] Error logs contain no initData, cookies, invite links, chat IDs, roster values, or tokens.
- [ ] Backup restore rehearsal and rollback decision are recorded before pilot traffic.
