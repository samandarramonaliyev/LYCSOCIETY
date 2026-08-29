from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel
from apps.lyceums.models import Lyceum
from apps.profiles.models import Interest


class ClubStatus(models.TextChoices):
    PENDING = "PENDING", "Pending review"
    ACTIVE = "ACTIVE", "Active"
    REJECTED = "REJECTED", "Rejected"
    PAUSED = "PAUSED", "Paused"
    ARCHIVED = "ARCHIVED", "Archived"


class ClubCategory(models.TextChoices):
    TECHNOLOGY = "TECHNOLOGY", "Technology"
    SCIENCE = "SCIENCE", "Science"
    BUSINESS = "BUSINESS", "Business"
    SPORTS = "SPORTS", "Sports"
    ARTS = "ARTS", "Arts"
    LANGUAGES = "LANGUAGES", "Languages"
    ACADEMIC = "ACADEMIC", "Academic"
    SOCIAL = "SOCIAL", "Social"
    OTHER = "OTHER", "Other"


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    MEMBER = "MEMBER", "Member"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REMOVED = "REMOVED", "Removed"


class JoinRequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class Club(UUIDTimeStampedModel):
    lyceum = models.ForeignKey(Lyceum, on_delete=models.PROTECT, related_name="clubs")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_clubs",
    )
    name = models.CharField(max_length=120)
    short_description = models.CharField(max_length=280)
    description = models.TextField(max_length=5_000)
    category = models.CharField(max_length=16, choices=ClubCategory.choices)
    status = models.CharField(
        max_length=16,
        choices=ClubStatus.choices,
        default=ClubStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(max_length=1_000, blank=True)
    interests = models.ManyToManyField(Interest, blank=True, related_name="clubs")

    class Meta:
        ordering = ("-created_at", "name")
        constraints = [
            models.UniqueConstraint(fields=("owner",), name="clubs_one_per_owner"),
            models.CheckConstraint(
                condition=Q(status=ClubStatus.REJECTED, rejection_reason__gt="")
                | ~Q(status=ClubStatus.REJECTED),
                name="clubs_rejected_requires_reason",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ClubMembership(UUIDTimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="club_memberships",
    )
    role = models.CharField(max_length=16, choices=MembershipRole.choices)
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("joined_at", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("club", "user"),
                condition=Q(status=MembershipStatus.ACTIVE),
                name="clubs_active_membership_unique",
            ),
            models.UniqueConstraint(
                fields=("club",),
                condition=Q(role=MembershipRole.OWNER, status=MembershipStatus.ACTIVE),
                name="clubs_one_owner_membership",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=MembershipStatus.ACTIVE, left_at__isnull=True)
                    | Q(status=MembershipStatus.REMOVED, left_at__isnull=False)
                ),
                name="clubs_membership_status_left_consistent",
            ),
        ]

    def clean(self) -> None:
        if self.club_id and self.user_id:
            owner_id = Club.objects.filter(pk=self.club_id).values_list("owner_id", flat=True).first()
            if self.role == MembershipRole.OWNER and owner_id != self.user_id:
                raise ValidationError("The owner membership must belong to Club.owner.")
            if self.role == MembershipRole.MEMBER and owner_id == self.user_id:
                raise ValidationError("The club owner must use the OWNER role.")

    def save(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        self.full_clean()
        return super().save(*args, **kwargs)


class JoinRequest(UUIDTimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="club_join_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(max_length=1_000, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("club", "user"),
                condition=Q(status=JoinRequestStatus.PENDING),
                name="clubs_pending_join_request_unique",
            ),
        ]
