from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent
from apps.common.throttling import ReportSubmissionThrottle

from .serializers import ReportCreateSerializer
from .services import create_report


class ReportCreateAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)
    throttle_classes = (ReportSubmissionThrottle,)

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = create_report(user=request.user, **serializer.validated_data)
        return Response(
            {"id": str(report.id), "status": report.status},
            status=status.HTTP_201_CREATED,
        )
