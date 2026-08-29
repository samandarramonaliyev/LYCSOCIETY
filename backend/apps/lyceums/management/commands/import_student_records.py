from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.lyceums.services.importing import import_student_records


class Command(BaseCommand):
    help = (
        "Import official student records from a UTF-8 CSV. "
        "This command is for trusted server operators only."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("csv_path", type=Path)

    def handle(self, *args, **options) -> str:  # type: ignore[no-untyped-def]
        csv_path: Path = options["csv_path"]
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                result = import_student_records(csv_file)
        except OSError as exc:
            raise CommandError(f"Could not read CSV file: {exc}") from exc

        for error in result.errors:
            self.stderr.write(f"Row {error.row_number}: {error.message}")

        self.stdout.write(f"Imported: {result.imported}")
        self.stdout.write(f"Skipped: {result.skipped}")
        self.stdout.write(f"Errors: {len(result.errors)}")

        if result.errors:
            raise CommandError("Import aborted; no records were written.")
        return ""
