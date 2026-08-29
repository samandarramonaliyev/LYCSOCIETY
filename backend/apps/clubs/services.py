from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from apps.identity.models import User
from apps.lyceums.services.scoping import get_verified_lyceum
from apps.profiles.models import Interest
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification

from .models import (
    Club,
    ClubMembership,
    ClubStatus,
    JoinRequest,
    JoinRequestStatus,
    MembershipRole,
    MembershipStatus,
)

MAX_ACTIVE_MEMBERSHIPS = 3


class ClubAlreadyOwned(APIException):
    status_code = 409
    default_detail = "You already own a club."
    default_code = "CLUB_ALREADY_EXISTS"


class MembershipLimitReached(APIException):
    status_code = 409
    default_detail = "You cannot belong to more than three active clubs."
    default_code = "MEMBERSHIP_LIMIT_REACHED"


class ClubStateConflict(APIException):
    status_code = 409
    default_detail = "This club cannot be changed in its current state."
    default_code = "CLUB_STATE_CONFLICT"


class JoinRequestConflict(APIException):
    status_code = 409
    default_detail = "This join request cannot be created or changed."
    default_code = "JOIN_REQUEST_CONFLICT"


class ClubInputInvalid(APIException):
    status_code = 400
    default_detail = "One or more selected interests are unavailable."
    default_code = "INVALID_CLUB_INPUT"


class ModerationInvalid(APIException):
    status_code = 400
    default_detail = "The moderation action is invalid."
    default_code = "INVALID_MODERATION_ACTION"


class ClubNotFound(NotFound):
    default_detail = "Club not found."
    default_code = "CLUB_NOT_FOUND"


class ClubNotOwner(PermissionDenied):
    default_detail = "Only the club owner may perform this action."
    default_code = "CLUB_OWNER_REQUIRED"


def _active_interests(ids: Iterable[Any]) -> list[Interest]:
    unique_ids = list(dict.fromkeys(ids))
    interests = list(
        Interest.objects.select_for_update().filter(pk__in=unique_ids, is_active=True)
    )
    if len(interests) != len(unique_ids):
        raise ClubInputInvalid
    return interests


def _verify_active_user(user: User) -> None:
    if not user.can_access_student_features:
        raise PermissionDenied("A verified active student account is required.")


def _active_membership_count(user: User) -> int:
    return ClubMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE).count()


