from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.serializers import serialize_account_state, verification_status_for
from apps.identity.throttling import StudentVerificationThrottle
from apps.lyceums.models import Lyceum, LyceumStatus
from apps.lyceums.serializers import VerificationClaimSerializer
from apps.lyceums.services.verification import claim_student_record


class VerificationStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        return Response(
            {
                "verification_status": verification_status_for(request.user),
                "can_access_student_features": request.user.can_access_student_features,
            }
        )


class VerificationLyceumListAPIView(APIView):
    """Expose only active lyceum choices needed during authenticated onboarding."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        lyceums = Lyceum.objects.filter(status=LyceumStatus.ACTIVE).order_by("name", "code")
        return Response(
            {
                "results": [
                    {
                        "id": str(lyceum.id),
                        "code": lyceum.code,
                        "name": lyceum.name,
                    }
                    for lyceum in lyceums
                ]
            }
        )


class VerificationClaimAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [StudentVerificationThrottle]

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        serializer = VerificationClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim_student_record(
            user=request.user,
            lyceum_id=serializer.validated_data["lyceum_id"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            group_name=serializer.validated_data["group"],
        )
        return Response({"user": serialize_account_state(request.user)})
