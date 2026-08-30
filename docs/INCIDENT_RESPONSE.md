# LYC Society pilot incident response

This runbook is intentionally small. Preserve evidence, restrict access, and rotate credentials
before attempting broad cleanup. Record times, affected account/object IDs where safe, operator,
actions, and decisions without copying secrets or student roster values into the incident log.

## First response

1. Declare an incident owner and record the UTC start time.
2. Contain the affected surface (disable the integration, admin account, or endpoint if needed)
   without deleting evidence.
3. Rotate the relevant credential immediately and restart only the services that need it.
4. Preserve redacted application/proxy/audit logs and database/cache health information.
5. Determine affected users and lyceums using least-privilege staff access.
6. Notify the administration and follow its student/minor privacy process.
7. Record remediation and a post-incident review before re-enabling traffic.

## Credential incidents

### Telegram bot token leak

1. Revoke and create a fresh token in BotFather.
2. Replace the production secret and restart the backend and bot runtime.
3. Reconfigure/verify the webhook or polling runtime and group permissions.
4. Inspect outbound delivery and Bot API error categories for misuse.
5. Never reuse the old token or place either token in a ticket, log, or commit.

### Django, database, or cache credential leak

Rotate the secret in the provider, restart affected services, invalidate sessions if the Django
secret was exposed, inspect access logs, and verify TLS/network restrictions. Do not publish the
credential in an issue or incident narrative.

## Account and data incidents

- **Compromised staff account:** disable it, rotate credentials, review admin changes and
  roster/group/report access, then restore only with a new least-privilege account.
- **Suspected student-data exposure:** stop the leaking route/integration, preserve evidence,
  identify the exact lyceum/object scope, notify administration, and follow approved privacy
  notification and retention procedures.
- **Abusive club or report spam:** apply existing moderation controls, preserve report IDs,
  throttle/disable the abusive account, and avoid exposing reporter identity.
- **Cache outage:** treat authentication and sensitive writes as unavailable; restore the
  shared cache and verify replay/throttle behavior before reopening traffic.

Never respond with blanket database deletion. Use a verified backup/restore procedure only after
the administration approves the recovery target and evidence preservation plan.
