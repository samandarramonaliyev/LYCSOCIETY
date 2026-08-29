from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import TextIO

from django.db import transaction

from apps.lyceums.models import Lyceum, StudentRecord, normalize_text


REQUIRED_HEADERS = frozenset({"lyceum", "first_name", "last_name", "group"})
OPTIONAL_HEADERS = frozenset({"external_student_key"})


class _LineTrackingIterator:
    """Track physical source-file lines independently of csv.reader error state."""

    def __init__(self, csv_file: TextIO) -> None:
        self._csv_file = csv_file
        self.line_number = 0

    def __iter__(self) -> "_LineTrackingIterator":
        return self

    def __next__(self) -> str:
        line = next(self._csv_file)
        self.line_number += 1
        return line


@dataclass(frozen=True)
class RosterImportError:
    row_number: int
    message: str


@dataclass(frozen=True)
class RosterImportRow:
    row_number: int
    lyceum_code: str
    first_name: str
    last_name: str
    group_name: str
    external_student_key: str | None


@dataclass
class RosterImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[RosterImportError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _clean_value(value: str | None, *, max_length: int) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())[: max_length + 1]


def _validate_headers(reader: csv.DictReader[str]) -> RosterImportResult | None:
    if reader.fieldnames is None:
        return RosterImportResult(errors=[RosterImportError(1, "CSV header row is required.")])

    headers = [header.strip() if header else "" for header in reader.fieldnames]
    if headers:
        headers[0] = headers[0].lstrip("\ufeff")
    reader.fieldnames = headers

    if len(headers) != len(set(headers)):
        return RosterImportResult(errors=[RosterImportError(1, "CSV headers must be unique.")])

    missing_headers = REQUIRED_HEADERS - set(headers)
    unexpected_headers = set(headers) - REQUIRED_HEADERS - OPTIONAL_HEADERS
    if missing_headers or unexpected_headers:
        parts: list[str] = []
        if missing_headers:
            parts.append(f"missing required header(s): {', '.join(sorted(missing_headers))}")
        if unexpected_headers:
            parts.append(f"unexpected header(s): {', '.join(sorted(unexpected_headers))}")
        return RosterImportResult(errors=[RosterImportError(1, "; ".join(parts))])
    return None


def _parse_rows(
    reader: csv.DictReader[str],
    line_tracker: _LineTrackingIterator,
) -> tuple[list[RosterImportRow], RosterImportResult]:
    result = RosterImportResult()
    rows: list[RosterImportRow] = []
    seen_tuples: set[tuple[str, str, str, str]] = set()

    while True:
        row_number = line_tracker.line_number + 1
        try:
            row = next(reader)
        except StopIteration:
            break

        if None in row:
            result.errors.append(RosterImportError(row_number, "row has too many columns"))
            continue

        lyceum = _clean_value(row.get("lyceum"), max_length=50)
        first_name = _clean_value(row.get("first_name"), max_length=128)
        last_name = _clean_value(row.get("last_name"), max_length=128)
        group_name = _clean_value(row.get("group"), max_length=64)
        external_student_key = _clean_value(
            row.get("external_student_key"),
            max_length=128,
        )

        required_values = {
            "lyceum": lyceum,
            "first_name": first_name,
            "last_name": last_name,
            "group": group_name,
        }
        missing_values = [field_name for field_name, value in required_values.items() if not value]
        too_long_values = [
            field_name
            for field_name, value, max_length in (
                ("lyceum", lyceum, 50),
                ("first_name", first_name, 128),
                ("last_name", last_name, 128),
                ("group", group_name, 64),
                ("external_student_key", external_student_key, 128),
            )
            if len(value) > max_length
        ]
        if missing_values or too_long_values:
            parts: list[str] = []
            if missing_values:
                parts.append(f"missing required value(s): {', '.join(missing_values)}")
            if too_long_values:
                parts.append(f"value too long: {', '.join(too_long_values)}")
            result.errors.append(RosterImportError(row_number, "; ".join(parts)))
            continue

        normalized_tuple = (
            normalize_text(lyceum),
            normalize_text(first_name),
            normalize_text(last_name),
            normalize_text(group_name),
        )
        if normalized_tuple in seen_tuples:
            result.skipped += 1
            continue
        seen_tuples.add(normalized_tuple)

        rows.append(
            RosterImportRow(
                row_number=row_number,
                lyceum_code=normalized_tuple[0],
                first_name=first_name,
                last_name=last_name,
                group_name=group_name,
                external_student_key=(normalize_text(external_student_key) if external_student_key else None),
            )
        )

    return rows, result


def import_student_records(csv_file: TextIO) -> RosterImportResult:
    """Validate and atomically import an administrator-supplied official roster CSV."""

    reader: csv.DictReader[str] | None = None
    line_tracker = _LineTrackingIterator(csv_file)
    try:
        reader = csv.DictReader(line_tracker, strict=True)
        header_result = _validate_headers(reader)
        if header_result is not None:
            return header_result

        rows, result = _parse_rows(reader, line_tracker)
    except (csv.Error, UnicodeError) as exc:
        row_number = max(1, line_tracker.line_number)
        return RosterImportResult(
            errors=[RosterImportError(row_number, f"malformed CSV: {exc}")]
        )

    if result.errors:
        return result

    locked_lyceums: dict[str, Lyceum | None] = {}
    with transaction.atomic():
        for row in rows:
            if row.lyceum_code not in locked_lyceums:
                locked_lyceums[row.lyceum_code] = (
                    Lyceum.objects.select_for_update().filter(code=row.lyceum_code).first()
                )
            lyceum = locked_lyceums[row.lyceum_code]
            if lyceum is None:
                result.errors.append(RosterImportError(row.row_number, "unknown lyceum code"))
                continue

            matching_records = list(
                StudentRecord.objects.select_for_update().filter(
                    lyceum=lyceum,
                    normalized_first_name=normalize_text(row.first_name),
                    normalized_last_name=normalize_text(row.last_name),
                    normalized_group_name=normalize_text(row.group_name),
                )
            )
            records_by_external_key = []
            if row.external_student_key:
                records_by_external_key = list(
                    StudentRecord.objects.select_for_update().filter(
                        lyceum=lyceum,
                        external_student_key=row.external_student_key,
                    )
                )

            if records_by_external_key:
                existing_record = records_by_external_key[0]
                if existing_record in matching_records:
                    result.skipped += 1
                else:
                    result.errors.append(
                        RosterImportError(
                            row.row_number,
                            "external_student_key conflicts with an existing record",
                        )
                    )
                continue

            if matching_records:
                if row.external_student_key:
                    result.errors.append(
                        RosterImportError(
                            row.row_number,
                            "matching record already exists with another external_student_key",
                        )
                    )
                else:
                    result.skipped += 1
                continue

            StudentRecord.objects.create(
                lyceum=lyceum,
                external_student_key=row.external_student_key,
                first_name=row.first_name,
                last_name=row.last_name,
                group_name=row.group_name,
            )
            result.imported += 1

        if result.errors:
            transaction.set_rollback(True)
            result.imported = 0

    return result
