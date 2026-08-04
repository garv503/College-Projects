"""Report card generation and CSV export.

Two output formats from one source of truth:

  * `build_report_card()` returns structured data for the web UI;
  * the `*_csv` helpers stream the same numbers as a downloadable file.

The per-subject rows, grades and GPA all come from the
`sp_student_report_card` stored procedure, so the printed report card and
the on-screen dashboard cannot drift apart.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

import db


def build_report_card(student_id: int) -> dict | None:
    """Return one student's full report card.

    sp_student_report_card returns two result sets - the subject rows and
    a one-row summary - which is why this reads `results[0]` and
    `results[1]` rather than a single list.
    """
    results = db.call_proc("sp_student_report_card", (student_id,))
    if len(results) < 2 or not results[1]:
        return None

    subjects = [_floatify(r) for r in results[0]]
    summary = _floatify(results[1][0])

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "student": {
            "student_id": student_id,
            "name": summary.get("student_name"),
            "roll_no": summary.get("roll_no"),
            "branch": summary.get("branch_code"),
            "semester": summary.get("semester"),
        },
        "summary": {
            "subject_count": summary.get("subject_count"),
            "average_marks": summary.get("avg_mark_percent"),
            "average_attendance": summary.get("avg_attendance_percent"),
            "backlog_count": summary.get("backlog_count"),
            "class_rank": summary.get("class_rank"),
            "cohort_size": summary.get("cohort_size"),
            "percentile": summary.get("percentile"),
            "overall_grade": summary.get("overall_grade"),
            "gpa": summary.get("gpa"),
        },
        "subjects": subjects,
    }


def report_card_csv(student_id: int) -> tuple[str, str] | None:
    """Render a report card as CSV. Returns (filename, csv_text)."""
    card = build_report_card(student_id)
    if not card:
        return None

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    student = card["student"]
    summary = card["summary"]

    writer.writerow(["Foresight - Report Card"])
    writer.writerow(["Generated", card["generated_at"]])
    writer.writerow([])
    writer.writerow(["Name", student["name"]])
    writer.writerow(["Roll No", student["roll_no"]])
    writer.writerow(["Branch", student["branch"]])
    writer.writerow(["Semester", student["semester"]])
    writer.writerow([])

    writer.writerow(
        [
            "Subject Code",
            "Subject",
            "Credits",
            "Marks %",
            "Attendance %",
            "Grade",
            "Grade Point",
            "Result",
        ]
    )
    for row in card["subjects"]:
        writer.writerow(
            [
                row.get("subject_code"),
                row.get("subject_name"),
                row.get("credits"),
                _fmt(row.get("mark_percent")),
                _fmt(row.get("attendance_percent")),
                row.get("grade"),
                _fmt(row.get("grade_point")),
                row.get("result"),
            ]
        )

    writer.writerow([])
    writer.writerow(["Average Marks %", _fmt(summary["average_marks"])])
    writer.writerow(["Average Attendance %", _fmt(summary["average_attendance"])])
    writer.writerow(["GPA", _fmt(summary["gpa"])])
    writer.writerow(["Overall Grade", summary["overall_grade"]])
    writer.writerow(
        ["Class Rank", f"{summary['class_rank']} of {summary['cohort_size']}"]
    )
    writer.writerow(["Backlogs", summary["backlog_count"]])

    roll = (student["roll_no"] or str(student_id)).replace("/", "-")
    return f"report-card-{roll}.csv", buffer.getvalue()


def cohort_csv(branch_id: int | None, semester: int | None) -> tuple[str, str]:
    """Export a whole cohort's summary as CSV, for the admin console."""
    rows = db.query_all(
        """
        SELECT roll_no, student_name, branch_code, semester,
               subject_count, avg_mark_percent, avg_attendance_percent,
               backlog_count, class_rank, cohort_size, percentile,
               risk_score, risk_band
        FROM v_at_risk_students a
        LEFT JOIN branches b ON b.code = a.branch_code
        WHERE (%s IS NULL OR b.branch_id = %s)
          AND (%s IS NULL OR a.semester = %s)
        ORDER BY a.semester, a.class_rank
        """,
        (branch_id, branch_id, semester, semester),
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Roll No",
            "Name",
            "Branch",
            "Semester",
            "Subjects",
            "Avg Marks %",
            "Avg Attendance %",
            "Backlogs",
            "Rank",
            "Cohort Size",
            "Percentile",
            "Risk Score",
            "Risk Band",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["roll_no"],
                r["student_name"],
                r["branch_code"],
                r["semester"],
                r["subject_count"],
                _fmt(r["avg_mark_percent"]),
                _fmt(r["avg_attendance_percent"]),
                r["backlog_count"],
                r["class_rank"],
                r["cohort_size"],
                _fmt(r["percentile"]),
                _fmt(r["risk_score"]),
                r["risk_band"],
            ]
        )

    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"cohort-export-{stamp}.csv", buffer.getvalue()


def marks_template_csv() -> tuple[str, str]:
    """A ready-to-fill CSV template for the bulk marks importer.

    Pre-populated with the caller's actual roll numbers and subject codes,
    so the operator does not have to guess the format or retype the keys.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["roll_no", "subject_code", "type", "marks_obtained", "max_marks", "assessed_on"]
    )

    examples = db.query_all(
        """
        SELECT s.roll_no, sub.code AS subject_code
        FROM enrollments e
        JOIN students s   ON s.student_id  = e.student_id
        JOIN subjects sub ON sub.subject_id = e.subject_id
        ORDER BY s.roll_no, sub.code
        LIMIT 5
        """
    )
    today = datetime.now(UTC).date().isoformat()
    for row in examples:
        writer.writerow([row["roll_no"], row["subject_code"], "midterm", "", "50", today])

    if not examples:
        writer.writerow(["CSE2023001", "CS301", "midterm", "42", "50", today])

    return "marks-template.csv", buffer.getvalue()


def _floatify(row: dict) -> dict:
    """Convert MySQL DECIMAL values to floats so jsonify can handle them.

    Dates and datetimes are deliberately left alone. Formatting them here
    would produce a plain string, and the JSON provider only stamps the
    UTC offset on real datetime objects - a string passes through it
    untouched, arriving at the browser as an unlabelled local time.
    """
    return {
        key: float(value) if hasattr(value, "quantize") else value
        for key, value in row.items()
    }


def _fmt(value) -> str:
    """Format a number for CSV, leaving blanks rather than 'None'."""
    if value is None:
        return ""
    return f"{float(value):.2f}"
