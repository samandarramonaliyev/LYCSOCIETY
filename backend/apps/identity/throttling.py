from __future__ import annotations

from apps.common.throttling import SafeSimpleRateThrottle


class TelegramAuthenticationThrottle(SafeSimpleRateThrottle):
    """Bound unauthenticated Telegram-init attempts by client address."""

    scope = "telegram_auth"

    def get_cache_key(self, request, view) -> str:  # type: ignore[no-untyped-def]
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class StudentVerificationThrottle(SafeSimpleRateThrottle):
    """Bound roster-match attempts without using roster data as a throttle key."""

    scope = "student_verification"

    def get_cache_key(self, request, view) -> str | None:  # type: ignore[no-untyped-def]
        user = request.user
        if not user or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(user.pk)}
