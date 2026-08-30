from __future__ import annotations

import logging

from rest_framework.exceptions import Throttled
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


class SafeSimpleRateThrottle(SimpleRateThrottle):
    """Fail closed when shared throttle storage is unavailable."""

    def allow_request(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        try:
            return super().allow_request(request, view)
        except Exception as exc:
            logger.error(
                "Throttle cache unavailable",
                extra={"scope": self.scope, "exception_type": type(exc).__name__},
            )
            raise Throttled(detail="Temporarily unavailable.", wait=60) from None


class AuthenticatedUserThrottle(SafeSimpleRateThrottle):
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
