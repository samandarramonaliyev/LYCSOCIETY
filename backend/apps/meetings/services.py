from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from apps.lyceums.services.scoping import get_verified_lyceum
from apps.notifications.models import NotificationPreference, NotificationType
from apps.notifications.services import create_notification

from .models import Announcement, Meeting, MeetingRSVP, MeetingStatus


def _club(club_id, user, owner: bool = False) -> Club:  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    club = Club.objects.filter(
        pk=club_id,
        status=ClubStatus.ACTIVE,
        lyceum_id=lyceum.pk,
    ).first()
    if club is None or not ClubMembership.objects.filter(
        club=club,
        user=user,
        status=MembershipStatus.ACTIVE,
    ).exists():
        raise NotFound("Club not found.")
    if owner and club.owner_id != user.pk:
        raise PermissionDenied("Only the club owner may perform this action.")
    return club


def _notify(club, notification_type, title, body, preference_field, key) -> None:  # type: ignore[no-untyped-def]
    memberships = ClubMembership.objects.filter(
        club=club,
        status=MembershipStatus.ACTIVE,
    ).select_related("user")
    for membership in memberships:
        preference = NotificationPreference.objects.filter(user=membership.user).first()
        if preference is not None and not getattr(preference, preference_field):
            continue
        create_notification(
            recipient=membership.user,
            type=notification_type,
            title=title,
            body=body,
            dedupe_key=f"{key}:{membership.user_id}",
        )


@transaction.atomic
def create_meeting(*, club_id, user, data) -> Meeting:  # type: ignore[no-untyped-def]
    club = _club(club_id, user, owner=True)
    if data["starts_at"] <= timezone.now():
        raise ValidationError("Meeting must be in the future.")
    meeting = Meeting.objects.create(club=club, created_by=user, **data)
    _notify(
        club,
        NotificationType.MEETING_CREATED,
        "New meeting",
        meeting.title,
        "meeting_notifications",
        f"meeting:{meeting.pk}:created",
    )
    return meeting


@transaction.atomic
def create_announcement(*, club_id, user, data) -> Announcement:  # type: ignore[no-untyped-def]
    club = _club(club_id, user, owner=True)
    announcement = Announcement.objects.create(club=club, created_by=user, **data)
    _notify(
        club,
        NotificationType.ANNOUNCEMENT,
        announcement.title,
        announcement.message,
        "club_announcements",
        f"announcement:{announcement.pk}",
    )
    return announcement


def accessible_meeting(meeting_id, user) -> Meeting:  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    meeting = Meeting.objects.select_related("club").filter(
        pk=meeting_id,
        club__lyceum_id=lyceum.pk,
        club__status=ClubStatus.ACTIVE,
    ).first()
    if meeting is None or not ClubMembership.objects.filter(
        club=meeting.club,
        user=user,
        status=MembershipStatus.ACTIVE,
    ).exists():
        raise NotFound("Meeting not found.")
    return meeting


@transaction.atomic
def cancel_meeting(*, meeting_id, user) -> Meeting:  # type: ignore[no-untyped-def]
    visible = accessible_meeting(meeting_id, user)
    meeting = Meeting.objects.select_for_update().select_related("club").get(pk=visible.pk)
    if meeting.club.owner_id != user.pk:
        raise PermissionDenied("Only the club owner may cancel a meeting.")
    if meeting.status != MeetingStatus.SCHEDULED:
        raise ValidationError("The meeting is already cancelled.")
    meeting.status = MeetingStatus.CANCELLED
    meeting.save(update_fields=("status", "updated_at"))
    return meeting


@transaction.atomic
def set_rsvp(*, meeting_id, user, response: str) -> MeetingRSVP:  # type: ignore[no-untyped-def]
    visible = accessible_meeting(meeting_id, user)
    meeting = Meeting.objects.select_for_update().get(pk=visible.pk)
    if meeting.status != MeetingStatus.SCHEDULED:
        raise ValidationError("Attendance cannot be changed for a cancelled meeting.")
    rsvp, _ = MeetingRSVP.objects.update_or_create(
        meeting=meeting,
        user=user,
        defaults={"response": response},
    )
    return rsvp
