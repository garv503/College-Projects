"""Academic analytics: risk scoring, trends and cohort statistics.

The original project's entire analysis was:

    status = "Good"
    if avg_marks < 40 or avg_attendance < 60:
        status = "Weak"

Three things are wrong with that. It crashes with a TypeError when a
student has no marks yet (AVG of nothing is NULL). It is a cliff, so
39.9% with three failed subjects is indistinguishable from 39.9% with
none. And it tells a student they are "Weak" without saying why or what
to do about it.

What replaces it:

  * a 0-100 risk score built from four weighted signals, so students can
    be *ranked* by how much attention they need;
  * a written reason for every point of that score;
  * a trend direction, because a student at 45% climbing is in a very
    different situation from one at 45% falling.

The weights below intentionally mirror `v_at_risk_students` in
database/views.sql. SQL does the set-based scoring for lists of students;
this module explains a single student. If you change a weight, change it
in both places - test_analytics.py asserts they agree.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import db
from config import config

# --- Scoring weights (must match database/views.sql) ------------------
WEIGHT_MARKS = 40  # maximum points contributed by low marks
WEIGHT_ATTENDANCE = 30  # maximum points contributed by poor attendance
WEIGHT_PER_BACKLOG = 10  # points per failed subject...
WEIGHT_BACKLOG_CAP = 20  # ...but capped here
WEIGHT_PERCENTILE = 10  # points for sitting in the bottom quartile

# A trend needs at least this many assessments before it means anything.
MIN_ASSESSMENTS_FOR_TREND = 3
# Percentage-point change below which a trend counts as flat.
TREND_FLAT_THRESHOLD = 3.0


@dataclass
class RiskAssessment:
    """The full explanation of one student's risk score."""

    score: float
    band: str
    reasons: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "band": self.band,
            "reasons": self.reasons,
            "recommendations": self.recommendations,
        }


def assess_risk(
    avg_marks: float | None,
    avg_attendance: float | None,
    backlog_count: int,
    percentile: float | None = None,
) -> RiskAssessment:
    """Score a student 0-100 and explain the score.

    Pure function - no database access - so the test suite can check the
    scoring rules directly with plain numbers.

    A student with no marks recorded scores 0 and lands in the 'unknown'
    band rather than looking like a top performer, which is what a plain
    "average is null, treat as zero" would have produced.
    """
    if avg_marks is None:
        return RiskAssessment(
            score=0.0,
            band="unknown",
            reasons=["No marks have been recorded yet"],
            recommendations=["Ask the department to upload assessment marks"],
        )

    score = 0.0
    reasons: list[str] = []
    recommendations: list[str] = []

    # --- Signal 1: marks below the pass mark --------------------------
    pass_mark = config.pass_percent
    if avg_marks < pass_mark:
        shortfall = (pass_mark - avg_marks) / pass_mark
        points = shortfall * WEIGHT_MARKS
        score += points
        reasons.append(f"Average of {avg_marks:.1f}% is below the {pass_mark}% pass mark")
        recommendations.append("Book remedial sessions for the lowest-scoring subjects")

    # --- Signal 2: attendance below the requirement -------------------
    min_attendance = config.min_attendance_percent
    if avg_attendance is not None and avg_attendance < min_attendance:
        shortfall = (min_attendance - avg_attendance) / min_attendance
        points = shortfall * WEIGHT_ATTENDANCE
        score += points
        reasons.append(
            f"Attendance of {avg_attendance:.1f}% is below the "
            f"{min_attendance}% requirement"
        )
        # Below 60% is usually an exam-eligibility problem, not just a
        # warning, so the advice escalates.
        if avg_attendance < 60:
            recommendations.append(
                "Attendance is low enough to risk exam ineligibility - "
                "escalate to the mentor"
            )
        else:
            recommendations.append("Attend all remaining classes this term")

    # --- Signal 3: backlogs -------------------------------------------
    if backlog_count > 0:
        points = min(WEIGHT_BACKLOG_CAP, backlog_count * WEIGHT_PER_BACKLOG)
        score += points
        subject_word = "subject" if backlog_count == 1 else "subjects"
        reasons.append(f"Failing {backlog_count} {subject_word}")
        recommendations.append(
            f"Register for re-assessment in {backlog_count} {subject_word}"
        )

    # --- Signal 4: standing against peers -----------------------------
    if percentile is not None and percentile < 25:
        score += WEIGHT_PERCENTILE
        reasons.append(
            f"In the bottom quartile of the class (percentile {percentile:.0f})"
        )

    score = max(0.0, min(100.0, score))

    # The band is a separate judgement from the score, matching the CASE
    # expression in v_at_risk_students, so the two never disagree.
    if (
        avg_marks < 40
        or (avg_attendance is not None and avg_attendance < 60)
        or backlog_count >= 2
    ):
        band = "high"
    elif (
        avg_marks < 55
        or (avg_attendance is not None and avg_attendance < 75)
        or backlog_count == 1
    ):
        band = "medium"
    else:
        band = "low"

    # The band uses a *warning* threshold (55%) while the score only
    # starts accumulating at the *failing* threshold (40%). A student
    # sitting between the two therefore lands in the medium band having
    # triggered none of the scoring signals - and without this branch
    # would be told "medium risk" and "meeting all requirements" in the
    # same breath. Naming the margin is the honest thing to report.
    if not reasons and band == "medium":
        if avg_marks < 55:
            reasons.append(
                f"Average of {avg_marks:.1f}% is passing, but the margin "
                "above the 40% pass mark is thin"
            )
            recommendations.append("Aim for 55%+ to build a safety margin before finals")
        elif avg_attendance is not None and avg_attendance < 75:
            reasons.append(
                f"Attendance of {avg_attendance:.1f}% is just under the "
                f"{min_attendance}% requirement"
            )
            recommendations.append("Attend all remaining classes this term")

    if not reasons:
        reasons.append("Meeting all academic requirements")
        recommendations.append("Keep it up - consider stretch coursework")

    return RiskAssessment(score, band, reasons, recommendations)


