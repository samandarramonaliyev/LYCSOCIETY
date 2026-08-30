from __future__ import annotations

from uuid import UUID

from django.db.models import Prefetch, Q
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsVerifiedActiveStudent
from apps.common.throttling import JoinRequestThrottle
from apps.lyceums.services.scoping import get_verified_lyceum, scope_queryset_to_verified_lyceum
from apps.profiles.models import Interest

from .models import Club, ClubCategory, ClubStatus, JoinRequest, JoinRequestStatus, ClubMembership, MembershipStatus
from .serializers import (
    ClubSerializer,
    ClubWriteSerializer,
    JoinRequestDecisionSerializer,
    JoinRequestSerializer,
    MemberSerializer,
    OwnerClubSerializer,
)
from .services import (
    ClubNotFound,
    accept_join_request,
    cancel_join_request,
    create_club,
    create_join_request,
    leave_club,
    moderate_club,
    reject_join_request,
    resubmit_club,
    update_club,
    _scoped_club_for_user,
)


def _club_queryset(user):  # type: ignore[no-untyped-def]
    return scope_queryset_to_verified_lyceum(
        Club.objects.select_related("owner", "lyceum").filter(status=ClubStatus.ACTIVE),
        user=user,
    )


class ClubListCreateAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        queryset = _club_queryset(request.user)
        search = str(request.query_params.get("search", "")).strip()
        if len(search) > 80:
            raise serializers.ValidationError({"search": "Search is too long."})
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(short_description__icontains=search)
            )
        category = str(request.query_params.get("category", "")).strip().upper()
        if category:
            if category not in ClubCategory.values:
                raise serializers.ValidationError({"category": "Choose a valid club category."})
            queryset = queryset.filter(category=category)
        interest = request.query_params.get("interest")
        if interest:
            try:
                interest = UUID(str(interest))
            except (TypeError, ValueError):
                raise serializers.ValidationError({"interest": "A valid interest ID is required."})
            queryset = queryset.filter(interests__pk=interest, interests__is_active=True)
        queryset = queryset.distinct()
        return Response({"results": ClubSerializer(queryset, many=True, context={"request": request}).data})

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        serializer = ClubWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = create_club(user=request.user, validated_data=dict(serializer.validated_data))
        return Response(
            OwnerClubSerializer(club, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyClubAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        club = Club.objects.select_related("owner", "lyceum").filter(owner=request.user).first()
        if club is None:
            raise ClubNotFound
        if club.lyceum_id != get_verified_lyceum(request.user).pk:
            raise ClubNotFound
        return Response(OwnerClubSerializer(club, context={"request": request}).data)


class ClubDetailAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        club = _scoped_club_for_user(club_id=club_id, user=request.user)
        return Response(ClubSerializer(club, context={"request": request}).data)

    def patch(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        club = _scoped_club_for_user(
            club_id=club_id, user=request.user, include_owner_states=True
        )
        serializer = ClubWriteSerializer(club, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_club(
            club=club, user=request.user, validated_data=dict(serializer.validated_data)
        )
        return Response(OwnerClubSerializer(updated, context={"request": request}).data)


class ClubResubmitAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        club = _scoped_club_for_user(club_id=club_id, user=request.user, include_owner_states=True)
        updated = resubmit_club(club=club, user=request.user)
        return Response(OwnerClubSerializer(updated, context={"request": request}).data)


class ClubModerationAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        unexpected = set(request.data) - {"action", "reason"}
        if unexpected:
            raise serializers.ValidationError(
                {field: "This field is not writable." for field in sorted(unexpected)}
            )
        action = str(request.data.get("action", "")).strip().lower()
        reason = str(request.data.get("reason", ""))
        if action not in {"approve", "reject", "pause", "archive"}:
            raise serializers.ValidationError({"action": "Unsupported moderation action."})
        club = moderate_club(club_id=club_id, action=action, reason=reason)
        return Response(OwnerClubSerializer(club, context={"request": request}).data)


class JoinRequestListCreateAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get_throttles(self):  # type: ignore[no-untyped-def]
        return [JoinRequestThrottle()] if self.request.method == "POST" else []

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        if request.data:
            raise serializers.ValidationError("Join requests do not accept arbitrary fields.")
        join_request = create_join_request(club_id=club_id, user=request.user)
        return Response(JoinRequestSerializer(join_request, context={"request": request}).data, status=201)

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        club = _scoped_club_for_user(club_id=club_id, user=request.user, include_owner_states=True)
        if club.owner_id != request.user.pk:
            raise ClubNotFound
        requests = JoinRequest.objects.select_related("user", "club").prefetch_related(
            Prefetch("user__profile__interests", queryset=Interest.objects.filter(is_active=True))
        ).filter(club=club, status=JoinRequestStatus.PENDING)
        return Response({"results": JoinRequestSerializer(requests, many=True, context={"request": request}).data})


def _join_request_for_user(request_id, user, action):  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    filters = {
        "pk": request_id,
        "club__lyceum_id": lyceum.pk,
    }
    if action in {"accept", "reject"}:
        filters["club__owner_id"] = user.pk
    elif action == "cancel":
        filters["user_id"] = user.pk
    join_request = JoinRequest.objects.select_related("club").filter(
        **filters
    ).first()
    if join_request is None:
        raise ClubNotFound
    return join_request


class JoinRequestActionAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def post(self, request, request_id, action) -> Response:  # type: ignore[no-untyped-def]
        if action == "accept":
            _join_request_for_user(request_id, request.user, action)
            membership = accept_join_request(request_id=request_id, owner=request.user)
            return Response(MemberSerializer(membership, context={"request": request}).data)
        if action == "reject":
            serializer = JoinRequestDecisionSerializer(data=request.data)
            unexpected = set(request.data) - set(serializer.fields)
            if unexpected:
                raise serializers.ValidationError({field: "This field is not writable." for field in unexpected})
            serializer.is_valid(raise_exception=True)
            _join_request_for_user(request_id, request.user, action)
            result = reject_join_request(
                request_id=request_id,
                owner=request.user,
                reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(JoinRequestSerializer(result, context={"request": request}).data)
        if action == "cancel":
            _join_request_for_user(request_id, request.user, action)
            result = cancel_join_request(request_id=request_id, user=request.user)
            return Response(JoinRequestSerializer(result, context={"request": request}).data)
        raise serializers.ValidationError({"action": "Unsupported request action."})


class MemberListAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def get(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        club = _scoped_club_for_user(club_id=club_id, user=request.user)
        is_member = ClubMembership.objects.filter(
            club=club, user=request.user, status=MembershipStatus.ACTIVE
        ).exists()
        if not is_member:
            raise PermissionDenied("Club membership is required to view members.")
        members = ClubMembership.objects.select_related("user", "club").prefetch_related(
            Prefetch("user__profile__interests", queryset=Interest.objects.filter(is_active=True))
        ).filter(club=club, status=MembershipStatus.ACTIVE)
        return Response({"results": MemberSerializer(members, many=True, context={"request": request}).data})


class LeaveClubAPIView(APIView):
    permission_classes = [IsVerifiedActiveStudent]

    def post(self, request, club_id) -> Response:  # type: ignore[no-untyped-def]
        leave_club(club_id=club_id, user=request.user)
        return Response(status=204)
