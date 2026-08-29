from __future__ import annotations

from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.lyceums.services.importing import import_student_records


class StudentRecordImportTests(TestCase):
    def setUp(self) -> None:
        self.lyceum = Lyceum.objects.create(name="Tashkent Lyceum", code="tashkent-1")

    def import_csv(self, content: str):
        return import_student_records(StringIO(content))

    def test_valid_csv_imports_normalized_records(self) -> None:
        result = self.import_csv(
            "lyceum,first_name,last_name,group,external_student_key\n"
            " TASHKENT-1 , Sam , Karimov , 10-B , Student-001 \n"
            "tashkent-1,Ada,Lovelace,11-A,student-002\n"
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.imported, 2)
        self.assertEqual(result.skipped, 0)
        record = StudentRecord.objects.get(external_student_key="student-001")
        self.assertEqual(record.first_name, "Sam")
        self.assertEqual(record.normalized_first_name, "sam")
        self.assertEqual(record.normalized_group_name, "10-b")

    def test_malformed_headers_are_rejected(self) -> None:
        result = self.import_csv(
            "lyceum,first_name,last_name,group_name\n"
            "tashkent-1,Sam,Karimov,10-B\n"
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].row_number, 1)
        self.assertEqual(StudentRecord.objects.count(), 0)

    def test_missing_required_value_aborts_the_import(self) -> None:
        result = self.import_csv(
            "lyceum,first_name,last_name,group\n"
            "tashkent-1,Sam,Karimov,\n"
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].row_number, 2)
        self.assertEqual(StudentRecord.objects.count(), 0)

    def test_duplicate_rows_are_skipped_deterministically(self) -> None:
        result = self.import_csv(
            "lyceum,first_name,last_name,group\n"
            "tashkent-1,Sam,Karimov,10-B\n"
            "TASHKENT-1, sam , KARIMOV , 10-b\n"
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(StudentRecord.objects.count(), 1)

    def test_existing_claimed_records_are_not_overwritten(self) -> None:
        user = User.objects.create_user(telegram_user_id=630_000_001)
        record = StudentRecord.objects.create(
            lyceum=self.lyceum,
            external_student_key="student-claimed",
            first_name="Sam",
            last_name="Karimov",
            group_name="10-B",
            verified_user=user,
            verified_at=timezone.now(),
        )

        result = self.import_csv(
            "lyceum,first_name,last_name,group,external_student_key\n"
            "tashkent-1,Sam,Karimov,10-B,new-key\n"
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].row_number, 2)
        record.refresh_from_db()
        self.assertEqual(record.verified_user, user)
        self.assertEqual(record.external_student_key, "student-claimed")

    def test_row_level_errors_roll_back_other_rows(self) -> None:
        result = self.import_csv(
            "lyceum,first_name,last_name,group\n"
            "tashkent-1,Sam,Karimov,10-B\n"
            "unknown-lyceum,Ada,Lovelace,11-A\n"
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.errors[0].row_number, 3)
        self.assertEqual(StudentRecord.objects.count(), 0)

    def test_management_command_reports_import_counts(self) -> None:
        csv_path: Path
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".csv", delete=False) as csv_file:
            csv_file.write(
                "lyceum,first_name,last_name,group\n"
                "tashkent-1,Sam,Karimov,10-B\n"
            )
            csv_path = Path(csv_file.name)

        try:
            output = StringIO()
            call_command("import_student_records", csv_path, stdout=output)
        finally:
            csv_path.unlink(missing_ok=True)

        self.assertIn("Imported: 1", output.getvalue())
        self.assertIn("Skipped: 0", output.getvalue())
        self.assertIn("Errors: 0", output.getvalue())
        self.assertEqual(StudentRecord.objects.count(), 1)