def compute_trend(percentages: list[float]) -> dict:
    """Describe whether a run of assessment percentages is improving.

    Compares the mean of the first half against the mean of the second
    half. That is deliberately simpler than fitting a regression line: it
    is resistant to a single bad paper, and - more importantly for a
    project you have to explain - it is obvious what it does.
    """
    if len(percentages) < MIN_ASSESSMENTS_FOR_TREND:
        return {
            "direction": "insufficient_data",
            "change": 0.0,
            "message": (
                f"Need at least {MIN_ASSESSMENTS_FOR_TREND} assessments "
                "to detect a trend"
            ),
        }

    midpoint = len(percentages) // 2
    earlier = percentages[:midpoint]
    later = percentages[midpoint:]

    earlier_avg = sum(earlier) / len(earlier)
    later_avg = sum(later) / len(later)
    change = later_avg - earlier_avg

    if change > TREND_FLAT_THRESHOLD:
        direction = "improving"
        message = f"Up {change:.1f} points versus earlier assessments"
    elif change < -TREND_FLAT_THRESHOLD:
        direction = "declining"
        message = f"Down {abs(change):.1f} points versus earlier assessments"
    else:
        direction = "stable"
        message = "Performance is holding steady"

    return {
        "direction": direction,
        "change": round(change, 1),
        "earlier_average": round(earlier_avg, 1),
        "later_average": round(later_avg, 1),
        "message": message,
    }


# ---------------------------------------------------------------------
# Database-backed queries
# ---------------------------------------------------------------------


def get_student_overview(student_id: int) -> dict | None:
    """Headline numbers for one student, straight from v_student_rank."""
    return db.query_one(
        """
        SELECT student_id, student_name, roll_no, branch_code, semester,
               subject_count, avg_mark_percent, avg_attendance_percent,
               backlog_count, lowest_subject_percent, highest_subject_percent,
               class_rank, cohort_size, percentile
        FROM v_student_rank
        WHERE student_id = %s
        """,
        (student_id,),
    )


def get_subject_breakdown(student_id: int) -> list[dict]:
    """Per-subject marks and attendance for one student."""
    return db.query_all(
        """
        SELECT subject_id, subject_code, subject_name, credits, pass_mark,
               assessment_count, mark_percent, attendance_percent,
               total_classes, attended_classes,
               CASE WHEN mark_percent IS NULL          THEN 'pending'
                    WHEN mark_percent >= pass_mark     THEN 'pass'
                    ELSE 'fail' END AS result
        FROM v_enrollment_summary
        WHERE student_id = %s
        ORDER BY subject_code
        """,
        (student_id,),
    )


