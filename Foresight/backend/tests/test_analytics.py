"""Analytics: risk scoring, trends, and the SQL that computes them."""

from __future__ import annotations

import pytest
from conftest import auth_header

from services.analytics import (
    WEIGHT_BACKLOG_CAP,
    WEIGHT_PERCENTILE,
    assess_risk,
    compute_trend,
)

# --- Risk scoring (pure functions, no database) ------------------------


def test_a_strong_student_scores_zero():
    result = assess_risk(avg_marks=85, avg_attendance=95, backlog_count=0, percentile=90)
    assert result.score == 0
    assert result.band == "low"
    assert result.reasons == ["Meeting all academic requirements"]


def test_a_failing_student_is_high_risk_with_reasons():
    result = assess_risk(avg_marks=25, avg_attendance=50, backlog_count=3, percentile=5)

    assert result.band == "high"
    assert result.score > 50
    # The reasons are what make the score actionable rather than opaque.
    assert any("below the 40% pass mark" in r for r in result.reasons)
    assert any("attendance" in r.lower() for r in result.reasons)
    assert any("Failing 3 subjects" in r for r in result.reasons)
    assert result.recommendations


def test_no_marks_yields_unknown_not_a_perfect_score():
    """The original code crashed here with a TypeError, because AVG of no
    rows is NULL and `None < 40` is not comparable in Python 3."""
    result = assess_risk(avg_marks=None, avg_attendance=None, backlog_count=0)

    assert result.band == "unknown"
    assert result.score == 0
    assert "No marks" in result.reasons[0]


def test_backlog_contribution_is_capped():
    """Without the cap, ten failed subjects would swamp every other
    signal and every such student would score an identical 100."""
    two = assess_risk(avg_marks=70, avg_attendance=90, backlog_count=2, percentile=50)
    ten = assess_risk(avg_marks=70, avg_attendance=90, backlog_count=10, percentile=50)

    assert two.score == ten.score == WEIGHT_BACKLOG_CAP


def test_score_is_bounded_to_0_100():
    worst = assess_risk(avg_marks=0, avg_attendance=0, backlog_count=99, percentile=0)
    assert 0 <= worst.score <= 100


def test_bottom_quartile_adds_the_percentile_penalty():
    inside = assess_risk(avg_marks=70, avg_attendance=90, backlog_count=0, percentile=10)
    outside = assess_risk(avg_marks=70, avg_attendance=90, backlog_count=0, percentile=60)

    assert inside.score - outside.score == WEIGHT_PERCENTILE


def test_marginal_student_gets_a_reason_rather_than_a_contradiction():
    """A student between the pass mark (40) and the warning bar (55)
    lands in the medium band while triggering no scored signal. Reporting
    "medium risk" and "meeting all requirements" together was a real bug."""
    result = assess_risk(avg_marks=50, avg_attendance=90, backlog_count=0, percentile=45)

    assert result.band == "medium"
    assert result.reasons != ["Meeting all academic requirements"]
    assert "thin" in result.reasons[0]


@pytest.mark.parametrize(
    "marks,attendance,backlogs,expected",
    [
        (85, 95, 0, "low"),
        (60, 80, 0, "low"),
        (50, 80, 0, "medium"),  # below the 55% warning bar
        (80, 70, 0, "medium"),  # attendance under 75
        (80, 95, 1, "medium"),  # one backlog
        (35, 95, 0, "high"),  # below the pass mark
        (80, 55, 0, "high"),  # attendance under 60
        (80, 95, 2, "high"),  # two backlogs
    ],
)
def test_band_thresholds(marks, attendance, backlogs, expected):
    result = assess_risk(marks, attendance, backlogs, percentile=50)
    assert result.band == expected


# --- Trend detection ---------------------------------------------------


def test_trend_needs_enough_data():
    assert compute_trend([50, 60])["direction"] == "insufficient_data"
    assert compute_trend([])["direction"] == "insufficient_data"


def test_improving_trend():
    result = compute_trend([40, 45, 60, 70])
    assert result["direction"] == "improving"
    assert result["change"] > 0


def test_declining_trend():
    result = compute_trend([80, 75, 50, 45])
    assert result["direction"] == "declining"
    assert result["change"] < 0


def test_stable_trend_tolerates_small_wobble():
    """A two-point drift is noise, not a decline. Without a threshold
    every student would be labelled as trending one way or the other."""
    assert compute_trend([70, 71, 69, 72, 70])["direction"] == "stable"


# --- The SQL views -----------------------------------------------------


def test_mark_percent_weights_by_what_each_assessment_was_worth(seeded, db_conn):
    """SUM(obtained)/SUM(max), not the mean of the percentages. A 100-mark
    final must move the average five times as much as a 20-mark quiz."""
    cur = db_conn.cursor(dictionary=True)
    student_id = seeded["students"]["CSE2023001"]

    cur.execute(
        "SELECT enrollment_id FROM enrollments WHERE student_id = %s LIMIT 1",
        (student_id,),
    )
    enrollment_id = cur.fetchone()["enrollment_id"]

    cur.execute("DELETE FROM assessments WHERE enrollment_id = %s", (enrollment_id,))
    # 100% on a 20-mark quiz, 50% on a 100-mark final.
    cur.execute(
        "INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, "
        "assessed_on) VALUES (%s, 'quiz', 20, 20, CURDATE()), "
        "(%s, 'final', 50, 100, CURDATE())",
        (enrollment_id, enrollment_id),
    )

    cur.execute(
        "SELECT mark_percent FROM v_enrollment_summary WHERE enrollment_id = %s",
        (enrollment_id,),
    )
    # (20 + 50) / (20 + 100) = 58.33%.  The naive mean would be 75%.
    assert float(cur.fetchone()["mark_percent"]) == pytest.approx(58.33, abs=0.01)
    cur.close()


