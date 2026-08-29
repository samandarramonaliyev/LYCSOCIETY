from __future__ import annotations

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.identity.models import AccountStatus, User


class UserModelTests(TestCase):
    def test_telegram_user_id_is_unique(self) -> None:
        User.objects.create_user(telegram_user_id=99_000_001)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(telegram_user_id=99_000_001)

    def test_telegram_user_id_must_be_positive(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(telegram_user_id=0)

    def test_account_status_controls_active_and_suspended_properties(self) -> None:
        user = User.objects.create_user(
            telegram_user_id=99_000_002,
            status=AccountStatus.SUSPENDED,
        )

        self.assertFalse(user.is_active)
        self.assertTrue(user.is_suspended)
        self.assertFalse(user.can_access_student_features)

    def test_superuser_requires_an_active_status(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                telegram_user_id=99_000_003,
                password="safely-managed-password",
                status=AccountStatus.SUSPENDED,
            )
