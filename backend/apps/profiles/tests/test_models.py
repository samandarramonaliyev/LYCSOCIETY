from __future__ import annotations

from datetime import UTC, datetime

from django.test import TestCase

from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.profiles.models import Interest, StudentProfile


VERIFIED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class StudentProfileModelTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(telegram_user_id=200_000_001)
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")

    def test_profile_is_created_for_each_account(self) -> None:
        self.assertTrue(StudentProfile.objects.filter(user=self.user).exists())

    def test_verified_fields_are_derived_from_official_record_not_profile_fields(self) -> None:
        StudentRecord.objects.create(
            lyceum=self.lyceum,
            external_student_key="student-001",
            first_name="Sam",
            last_name="Karimov",
            group_name="10-B",
            verified_user=self.user,
            verified_at=VERIFIED_AT,
        )
        profile = self.user.profile
        profile.about = "Interested in Python."
        profile.hobbies = "Chess"
        profile.save()

        field_names = {field.name for field in StudentProfile._meta.fields}
        self.assertNotIn("lyceum", field_names)
        self.assertNotIn("group_name", field_names)
        self.assertEqual(profile.verified_lyceum, self.lyceum)
        self.assertEqual(profile.verified_group_name, "10-B")

    def test_interests_are_reusable_and_not_duplicated_for_a_profile(self) -> None:
        programming = Interest.objects.create(name="Programming", slug="PROGRAMMING")
        second_user = User.objects.create_user(telegram_user_id=200_000_002)

        self.user.profile.interests.add(programming, programming)
        second_user.profile.interests.add(programming)

        self.assertEqual(self.user.profile.interests.count(), 1)
        self.assertEqual(second_user.profile.interests.get(), programming)
        self.assertEqual(programming.slug, "programming")
