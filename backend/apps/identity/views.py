from __future__ import annotations

from django.conf import settings
from django.contrib.auth import login, logout
from django.http import Http404
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.authentication import CsrfRequiredAnonymousAuthentication
from apps.identity.serializers import (
    LocalDevelopmentAuthenticationSerializer,
    TelegramAuthenticationSerializer,
    serialize_account_state,
)
from apps.identity.models import User
from apps.identity.services.telegram import authenticate_telegram_user
from apps.identity.throttling import TelegramAuthenticationThrottle


class CsrfTokenAPIView(APIView):
    """Issue a CSRF token before the unauthenticated session-login POST."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        return Response({"csrf_token": get_token(request)})


class TelegramAuthenticationAPIView(APIView):
    authentication_classes = [CsrfRequiredAnonymousAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [TelegramAuthenticationThrottle]

    def get_authenticate_header(self, request) -> str:  # type: ignore[no-untyped-def]
        """Keep invalid Telegram credentials on the API's documented 401 path."""

        return "Telegram"

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        serializer = TelegramAuthenticationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate_telegram_user(serializer.validated_data["init_data"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        return Response(
            {
                "authenticated": True,
                "csrf_token": get_token(request),
                "user": serialize_account_state(user),
            },
            status=status.HTTP_200_OK,
        )


class LocalDevelopmentAuthenticationAPIView(APIView):
    """Create a CSRF-protected local session only for explicitly enabled debug mode."""

    authentication_classes = [CsrfRequiredAnonymousAuthentication]
    permission_classes = [AllowAny]

    @staticmethod
    def _is_enabled() -> bool:
        return bool(
            settings.DEBUG
            and getattr(settings, "LOCAL_DEV_AUTH_AVAILABLE", False)
            and getattr(settings, "LOCAL_DEV_AUTH_ENABLED", False)
        )

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        if not self._is_enabled():
            raise Http404

        serializer = LocalDevelopmentAuthenticationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_user_id = getattr(settings, "LOCAL_DEV_TELEGRAM_USER_ID", 0)
        if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
            raise Http404

        user, _ = User.objects.get_or_create(telegram_user_id=telegram_user_id)
        if user.is_staff or user.is_superuser:
            raise PermissionDenied("The configured local development account is not eligible.")
        if not user.is_active:
            raise PermissionDenied("The configured local development account is unavailable.")

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(
            {
                "authenticated": True,
                "csrf_token": get_token(request),
                "user": serialize_account_state(user),
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        return Response(serialize_account_state(request.user))
