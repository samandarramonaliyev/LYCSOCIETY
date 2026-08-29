from __future__ import annotations

from datetime import UTC, datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord


VERIFIED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class LyceumModelTests(TestCase):
    def test_code_is_normalized_and_case_insensitively_unique(self) -> None:
        Lyceum.objects.create(name="Tashkent Lyceum", code="TASHKENT-1")

        lyceum = Lyceum.objects.get()
        self.assertEqual(lyceum.code, "tashkent-1")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Lyceum.objects.create(name="Another name", code="TASHKENT-1")


class StudentRecordModelTests(TestCase):
    def setUp(self) -> None:
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")

    def create_record(self, **overrides) -> StudentRecord:
        values = {
            "lyceum": self.lyceum,
            "external_student_key": "student-001",
            "first_name": "Sam",
            "last_name": "Karimov",
            "group_name": "10-B",
        }
        values.update(overrides)
        return StudentRecord.objects.create(**values)

    def test_identical_names_are_not_used_as_a_unique_identity(self) -> None:
        self.create_record(external_student_key="student-001")
        self.create_record(external_student_key="student-002")

        self.assertEqual(StudentRecord.objects.count(), 2)

    def test_external_student_key_is_unique_within_a_lyceum(self) -> None:
        self.create_record(external_student_key="STUDENT-001")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_record(external_student_key="student-001")

    def test_matching_fields_are_normalized_without_becoming_identity_fields(self) -> None:
        record = self.create_record(
            external_student_key=" Student-001 ",
            first_name="  Sam ",
            last_name=" KARIMOV ",
            group_name="  10-B  ",
        )

        self.assertEqual(record.external_student_key, "student-001")
        self.assertEqual(record.normalized_first_name, "sam")
        self.assertEqual(record.normalized_last_name, "karimov")
        self.assertEqual(record.normalized_group_name, "10-b")

    def test_external_student_key_can_repeat_in_another_lyceum(self) -> None:
        self.create_record(external_student_key="student-001")
        second_lyceum = Lyceum.objects.create(name="Samarkand Lyceum", code="samarkand-1")

        self.create_record(lyceum=second_lyceum, external_student_key="student-001")

        self.assertEqual(StudentRecord.objects.count(), 2)

    def test_one_user_cannot_be_linked_to_multiple_official_records(self) -> None:
        user = User.objects.create_user(telegram_user_id=100_000_001)
        self.create_record(verified_user=user, verified_at=VERIFIED_AT)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_record(
                    external_student_key="student-002",
                    verified_user=user,
                    verified_at=VERIFIED_AT,
                )

    def test_verified_user_relationship_is_one_to_one(self) -> None:
        verified_user_field = StudentRecord._meta.get_field("verified_user")

        self.assertTrue(verified_user_field.unique)

    def test_verified_user_and_timestamp_must_be_stored_together(self) -> None:
        user = User.objects.create_user(telegram_user_id=100_000_002)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_record(verified_user=user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_record(external_student_key="student-002", verified_at=VERIFIED_AT)
