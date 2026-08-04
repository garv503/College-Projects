"""Student-facing routes: dashboard data and report cards.

Every route here that names a student calls `require_self_or_staff`.
That single line is the fix for the original project's most serious flaw:
`GET /student-data/<id>` had no check at all, so any logged-in student
could read any other student's marks by changing the number in the URL.
"""

from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

import db
from errors import not_found
from security import require_auth, require_role, require_self_or_staff
from services import analytics, reports
from validators import pagination, query_int, sort_column

bp = Blueprint("students", __name__, url_prefix="/api/students")


@bp.get("/me")
@require_auth
def my_dashboard():
    """The signed-in student's own dashboard.

    Exists so the front end never has to put a student id in a URL: the
    id comes from the signed token, which the browser cannot forge.
    """
    student_id = g.user.get("student_id")
    if not student_id:
        raise not_found(
            "This account is not linked to a student record. "
            "Staff accounts should use the admin console."
        )

    data = analytics.build_student_analytics(student_id)
    if not data:
        raise not_found("No academic records found for your account yet")
    return jsonify(data)


@bp.get("/<int:student_id>")
@require_auth
def student_dashboard(student_id: int):
    """Full analytics for one student. Staff, or that student."""
    require_self_or_staff(student_id)

    data = analytics.build_student_analytics(student_id)
    if not data:
        raise not_found(f"Student {student_id} has no academic records")
    return jsonify(data)


@bp.get("/<int:student_id>/subjects")
@require_auth
def student_subjects(student_id: int):
    """Per-subject marks and attendance."""
    require_self_or_staff(student_id)
    return jsonify(analytics.get_subject_breakdown(student_id))


@bp.get("/<int:student_id>/timeline")
@require_auth
def student_timeline(student_id: int):
    """Every assessment, oldest first - the data behind the trend chart."""
    require_self_or_staff(student_id)
    timeline = analytics.get_assessment_timeline(student_id)
    return jsonify(
        {
            "timeline": timeline,
            "trend": analytics.compute_trend(
                [float(a["percent"]) for a in timeline if a["percent"] is not None]
            ),
        }
    )


@bp.get("/<int:student_id>/comparison")
@require_auth
def student_comparison(student_id: int):
    """This student's marks against the class average, per subject."""
    require_self_or_staff(student_id)
    return jsonify(analytics.get_cohort_comparison(student_id))


@bp.get("/<int:student_id>/report-card")
@require_auth
def report_card(student_id: int):
    """Report card as JSON, including grades and GPA."""
    require_self_or_staff(student_id)
    card = reports.build_report_card(student_id)
    if not card:
        raise not_found(f"Student {student_id} has no records to report on")
    return jsonify(card)


@bp.get("/<int:student_id>/report-card.csv")
@require_auth
def report_card_download(student_id: int):
    """Report card as a downloadable CSV file."""
    require_self_or_staff(student_id)
    result = reports.report_card_csv(student_id)
    if not result:
        raise not_found(f"Student {student_id} has no records to report on")

    filename, body = result
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.get("")
@require_role("admin", "faculty")
def list_students():
    """Searchable, sortable, paginated student list for staff.

    The original project had no way to list students at all - the admin
    could add one and then never see it again.
    """
    page, per_page, offset = pagination()
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    search = request.args.get("q", "").strip()
    risk_band = request.args.get("risk", "").strip().lower() or None

    # Sorting has to be interpolated into the SQL because a column name
    # cannot be a bound parameter - so the value is resolved through this
    # whitelist and the raw query string is never used.
    order_by = sort_column(
        {
            "name": "a.student_name",
            "roll_no": "a.roll_no",
            "marks": "a.avg_mark_percent",
            "attendance": "a.avg_attendance_percent",
            "rank": "a.class_rank",
            "risk": "a.risk_score",
            "semester": "a.semester",
            # NULL sorts first ascending in MySQL, which is what you want
            # here: "never signed in" is the interesting end of this list.
            "last_seen": "u.last_login_at",
        },
        default="roll_no",
    )

    # `LIKE %s` with the wildcards inside the *parameter* keeps this
    # injection-safe; the % characters are data, not SQL.
    like = f"%{search}%" if search else None

    where = """
        WHERE (%s IS NULL OR b.branch_id = %s)
          AND (%s IS NULL OR a.semester = %s)
          AND (%s IS NULL OR a.student_name LIKE %s OR a.roll_no LIKE %s)
          AND (%s IS NULL OR a.risk_band = %s)
    """
    params = (
        branch_id,
        branch_id,
        semester,
        semester,
        like,
        like,
        like,
        risk_band,
        risk_band,
    )

    # The users join is a LEFT join on purpose: a student row without a
    # login account still has to appear in this list, with a NULL last
    # sign-in rather than vanishing from the results entirely.
    from_clause = """
        FROM v_at_risk_students a
        LEFT JOIN branches b ON b.code = a.branch_code
        LEFT JOIN users u ON u.student_id = a.student_id
    """

    total = db.query_value(
        f"""
        SELECT COUNT(*)
        {from_clause}
        {where}
        """,
        params,
        default=0,
    )

    rows = db.query_all(
        f"""
        SELECT a.student_id, a.student_name, a.roll_no, a.branch_code,
               a.semester, a.avg_mark_percent, a.avg_attendance_percent,
               a.backlog_count, a.class_rank, a.cohort_size, a.percentile,
               a.risk_score, a.risk_band,
               u.last_login_at
        {from_clause}
        {where}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
        """,
        params + (per_page, offset),
    )

    return jsonify(
        {
            "students": rows,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if total else 0,
            },
        }
    )
