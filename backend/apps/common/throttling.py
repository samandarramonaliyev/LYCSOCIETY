from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class AuthenticatedUserThrottle(SimpleRateThrottle):
    """Rate-limit a sensitive action by the authenticated application account."""

    def get_cache_key(self, request, view) -> str | None:  # type: ignore[no-untyped-def]
        user = request.user
        if not user or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(user.pk)}


class JoinRequestThrottle(AuthenticatedUserThrottle):
    scope = "join_request"


class ReportSubmissionThrottle(AuthenticatedUserThrottle):
    scope = "report_submission"


class TelegramInviteThrottle(AuthenticatedUserThrottle):
    scope = "telegram_invite"