def test_attendance_excludes_excused_absences(seeded, db_conn):
    """An approved absence must not count against the percentage - it is
    removed from the denominator rather than counted as an absence."""
    cur = db_conn.cursor(dictionary=True)
    student_id = seeded["students"]["CSE2023001"]

    cur.execute(
        "SELECT enrollment_id FROM enrollments WHERE student_id = %s LIMIT 1",
        (student_id,),
    )
    enrollment_id = cur.fetchone()["enrollment_id"]

    cur.execute(
        "DELETE FROM attendance_records WHERE enrollment_id = %s", (enrollment_id,)
    )
    cur.execute(
        "INSERT INTO attendance_records (enrollment_id, class_date, status) VALUES "
        "(%s, '2025-01-01', 'present'), "
        "(%s, '2025-01-02', 'present'), "
        "(%s, '2025-01-03', 'late'), "  # counts as attended
        "(%s, '2025-01-04', 'absent'), "
        "(%s, '2025-01-05', 'excused')",  # excluded entirely
        (enrollment_id,) * 5,
    )

    cur.execute(
        "SELECT attendance_percent FROM v_enrollment_summary WHERE enrollment_id = %s",
        (enrollment_id,),
    )
    # attended 3 of 4 counted classes = 75%, not 3/5 = 60%.
    assert float(cur.fetchone()["attendance_percent"]) == pytest.approx(75.0, abs=0.01)
    cur.close()


def test_class_rank_orders_students_within_their_cohort(seeded, db_conn):
    cur = db_conn.cursor(dictionary=True)
    cur.execute(
        "SELECT roll_no, class_rank, cohort_size FROM v_student_rank ORDER BY class_rank"
    )
    rows = cur.fetchall()
    cur.close()

    assert rows[0]["roll_no"] == "CSE2023001"  # 80%
    assert rows[-1]["roll_no"] == "CSE2023002"  # 30%
    assert all(r["cohort_size"] == 3 for r in rows)


def test_risk_view_and_python_agree_on_the_band(seeded, db_conn):
    """The SQL view scores lists of students; the Python function
    explains one. If the two drift apart the dashboard contradicts the
    report, so this pins them together."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute(
        "SELECT roll_no, avg_mark_percent, avg_attendance_percent, backlog_count, "
        "percentile, risk_score, risk_band FROM v_at_risk_students"
    )
    rows = cur.fetchall()
    cur.close()

    assert rows, "expected at least one scored student"

    for row in rows:
        python_result = assess_risk(
            avg_marks=float(row["avg_mark_percent"]),
            avg_attendance=(
                None
                if row["avg_attendance_percent"] is None
                else float(row["avg_attendance_percent"])
            ),
            backlog_count=int(row["backlog_count"]),
            percentile=float(row["percentile"]),
        )
        assert python_result.band == row["risk_band"], row["roll_no"]
        assert python_result.score == pytest.approx(
            float(row["risk_score"]), abs=0.5
        ), row["roll_no"]


# --- The API payload ---------------------------------------------------


def test_dashboard_payload_is_complete(client, seeded, alice_token):
    response = client.get("/api/students/me", headers=auth_header(alice_token))
    assert response.status_code == 200

    body = response.get_json()
    for key in (
        "student",
        "summary",
        "risk",
        "trend",
        "subjects",
        "timeline",
        "comparison",
    ):
        assert key in body, f"missing '{key}'"

    assert body["summary"]["average_marks"] == pytest.approx(80.0, abs=0.1)
    assert body["risk"]["band"] == "low"
    assert len(body["subjects"]) == 2


def test_numbers_are_json_numbers_not_strings(client, seeded, alice_token):
    """MySQL DECIMAL becomes a Python Decimal, which Flask serialises as a
    string by default. `"80.00"` breaks every chart and makes JavaScript
    comparisons silently wrong, so a JSON provider converts them."""
    response = client.get("/api/students/me", headers=auth_header(alice_token))
    body = response.get_json()

    assert isinstance(body["summary"]["average_marks"], (int, float))
    assert isinstance(body["summary"]["backlog_count"], int)
    for subject in body["subjects"]:
        assert isinstance(subject["mark_percent"], (int, float))
        assert isinstance(subject["attendance_percent"], (int, float))


def test_at_risk_endpoint_explains_every_student(client, seeded, admin_token):
    response = client.get("/api/analytics/at-risk", headers=auth_header(admin_token))
    assert response.status_code == 200

    students = response.get_json()["students"]
    assert students, "Bob should be flagged"
    for student in students:
        assert student["reasons"], "a flagged student with no reason is not actionable"


def test_admin_overview_also_carries_reasons(client, seeded, admin_token):
    """Regression: the overview used a code path that skipped the
    explanations, so the dashboard's "Why" column rendered all dashes."""
    response = client.get("/api/admin/overview", headers=auth_header(admin_token))
    assert response.status_code == 200

    at_risk = response.get_json()["at_risk"]
    assert at_risk
    assert all(student.get("reasons") for student in at_risk)


def test_grade_distribution_always_returns_every_band(client, seeded, admin_token):
    """The chart's x-axis must not change shape because no student
    happened to earn a C this term."""
    response = client.get(
        "/api/analytics/grade-distribution", headers=auth_header(admin_token)
    )
    grades = [row["grade"] for row in response.get_json()]
    assert grades == ["A+", "A", "B", "C", "D", "E", "F"]
