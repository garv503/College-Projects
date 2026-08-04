"""Reference data: branches and subjects.

Read-only lookups the front end needs to render its dropdowns. Kept
separate from admin.py because these are the only endpoints a signed-in
student is allowed to read, and mixing them into the admin blueprint
would mean weakening that blueprint's role check.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

import db
from errors import not_found
from security import require_auth
from validators import query_int

bp = Blueprint("catalog", __name__, url_prefix="/api")


@bp.get("/branches")
@require_auth
def list_branches():
    """All branches, with a live count of active students in each."""
    return jsonify(
        db.query_all(
            """
            SELECT b.branch_id, b.code, b.name,
                   COUNT(s.student_id) AS student_count
            FROM branches b
            LEFT JOIN students s
                   ON s.branch_id = b.branch_id AND s.is_active = TRUE
            GROUP BY b.branch_id, b.code, b.name
            ORDER BY b.code
            """
        )
    )


@bp.get("/subjects")
@require_auth
def list_subjects():
    """Subjects, optionally filtered by ?branch_id= and ?semester=."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None

    return jsonify(
        db.query_all(
            """
            SELECT s.subject_id, s.code, s.name, s.credits, s.pass_mark,
                   s.semester, b.code AS branch_code, b.branch_id
            FROM subjects s
            JOIN branches b ON b.branch_id = s.branch_id
            WHERE (%s IS NULL OR s.branch_id = %s)
              AND (%s IS NULL OR s.semester  = %s)
            ORDER BY s.semester, s.code
            """,
            (branch_id, branch_id, semester, semester),
        )
    )


@bp.get("/subjects/<int:subject_id>/stats")
@require_auth
def subject_stats(subject_id: int):
    """Class-level statistics for one subject."""
    row = db.query_one(
        """
        SELECT subject_id, subject_code, subject_name, branch_code, semester,
               enrolled_count, avg_mark_percent, min_mark_percent,
               max_mark_percent, stddev_mark_percent, avg_attendance_percent,
               passed_count, failed_count, pass_rate
        FROM v_subject_stats
        WHERE subject_id = %s
        """,
        (subject_id,),
    )
    if not row:
        raise not_found(f"No statistics for subject {subject_id}")
    return jsonify(row)
