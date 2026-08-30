from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, NotFound

from apps.clubs.models import Club, ClubMembership, ClubStatus, MembershipStatus
from apps.identity.models import User
from apps.lyceums.services.scoping import get_verified_lyceum
from apps.meetings.models import Announcement

from .models import Report, ReportStatus


class DuplicateOpenReport(APIException):
    status_code = 409
    default_detail = "You already have an open report for this content."
    default_code = "REPORT_ALREADY_OPEN"


def _visible_target(*, user: User, target_type: str, target_id):  # type: ignore[no-untyped-def]
    lyceum = get_verified_lyceum(user)
    if target_type == "CLUB":
        club = Club.objects.filter(
            pk=target_id,
            lyceum_id=lyceum.pk,
            status=ClubStatus.ACTIVE,
        ).first()
        if club is None:
            raise NotFound("Report target not found.")
        return {"club": club}

    announcement = Announcement.objects.select_related("club").filter(
        pk=target_id,
        club__lyceum_id=lyceum.pk,
        club__status=ClubStatus.ACTIVE,
    ).first()
    if announcement is None or not ClubMembership.objects.filter(
        club=announcement.club,
        user=user,
        status=MembershipStatus.ACTIVE,
    ).exists():
        raise NotFound("Report target not found.")
    return {"announcement": announcement}


def create_report(
    *,
    user: User,
    target_type: str,
    target_id,
    reason: str,
    details: str,
) -> Report:
    target = _visible_target(user=user, target_type=target_type, target_id=target_id)
    try:
        with transaction.atomic():
            duplicate_filter = {
                "reporter": user,
                "status": ReportStatus.OPEN,
                **target,
            }
            if Report.objects.filter(**duplicate_filter).exists():
                raise DuplicateOpenReport
            return Report.objects.create(
                reporter=user,
                reason=reason,
                details=details,
                **target,
            )
    except IntegrityError as exc:
        raise DuplicateOpenReport from exc