@transaction.atomic
def create_club(*, user: User, validated_data: dict[str, Any]) -> Club:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    _verify_active_user(locked_user)
    if Club.objects.filter(owner_id=locked_user.pk).exists():
        raise ClubAlreadyOwned
    if _active_membership_count(locked_user) >= MAX_ACTIVE_MEMBERSHIPS:
        raise MembershipLimitReached

    lyceum = get_verified_lyceum(locked_user)
    locked_interests = _active_interests(validated_data.pop("interest_ids", []))
    club = Club.objects.create(
        owner=locked_user,
        lyceum=lyceum,
        status=ClubStatus.PENDING,
        **validated_data,
    )
    club.interests.set(locked_interests)
    ClubMembership.objects.create(
        club=club,
        user=locked_user,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    return club


@transaction.atomic
def update_club(*, club: Club, user: User, validated_data: dict[str, Any]) -> Club:
    _verify_active_user(user)
    locked_club = Club.objects.select_for_update().filter(pk=club.pk).first()
    if locked_club is None:
        raise ClubNotFound
    if locked_club.owner_id != user.pk:
        raise ClubNotOwner
    if locked_club.status == ClubStatus.ARCHIVED:
        raise ClubStateConflict
    locked_interests = (
        _active_interests(validated_data.pop("interest_ids", []))
        if "interest_ids" in validated_data
        else None
    )
    for field, value in validated_data.items():
        setattr(locked_club, field, value)
    if validated_data:
        locked_club.save(update_fields=(*validated_data.keys(), "updated_at"))
    if locked_interests is not None:
        locked_club.interests.set(locked_interests)
    return locked_club


@transaction.atomic
def resubmit_club(*, club: Club, user: User) -> Club:
    _verify_active_user(user)
    locked_club = Club.objects.select_for_update().filter(pk=club.pk).first()
    if locked_club is None:
        raise ClubNotFound
    if locked_club.owner_id != user.pk:
        raise ClubNotOwner
    if locked_club.status != ClubStatus.REJECTED:
        raise ClubStateConflict
    locked_club.status = ClubStatus.PENDING
    locked_club.rejection_reason = ""
    locked_club.save(update_fields=("status", "rejection_reason", "updated_at"))
    return locked_club


@transaction.atomic
def moderate_club(*, club_id, action: str, reason: str = "") -> Club:
    club = Club.objects.select_for_update().filter(pk=club_id).first()
    if club is None:
        raise ClubNotFound
    if action == "approve":
        if club.status not in (ClubStatus.PENDING, ClubStatus.REJECTED):
            raise ClubStateConflict
        club.status = ClubStatus.ACTIVE
        club.rejection_reason = ""
    elif action == "reject":
        if club.status not in (ClubStatus.PENDING, ClubStatus.ACTIVE):
            raise ClubStateConflict
        if not reason.strip():
            raise ModerationInvalid("A rejection reason is required.")
        club.status = ClubStatus.REJECTED
        club.rejection_reason = reason.strip()
    elif action == "pause":
        if club.status != ClubStatus.ACTIVE:
            raise ClubStateConflict
        club.status = ClubStatus.PAUSED
    elif action == "archive":
        if club.status == ClubStatus.ARCHIVED:
            raise ClubStateConflict
        club.status = ClubStatus.ARCHIVED
    else:
        raise ModerationInvalid("Unsupported club moderation action.")
    club.save(update_fields=("status", "rejection_reason", "updated_at"))
    if action == "approve":
        create_notification(recipient=club.owner, type=NotificationType.CLUB_APPROVED, title="Club approved", body=f"Your club '{club.name}' was approved.", dedupe_key=f"club:{club.pk}:approved")
    elif action == "reject":
        create_notification(recipient=club.owner, type=NotificationType.CLUB_REJECTED, title="Club rejected", body=club.rejection_reason, dedupe_key=f"club:{club.pk}:rejected:{club.updated_at.isoformat()}")
    return club


def _scoped_club_for_user(*, club_id, user: User, include_owner_states: bool = False) -> Club:
    lyceum = get_verified_lyceum(user)
    queryset = Club.objects.select_related("owner", "lyceum").filter(
        lyceum_id=lyceum.pk, pk=club_id
    )
    if include_owner_states:
        queryset = queryset.filter(owner_id=user.pk)
    else:
        queryset = queryset.filter(status=ClubStatus.ACTIVE)
    club = queryset.first()
    if club is None:
        raise ClubNotFound
    return club


@transaction.atomic
def create_join_request(*, club_id, user: User) -> JoinRequest:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    _verify_active_user(locked_user)
    lyceum = get_verified_lyceum(locked_user)
    club = Club.objects.select_for_update().filter(pk=club_id, lyceum_id=lyceum.pk).first()
    if club is None or club.status != ClubStatus.ACTIVE:
        raise ClubNotFound
    if club.owner_id == locked_user.pk:
        raise JoinRequestConflict
    if ClubMembership.objects.filter(
        club=club, user=locked_user, status=MembershipStatus.ACTIVE
    ).exists():
        raise JoinRequestConflict
    if JoinRequest.objects.filter(
        club=club, user=locked_user, status=JoinRequestStatus.PENDING
    ).exists():
        raise JoinRequestConflict
    if _active_membership_count(locked_user) >= MAX_ACTIVE_MEMBERSHIPS:
        raise MembershipLimitReached
    request = JoinRequest.objects.create(club=club, user=locked_user, status=JoinRequestStatus.PENDING)
    create_notification(recipient=club.owner, type=NotificationType.JOIN_REQUEST_CREATED, title="New join request", body=f"A student requested to join {club.name}.", dedupe_key=f"join-request:{request.pk}:created")
    return request


@transaction.atomic
def accept_join_request(*, request_id, owner: User) -> ClubMembership:
    join_request = JoinRequest.objects.filter(pk=request_id).first()
    if join_request is None:
        raise ClubNotFound
    locked_owner = User.objects.select_for_update().get(pk=owner.pk)
    _verify_active_user(locked_owner)
    trusted_lyceum = get_verified_lyceum(locked_owner)
    club = Club.objects.select_for_update().filter(pk=join_request.club_id).first()
    if club is None:
        raise ClubNotFound
    join_request = JoinRequest.objects.select_for_update().filter(pk=request_id).first()
    if join_request is None:
        raise ClubNotFound
    if club.owner_id != owner.pk:
        raise ClubNotOwner
    if club.lyceum_id != trusted_lyceum.pk:
        raise ClubNotFound
    locked_user = User.objects.select_for_update().get(pk=join_request.user_id)
    _verify_active_user(locked_user)
    if join_request.status != JoinRequestStatus.PENDING or club.status != ClubStatus.ACTIVE:
        raise JoinRequestConflict
    if ClubMembership.objects.filter(
        club=club, user=locked_user, status=MembershipStatus.ACTIVE
    ).exists():
        raise JoinRequestConflict
    if _active_membership_count(locked_user) >= MAX_ACTIVE_MEMBERSHIPS:
        raise MembershipLimitReached
    membership = ClubMembership.objects.create(
        club=club,
        user=locked_user,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    join_request.status = JoinRequestStatus.ACCEPTED
    join_request.save(update_fields=("status", "updated_at"))
    create_notification(recipient=locked_user, type=NotificationType.JOIN_REQUEST_ACCEPTED, title="Join request accepted", body=f"Your request to join {club.name} was accepted.", dedupe_key=f"join-request:{join_request.pk}:accepted")
    return membership


@transaction.atomic
def reject_join_request(*, request_id, owner: User, reason: str = "") -> JoinRequest:
    join_request = JoinRequest.objects.select_for_update().select_related("club").filter(pk=request_id).first()
    if join_request is None:
        raise ClubNotFound
    if join_request.club.lyceum_id != get_verified_lyceum(owner).pk:
        raise ClubNotFound
    if join_request.club.owner_id != owner.pk:
        raise ClubNotOwner
    if join_request.status != JoinRequestStatus.PENDING:
        raise JoinRequestConflict
    join_request.status = JoinRequestStatus.REJECTED
    join_request.rejection_reason = reason.strip()
    join_request.save(update_fields=("status", "rejection_reason", "updated_at"))
    create_notification(recipient=join_request.user, type=NotificationType.JOIN_REQUEST_REJECTED, title="Join request rejected", body=join_request.rejection_reason or f"Your request to join {join_request.club.name} was rejected.", dedupe_key=f"join-request:{join_request.pk}:rejected")
    return join_request


@transaction.atomic
def cancel_join_request(*, request_id, user: User) -> JoinRequest:
    join_request = JoinRequest.objects.select_for_update().select_related("club").filter(pk=request_id).first()
    if join_request is None:
        raise ClubNotFound
    if join_request.club.lyceum_id != get_verified_lyceum(user).pk:
        raise ClubNotFound
    if join_request.user_id != user.pk:
        raise PermissionDenied
    if join_request.status != JoinRequestStatus.PENDING:
        raise JoinRequestConflict
    join_request.status = JoinRequestStatus.CANCELLED
    join_request.save(update_fields=("status", "updated_at"))
    return join_request


@transaction.atomic
def leave_club(*, club_id, user: User) -> None:
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    club = Club.objects.select_for_update().filter(pk=club_id).first()
    if club is None or club.lyceum_id != get_verified_lyceum(locked_user).pk:
        raise ClubNotFound
    membership = ClubMembership.objects.select_for_update().filter(
        club=club, user=locked_user, status=MembershipStatus.ACTIVE
    ).first()
    if membership is None:
        raise JoinRequestConflict
    if membership.role == MembershipRole.OWNER:
        raise ClubStateConflict("Owners must archive their club instead of leaving it.")
    membership.status = MembershipStatus.REMOVED
    membership.left_at = timezone.now()
    membership.save(update_fields=("status", "left_at", "updated_at"))
