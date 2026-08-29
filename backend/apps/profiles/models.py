from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify

from apps.common.models import UUIDTimeStampedModel

if TYPE_CHECKING:
    from apps.lyceums.models import Lyceum, StudentRecord


class Interest(UUIDTimeStampedModel):
    """Reusable, staff-managed interest vocabulary."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(Lower("name"), name="profiles_interest_name_ci_unique"),
            models.UniqueConstraint(Lower("slug"), name="profiles_interest_slug_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = " ".join(self.name.strip().split())
        self.slug = slugify(self.slug or self.name)
        super().save(*args, **kwargs)


class StudentProfile(UUIDTimeStampedModel):
    """User-editable profile data kept separate from verified roster information."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    about = models.TextField(max_length=1_000, blank=True)
    hobbies = models.CharField(max_length=500, blank=True)
    profile_photo_url = models.URLField(max_length=500, blank=True)
    interests = models.ManyToManyField(
        Interest,
        blank=True,
        related_name="profiles",
    )

    class Meta:
        ordering = ("user__telegram_user_id",)

    def __str__(self) -> str:
        return f"Profile for {self.user}"

    @property
    def official_student_record(self) -> "StudentRecord | None":
        try:
            return self.user.student_record
        except ObjectDoesNotExist:
            return None

    @property
    def verified_lyceum(self) -> "Lyceum | None":
        student_record = self.official_student_record
        return student_record.lyceum if student_record else None

    @property
    def verified_group_name(self) -> str | None:
        student_record = self.official_student_record
        return student_record.group_name if student_record else None