def get_assessment_timeline(student_id: int) -> list[dict]:
    """Every assessment for a student, oldest first, as percentages."""
    return db.query_all(
        """
        SELECT subject_code, subject_name, type, assessed_on,
               marks_obtained, max_marks, percent
        FROM v_assessment_trend
        WHERE student_id = %s
        ORDER BY assessed_on, subject_code
        """,
        (student_id,),
    )


def get_cohort_comparison(student_id: int) -> list[dict]:
    """This student's per-subject marks next to the class average.

    Answers the question a bare number cannot: 52% sounds poor, but if
    the class average is 48% the student is actually above the line.
    """
    return db.query_all(
        """
        SELECT v.subject_code,
               v.subject_name,
               v.mark_percent                AS student_percent,
               s.avg_mark_percent            AS class_average,
               s.max_mark_percent            AS class_best,
               ROUND(v.mark_percent - s.avg_mark_percent, 2) AS difference
        FROM v_enrollment_summary v
        JOIN v_subject_stats s ON s.subject_id = v.subject_id
        WHERE v.student_id = %s
        ORDER BY v.subject_code
        """,
        (student_id,),
    )


def get_at_risk_students(
    branch_id: int | None = None,
    semester: int | None = None,
    limit: int = 50,
    explain: bool = True,
) -> list[dict]:
    """Students needing attention, worst first.

    The branch/semester filters are optional; passing NULL for either
    means "all", which is handled in SQL so this stays a single query.

    With `explain` (the default) each row also carries the written
    `reasons` and `recommendations` behind its score. That lives here
    rather than in a route because more than one endpoint needs it, and
    the first version - which attached the reasons in the route - left
    the admin dashboard showing a "Why" column full of dashes.
    """
    students = db.query_all(
        """
        SELECT a.student_id, a.student_name, a.roll_no, a.branch_code,
               a.semester, a.avg_mark_percent, a.avg_attendance_percent,
               a.backlog_count, a.class_rank, a.cohort_size, a.percentile,
               a.risk_score, a.risk_band
        FROM v_at_risk_students a
        LEFT JOIN branches b ON b.code = a.branch_code
        WHERE a.risk_band IN ('high', 'medium')
          AND (%s IS NULL OR b.branch_id = %s)
          AND (%s IS NULL OR a.semester = %s)
        ORDER BY a.risk_score DESC, a.avg_mark_percent ASC
        LIMIT %s
        """,
        (branch_id, branch_id, semester, semester, limit),
    )

    if explain:
        for student in students:
            assessment = assess_risk(
                avg_marks=_as_float(student.get("avg_mark_percent")),
                avg_attendance=_as_float(student.get("avg_attendance_percent")),
                backlog_count=int(student.get("backlog_count") or 0),
                percentile=_as_float(student.get("percentile")),
            )
            student["reasons"] = assessment.reasons
            student["recommendations"] = assessment.recommendations

    return students


def get_cohort_summary(branch_id: int | None = None, semester: int | None = None) -> dict:
    """Headline cohort numbers, via the sp_cohort_summary procedure."""
    results = db.call_proc("sp_cohort_summary", (branch_id, semester))
    if results and results[0]:
        return results[0][0]
    return {}


