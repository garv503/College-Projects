"""Cohort-level analytics for staff.

Per-student analytics live in routes/students.py. This blueprint answers
questions about *groups* - which subjects are failing people, how marks
are distributed, who needs attention first.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from security import require_role
from services import analytics
from validators import query_int

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.get("/cohort")
@require_role("admin", "faculty")
def cohort_summary():
    """Headline numbers for a branch/semester, or the whole college."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    return jsonify(analytics.get_cohort_summary(branch_id, semester))


@bp.get("/at-risk")
@require_role("admin", "faculty")
def at_risk():
    """Students needing intervention, highest risk score first."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    limit = query_int("limit", 50, minimum=1, maximum=200)

    # The service attaches the written `reasons` and `recommendations`
    # alongside each score - the "why" is what makes the list actionable
    # rather than merely ordered.
    students = analytics.get_at_risk_students(branch_id, semester, limit)
    return jsonify({"students": students, "count": len(students)})


@bp.get("/grade-distribution")
@require_role("admin", "faculty")
def grade_distribution():
    """How many students sit in each grade band."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    return jsonify(analytics.get_grade_distribution(branch_id, semester))


@bp.get("/subjects")
@require_role("admin", "faculty")
def subject_statistics():
    """Per-subject averages and pass rates, weakest first."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    return jsonify(analytics.get_subject_statistics(branch_id, semester))
