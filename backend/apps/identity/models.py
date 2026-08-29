from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
        self,
        telegram_user_id: int,
        password: str | None,
        **extra_fields: Any,
    ) -> "User":
        if telegram_user_id is None:
            raise ValueError("A Telegram user ID is required.")

        user = self.model(telegram_user_id=telegram_user_id, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(
        self,
        telegram_user_id: int,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("status", AccountStatus.ACTIVE)
        return self._create_user(telegram_user_id, password, **extra_fields)

    def create_superuser(
        self,
        telegram_user_id: int,
        password: str | None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", AccountStatus.ACTIVE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusers must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_superuser=True.")
        if extra_fields.get("status") != AccountStatus.ACTIVE:
            raise ValueError("Superusers must have an active account status.")

        return self._create_user(telegram_user_id, password, **extra_fields)


class User(UUIDTimeStampedModel, AbstractBaseUser, PermissionsMixin):
    """Application account uniquely anchored to a Telegram numeric user ID."""

    telegram_user_id = models.PositiveBigIntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
        help_text="Telegram numeric user ID. This is the account identity, not a display field.",
    )
    telegram_username = models.CharField(max_length=128, blank=True)
    telegram_first_name = models.CharField(max_length=128, blank=True)
    telegram_last_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    is_staff = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "telegram_user_id"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("telegram_user_id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(telegram_user_id__gt=0),
                name="identity_user_telegram_id_positive",
            )
        ]

    def __str__(self) -> str:
        if self.telegram_username:
            return f"@{self.telegram_username} ({self.telegram_user_id})"
        return str(self.telegram_user_id)

    def get_full_name(self) -> str:
        return " ".join(
            part for part in (self.telegram_first_name, self.telegram_last_name) if part
        )

    def get_short_name(self) -> str:
        return self.telegram_first_name or str(self.telegram_user_id)

    @property
    def is_active(self) -> bool:
        """Django admin authentication hook backed by the account status enum."""

        return self.status == AccountStatus.ACTIVE

    @property
    def is_suspended(self) -> bool:
        return self.status == AccountStatus.SUSPENDED

    @property
    def is_verified(self) -> bool:
        try:
            student_record = self.student_record
        except ObjectDoesNotExist:
            return False
        return student_record.is_active and student_record.lyceum.is_active

    @property
    def can_access_student_features(self) -> bool:
        return self.is_active and self.is_verified
