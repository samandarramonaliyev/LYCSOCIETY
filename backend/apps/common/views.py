from __future__ import annotations

from django.db import OperationalError, connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckAPIView(APIView):
    """Minimal unauthenticated liveness/readiness endpoint for deployment checks."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except OperationalError:
            return Response(
                {"status": "unavailable", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"status": "ok", "database": "ok"})