def get_grade_distribution(
    branch_id: int | None = None, semester: int | None = None
) -> list[dict]:
    """How many students fall in each grade band.

    Bucketed in SQL with a CASE rather than fetched and counted in
    Python, because the whole point is to avoid pulling every row over
    the wire just to produce seven numbers.
    """
    rows = db.query_all(
        """
        SELECT CASE
                   WHEN avg_mark_percent >= 90 THEN 'A+'
                   WHEN avg_mark_percent >= 80 THEN 'A'
                   WHEN avg_mark_percent >= 70 THEN 'B'
                   WHEN avg_mark_percent >= 60 THEN 'C'
                   WHEN avg_mark_percent >= 50 THEN 'D'
                   WHEN avg_mark_percent >= 40 THEN 'E'
                   ELSE 'F'
               END AS grade,
               COUNT(*) AS student_count
        FROM v_student_overall o
        LEFT JOIN branches b ON b.branch_id = o.branch_id
        WHERE o.avg_mark_percent IS NOT NULL
          AND (%s IS NULL OR o.branch_id = %s)
          AND (%s IS NULL OR o.semester = %s)
        GROUP BY grade
        """,
        (branch_id, branch_id, semester, semester),
    )

    # Guarantee every band is present, in order, so the chart's x-axis is
    # stable even when no student earned a particular grade.
    counts = {r["grade"]: r["student_count"] for r in rows}
    return [
        {"grade": g, "student_count": counts.get(g, 0)}
        for g in ("A+", "A", "B", "C", "D", "E", "F")
    ]


def get_subject_statistics(
    branch_id: int | None = None, semester: int | None = None
) -> list[dict]:
    """Per-subject pass rates and averages, weakest subject first."""
    return db.query_all(
        """
        SELECT subject_id, subject_code, subject_name, branch_code, semester,
               enrolled_count, avg_mark_percent, min_mark_percent,
               max_mark_percent, stddev_mark_percent, avg_attendance_percent,
               passed_count, failed_count, pass_rate
        FROM v_subject_stats
        WHERE (%s IS NULL OR branch_id = %s)
          AND (%s IS NULL OR semester = %s)
        ORDER BY pass_rate ASC, subject_code
        """,
        (branch_id, branch_id, semester, semester),
    )


def build_student_analytics(student_id: int) -> dict | None:
    """Assemble everything the student dashboard needs, in one payload.

    Deliberately one endpoint rather than six: the dashboard needs all of
    it to render, and six round-trips from the browser would show the
    page assembling itself piece by piece.
    """
    overview = get_student_overview(student_id)
    if not overview:
        return None

    subjects = get_subject_breakdown(student_id)
    timeline = get_assessment_timeline(student_id)

    risk = assess_risk(
        avg_marks=_as_float(overview.get("avg_mark_percent")),
        avg_attendance=_as_float(overview.get("avg_attendance_percent")),
        backlog_count=int(overview.get("backlog_count") or 0),
        percentile=_as_float(overview.get("percentile")),
    )

    trend = compute_trend([_as_float(a["percent"]) or 0.0 for a in timeline])

    # A falling trend is added to the *explanation* but never to the
    # score. The score has to keep matching v_at_risk_students, which is
    # set-based SQL with no notion of an individual's timeline - and a
    # dashboard that reported "Declining" in one panel while the standing
    # card listed no concerns at all read as a bug. This closes that gap
    # without breaking the parity the tests assert.
    if trend["direction"] == "declining":
        risk.reasons.append(
            f"Marks are trending down - {abs(trend['change']):.1f} points "
            "below earlier assessments"
        )
        risk.recommendations.append(
            "Review what changed since the earlier assessments before the " "next one"
        )

    return {
        "student": {
            "student_id": overview["student_id"],
            "name": overview["student_name"],
            "roll_no": overview["roll_no"],
            "branch": overview["branch_code"],
            "semester": overview["semester"],
        },
        "summary": {
            "subject_count": overview["subject_count"],
            "average_marks": _as_float(overview["avg_mark_percent"]),
            "average_attendance": _as_float(overview["avg_attendance_percent"]),
            "backlog_count": overview["backlog_count"],
            "lowest_subject": _as_float(overview["lowest_subject_percent"]),
            "highest_subject": _as_float(overview["highest_subject_percent"]),
            "class_rank": overview["class_rank"],
            "cohort_size": overview["cohort_size"],
            "percentile": _as_float(overview["percentile"]),
        },
        "risk": risk.to_dict(),
        "trend": trend,
        "subjects": subjects,
        "timeline": timeline,
        "comparison": get_cohort_comparison(student_id),
    }


def _as_float(value) -> float | None:
    """Convert a MySQL DECIMAL to a float for JSON.

    The driver returns DECIMAL columns as Python `Decimal`, which
    `jsonify` cannot serialise. Rounding to float here loses precision
    that percentages do not need.
    """
    if value is None:
        return None
    return float(value)
