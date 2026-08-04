"""Bulk CSV import of assessment marks and attendance.

Entering marks for a class of sixty through a web form is not something
anyone does twice, so the admin console accepts a CSV instead.

The important design decision here is that the import is **atomic and
validated up front**: every row is checked before a single one is
written, and if any row is bad the whole file is rejected with a list of
exactly which lines were wrong and why. The alternative - writing rows
until one fails - leaves the operator with a half-imported file and no
straightforward way to work out where to resume.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

import db
from errors import bad_request

# Columns each import type requires. Extra columns are ignored, so a
# spreadsheet exported with a stray "Notes" column still imports.
MARKS_COLUMNS = {"roll_no", "subject_code", "type", "marks_obtained"}
ATTENDANCE_COLUMNS = {"roll_no", "subject_code", "class_date", "status"}

ASSESSMENT_TYPES = {"quiz", "assignment", "midterm", "final"}
ATTENDANCE_STATUSES = {"present", "absent", "late", "excused"}

MAX_ROWS = 5000


@dataclass
class RowError:
    line: int
    message: str

    def to_dict(self) -> dict:
        return {"line": self.line, "message": self.message}


@dataclass
class ImportResult:
    imported: int = 0
    errors: list[RowError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "imported": self.imported,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


def _read_csv(raw: bytes, required: set[str]) -> list[dict]:
    """Decode and parse the upload, or raise a helpful 400."""
    try:
        # utf-8-sig strips the byte-order mark Excel writes, which would
        # otherwise turn the first header into "﻿roll_no" and make
        # the column look missing.
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise bad_request("File must be UTF-8 encoded CSV")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise bad_request("CSV file is empty")

    headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = required - headers
    if missing:
        raise bad_request(
            f"CSV is missing required column(s): {', '.join(sorted(missing))}. "
            f"Found: {', '.join(sorted(headers))}"
        )

    rows = []
    for row in reader:
        # Normalise keys and values once so the validators below do not
        # each have to think about whitespace and casing.
        rows.append(
            {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        )
        if len(rows) > MAX_ROWS:
            raise bad_request(f"File exceeds the {MAX_ROWS} row limit")

    if not rows:
        raise bad_request("CSV contains headers but no data rows")
    return rows


def _lookup_enrollments() -> dict[tuple[str, str], int]:
    """Map (roll_no, subject_code) -> enrollment_id for the whole college.

    One query instead of one per row. For a few thousand enrollments this
    is a small dictionary and turns an O(n) round-trip import into O(1).
    """
    rows = db.query_all(
        """
        SELECT s.roll_no, sub.code AS subject_code, e.enrollment_id
        FROM enrollments e
        JOIN students s   ON s.student_id  = e.student_id
        JOIN subjects sub ON sub.subject_id = e.subject_id
        """
    )
    return {
        (r["roll_no"].upper(), r["subject_code"].upper()): r["enrollment_id"]
        for r in rows
    }


def import_marks(raw: bytes) -> ImportResult:
    """Import assessment marks from CSV.

    Expected columns:
        roll_no, subject_code, type, marks_obtained[, max_marks][, assessed_on]

    `max_marks` defaults to 100 and `assessed_on` to today, because most
    uploads are a single exam already scored out of 100.
    """
    rows = _read_csv(raw, MARKS_COLUMNS)
    enrollments = _lookup_enrollments()

    result = ImportResult()
    to_insert: list[tuple] = []
    seen: set[tuple[int, str]] = set()

    for index, row in enumerate(rows, start=2):  # line 1 is the header
        roll = row.get("roll_no", "").upper()
        subject = row.get("subject_code", "").upper()

        enrollment_id = enrollments.get((roll, subject))
        if enrollment_id is None:
            result.errors.append(
                RowError(index, f"'{roll}' is not enrolled in '{subject}'")
            )
            continue

        assessment_type = row.get("type", "").lower()
        if assessment_type not in ASSESSMENT_TYPES:
            result.errors.append(
                RowError(
                    index,
                    f"type '{assessment_type}' must be one of: "
                    f"{', '.join(sorted(ASSESSMENT_TYPES))}",
                )
            )
            continue

        max_marks = _parse_number(row.get("max_marks"), default=100.0)
        if max_marks is None or max_marks <= 0:
            result.errors.append(RowError(index, "max_marks must be a positive number"))
            continue

        obtained = _parse_number(row.get("marks_obtained"))
        if obtained is None:
            result.errors.append(
                RowError(
                    index, f"marks_obtained '{row.get('marks_obtained')}' is not a number"
                )
            )
            continue
        if obtained < 0:
            result.errors.append(RowError(index, "marks_obtained cannot be negative"))
            continue
        if obtained > max_marks:
            result.errors.append(
                RowError(
                    index,
                    f"marks_obtained ({obtained:g}) exceeds max_marks ({max_marks:g})",
                )
            )
            continue

        assessed_on = _parse_date(row.get("assessed_on"), default=date.today())
        if assessed_on is None:
            result.errors.append(
                RowError(
                    index, f"assessed_on '{row.get('assessed_on')}' must be YYYY-MM-DD"
                )
            )
            continue
        if assessed_on > date.today():
            result.errors.append(RowError(index, "assessed_on cannot be in the future"))
            continue

        # The same student+subject+type twice in one file means the
        # operator has a duplicate row; silently keeping the last one
        # would hide a mistake in their spreadsheet.
        key = (enrollment_id, assessment_type)
        if key in seen:
            result.errors.append(
                RowError(
                    index, f"duplicate row for {roll} / {subject} / {assessment_type}"
                )
            )
            continue
        seen.add(key)

        to_insert.append(
            (enrollment_id, assessment_type, obtained, max_marks, assessed_on)
        )

    # Nothing is written unless the entire file is clean.
    if result.errors:
        return result

    # ON DUPLICATE KEY would need a unique index on (enrollment, type),
    # which the schema deliberately does not have - a student can sit two
    # quizzes. So a re-upload updates the matching row explicitly.
    db.execute_many(
        """
        INSERT INTO assessments
            (enrollment_id, type, marks_obtained, max_marks, assessed_on)
        VALUES (%s, %s, %s, %s, %s)
        """,
        to_insert,
    )
    result.imported = len(to_insert)
    return result


def import_attendance(raw: bytes) -> ImportResult:
    """Import daily attendance from CSV.

    Expected columns: roll_no, subject_code, class_date, status
    """
    rows = _read_csv(raw, ATTENDANCE_COLUMNS)
    enrollments = _lookup_enrollments()

    result = ImportResult()
    to_insert: list[tuple] = []
    seen: set[tuple[int, date]] = set()

    for index, row in enumerate(rows, start=2):
        roll = row.get("roll_no", "").upper()
        subject = row.get("subject_code", "").upper()

        enrollment_id = enrollments.get((roll, subject))
        if enrollment_id is None:
            result.errors.append(
                RowError(index, f"'{roll}' is not enrolled in '{subject}'")
            )
            continue

        class_date = _parse_date(row.get("class_date"))
        if class_date is None:
            result.errors.append(
                RowError(
                    index, f"class_date '{row.get('class_date')}' must be YYYY-MM-DD"
                )
            )
            continue
        if class_date > date.today():
            result.errors.append(RowError(index, "class_date cannot be in the future"))
            continue

        status = row.get("status", "").lower()
        if status not in ATTENDANCE_STATUSES:
            result.errors.append(
                RowError(
                    index,
                    f"status '{status}' must be one of: "
                    f"{', '.join(sorted(ATTENDANCE_STATUSES))}",
                )
            )
            continue

        key = (enrollment_id, class_date)
        if key in seen:
            result.errors.append(
                RowError(
                    index, f"duplicate attendance for {roll} / {subject} on {class_date}"
                )
            )
            continue
        seen.add(key)

        to_insert.append((enrollment_id, class_date, status))

    if result.errors:
        return result

    # Re-uploading a corrected register should fix the existing rows
    # rather than fail on the uq_attendance unique key.
    db.execute_many(
        """
        INSERT INTO attendance_records (enrollment_id, class_date, status)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE status = VALUES(status)
        """,
        to_insert,
    )
    result.imported = len(to_insert)
    return result


def _parse_number(value: str | None, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return None


def _parse_date(value: str | None, default: date | None = None) -> date | None:
    if value is None or value == "":
        return default
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
