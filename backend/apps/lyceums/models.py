from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.common.models import UUIDTimeStampedModel


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


class LyceumStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class StudentRecordStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Lyceum(UUIDTimeStampedModel):
    """A first-class tenant boundary for official records and future clubs."""

    code = models.SlugField(
        max_length=50,
        help_text="Stable internal lyceum code. Stored in lowercase.",
    )
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=16,
        choices=LyceumStatus.choices,
        default=LyceumStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ("name", "code")
        constraints = [
            models.UniqueConstraint(
                Lower("code"),
                name="lyceums_lyceum_code_ci_unique",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.status == LyceumStatus.ACTIVE

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = self.code.strip().lower()
        super().save(*args, **kwargs)


class StudentRecord(UUIDTimeStampedModel):
    """Sensitive official roster data, deliberately separate from application users."""

    lyceum = models.ForeignKey(
        Lyceum,
        on_delete=models.PROTECT,
        related_name="student_records",
    )
    external_student_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Administration-provided stable identifier, if available.",
    )
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    normalized_first_name = models.CharField(max_length=128, editable=False)
    normalized_last_name = models.CharField(max_length=128, editable=False)
    group_name = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=StudentRecordStatus.choices,
        default=StudentRecordStatus.ACTIVE,
        db_index=True,
    )
    verification_code_hash = models.CharField(max_length=256, blank=True, editable=False)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.PositiveSmallIntegerField(default=0)
    verified_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="student_record",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("lyceum__name", "last_name", "first_name", "group_name")
        constraints = [
            models.UniqueConstraint(
                fields=("lyceum", "external_student_key"),
                condition=models.Q(external_student_key__isnull=False),
                name="lyceums_student_record_external_key_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(verified_user__isnull=True, verified_at__isnull=True)
                    | models.Q(verified_user__isnull=False, verified_at__isnull=False)
                ),
                name="lyceums_record_verified_pair_consistent",
            ),
            models.CheckConstraint(
                condition=models.Q(verification_attempts__gte=0),
                name="lyceums_record_verification_attempts_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=("lyceum", "status", "group_name"),
                name="lyceums_record_scope_group_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.group_name})"

    @property
    def is_active(self) -> bool:
        return self.status == StudentRecordStatus.ACTIVE

    @property
    def is_claimed(self) -> bool:
        return self.verified_user_id is not None

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.external_student_key = (
            _normalize_text(self.external_student_key) if self.external_student_key else None
        )
        self.normalized_first_name = _normalize_text(self.first_name)
        self.normalized_last_name = _normalize_text(self.last_name)

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "external_student_key",
                "normalized_first_name",
                "normalized_last_name",
            }

        super().save(*args, **kwargs)
