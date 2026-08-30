from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent

from .models import Announcement, Meeting
from .serializers import AnnouncementSerializer, MeetingSerializer, RSVPSerializer
from .services import (
    _club,
    accessible_meeting,
    cancel_meeting,
    create_announcement,
    create_meeting,
    set_rsvp,
)


class MeetingListCreateAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        meetings = Meeting.objects.filter(club=_club(club_id, request.user)).order_by("starts_at")
        return Response({"results": MeetingSerializer(meetings, many=True).data})

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        serializer = MeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meeting = create_meeting(
            club_id=club_id,
            user=request.user,
            data=dict(serializer.validated_data),
        )
        return Response(MeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)


class MeetingDetailAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def get(self, request, meeting_id) -> Response:  # type: ignore[no-untyped-def]
        return Response(MeetingSerializer(accessible_meeting(meeting_id, request.user)).data)

    def _cancel(self, request, meeting_id) -> Response:  # type: ignore[no-untyped-def]
        if request.data:
            raise serializers.ValidationError("Meeting cancellation does not accept fields.")
        meeting = cancel_meeting(meeting_id=meeting_id, user=request.user)
        return Response(MeetingSerializer(meeting).data)

    def patch(self, request, meeting_id) -> Response:  # type: ignore[no-untyped-def]
        return self._cancel(request, meeting_id)

    def post(self, request, meeting_id) -> Response:  # type: ignore[no-untyped-def]
        return self._cancel(request, meeting_id)


class AnnouncementListCreateAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        announcements = Announcement.objects.filter(
            club=_club(club_id, request.user)
        ).order_by("-created_at")
        return Response({"results": AnnouncementSerializer(announcements, many=True).data})

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = create_announcement(
            club_id=club_id,
            user=request.user,
            data=dict(serializer.validated_data),
        )
        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )


class RSVPAPIView(APIView):
    permission_classes = (IsVerifiedActiveStudent,)

    def post(self, request, meeting_id) -> Response:  # type: ignore[no-untyped-def]
        serializer = RSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rsvp = set_rsvp(
            meeting_id=meeting_id,
            user=request.user,
            response=serializer.validated_data["response"],
        )
        return Response(RSVPSerializer(rsvp).data)
