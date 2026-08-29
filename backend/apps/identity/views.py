from __future__ import annotations

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.serializers import (
    TelegramAuthenticationSerializer,
    serialize_account_state,
)
from apps.identity.services.telegram import authenticate_telegram_user
from apps.identity.throttling import TelegramAuthenticationThrottle


class TelegramAuthenticationAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [TelegramAuthenticationThrottle]

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


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        return Response(serialize_account_state(request.user))
