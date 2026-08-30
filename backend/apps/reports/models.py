from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.clubs.models import Club
from apps.common.models import UUIDTimeStampedModel
from apps.meetings.models import Announcement


class ReportReason(models.TextChoices):
    SPAM = "SPAM", "Spam"
    FAKE_INFORMATION = "FAKE_INFORMATION", "Fake information"
    HARASSMENT = "HARASSMENT", "Harassment"
    INAPPROPRIATE = "INAPPROPRIATE", "Inappropriate"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    REVIEWED = "REVIEWED", "Reviewed"
    ACTIONED = "ACTIONED", "Actioned"
    DISMISSED = "DISMISSED", "Dismissed"


class Report(UUIDTimeStampedModel):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_made",
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    reason = models.CharField(max_length=32, choices=ReportReason.choices)
    details = models.CharField(max_length=1_000, blank=True)
    status = models.CharField(
        max_length=12,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
        db_index=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports_reviewed",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(club__isnull=False, announcement__isnull=True)
                    | Q(club__isnull=True, announcement__isnull=False)
                ),
                name="reports_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=("reporter", "club"),
                condition=Q(status=ReportStatus.OPEN, club__isnull=False),
                name="reports_one_open_per_club",
            ),
            models.UniqueConstraint(
                fields=("reporter", "announcement"),
                condition=Q(status=ReportStatus.OPEN, announcement__isnull=False),
                name="reports_one_open_per_announcement",
            ),
        ]

    @property
    def target_type(self) -> str:
        return "CLUB" if self.club_id else "ANNOUNCEMENT"

    @property
    def target_id(self):  # type: ignore[no-untyped-def]
        return self.club_id or self.announcement_id
