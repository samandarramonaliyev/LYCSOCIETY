from __future__ import annotations

from django.db.models import Prefetch, Q
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent

from .models import Interest, StudentProfile
from .serializers import InterestSerializer, SelfProfileSerializer


def _profile_for(user) -> StudentProfile:  # type: ignore[no-untyped-def]
    return (
        StudentProfile.objects.select_related("user__student_record__lyceum")
        .prefetch_related(
            Prefetch(
                "interests",
                queryset=Interest.objects.filter(is_active=True).order_by("name", "slug"),
            )
        )
        .get(user=user)
    )


class ProfileAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        return Response(SelfProfileSerializer(_profile_for(request.user)).data)

    def patch(self, request) -> Response:  # type: ignore[no-untyped-def]
        serializer = SelfProfileSerializer(_profile_for(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(SelfProfileSerializer(_profile_for(request.user)).data)


class InterestListAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        search = str(request.query_params.get("search", "")).strip()
        if len(search) > 80:
            raise serializers.ValidationError({"search": "Search is too long."})
        queryset = Interest.objects.filter(is_active=True)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return Response({"results": InterestSerializer(queryset.order_by("name", "slug"), many=True).data})
