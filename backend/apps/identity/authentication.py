from __future__ import annotations

from rest_framework.authentication import BaseAuthentication, CSRFCheck

from apps.identity.exceptions import CsrfValidationFailed


class CsrfRequiredAnonymousAuthentication(BaseAuthentication):
    """Apply Django's CSRF check before an anonymous request creates a session."""

    def authenticate(self, request):  # type: ignore[no-untyped-def]
        check = CSRFCheck(lambda request: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise CsrfValidationFailed
        return None
