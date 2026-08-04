"""Authorization: who is allowed to read and change what.

These are the tests for the original project's most serious flaw. Every
endpoint was open: `GET /student-data/7` returned student 7's marks to
anyone who asked, and `admin.html` was protected only by not being linked
from anywhere.
"""

from __future__ import annotations

import re

import pytest
from conftest import auth_header, login

# Every route that must reject an anonymous caller.
PROTECTED_GET_ROUTES = [
    "/api/auth/me",
    "/api/students/me",
    "/api/students",
    "/api/students/1",
    "/api/students/1/subjects",
    "/api/students/1/timeline",
    "/api/students/1/report-card",
    "/api/branches",
    "/api/subjects",
    "/api/analytics/cohort",
    "/api/analytics/at-risk",
    "/api/analytics/grade-distribution",
    "/api/admin/overview",
    "/api/admin/audit-log",
    "/api/admin/export/cohort.csv",
    "/api/admin/students/1/credentials",
]

# Routes a signed-in student must not reach at all.
STAFF_ONLY_GET_ROUTES = [
    "/api/students",
    "/api/analytics/cohort",
    "/api/analytics/at-risk",
    "/api/analytics/grade-distribution",
    "/api/analytics/subjects",
    "/api/admin/overview",
    "/api/admin/audit-log",
    "/api/admin/export/cohort.csv",
    "/api/admin/students/1/credentials",
]

# Routes only an admin may reach - faculty is not enough. Password lookup
# is admin-only for the same reason account creation is: faculty enters
# marks, but does not manage who can sign in as whom.
ADMIN_ONLY_GET_ROUTES = ["/api/admin/audit-log", "/api/admin/students/1/credentials"]


@pytest.mark.parametrize("route", PROTECTED_GET_ROUTES)
def test_anonymous_access_is_rejected(client, seeded, route):
    response = client.get(route)
    assert response.status_code == 401, f"{route} allowed an anonymous caller"


@pytest.mark.parametrize("route", STAFF_ONLY_GET_ROUTES)
def test_students_cannot_reach_staff_routes(client, seeded, alice_token, route):
    response = client.get(route, headers=auth_header(alice_token))
    assert response.status_code == 403, f"{route} allowed a student"


@pytest.mark.parametrize("route", ADMIN_ONLY_GET_ROUTES)
def test_faculty_cannot_reach_admin_only_routes(client, seeded, faculty_token, route):
    response = client.get(route, headers=auth_header(faculty_token))
    assert response.status_code == 403, f"{route} allowed faculty"


# --- The IDOR that the original project had ---------------------------


def test_a_student_cannot_read_another_students_records(client, seeded, alice_token):
    """The headline fix. Changing the id in the URL used to work."""
    bob_id = seeded["students"]["CSE2023002"]

    response = client.get(f"/api/students/{bob_id}", headers=auth_header(alice_token))
    assert response.status_code == 403


@pytest.mark.parametrize(
    "suffix",
    ["", "/subjects", "/timeline", "/comparison", "/report-card", "/report-card.csv"],
)
def test_every_per_student_route_checks_ownership(client, seeded, alice_token, suffix):
    """One test per sub-route: it is easy to add a new endpoint and
    forget the ownership check on that one."""
    bob_id = seeded["students"]["CSE2023002"]

    response = client.get(
        f"/api/students/{bob_id}{suffix}", headers=auth_header(alice_token)
    )
    assert response.status_code == 403, f"/api/students/<id>{suffix} leaked data"


def test_a_student_can_read_their_own_records(client, seeded, alice_token):
    alice_id = seeded["students"]["CSE2023001"]

    response = client.get(f"/api/students/{alice_id}", headers=auth_header(alice_token))
    assert response.status_code == 200
    assert response.get_json()["student"]["roll_no"] == "CSE2023001"


def test_students_me_uses_the_token_not_a_url_parameter(client, seeded, alice_token):
    """`/me` exists so the front end never puts an id in a URL at all."""
    response = client.get("/api/students/me", headers=auth_header(alice_token))
    assert response.status_code == 200
    assert response.get_json()["student"]["roll_no"] == "CSE2023001"


def test_staff_may_read_any_student(client, seeded, admin_token, faculty_token):
    bob_id = seeded["students"]["CSE2023002"]

    for token in (admin_token, faculty_token):
        response = client.get(f"/api/students/{bob_id}", headers=auth_header(token))
        assert response.status_code == 200


# --- Write access ------------------------------------------------------


def test_students_cannot_create_students(client, seeded, alice_token):
    response = client.post(
        "/api/admin/students",
        json={
            "name": "Intruder",
            "roll_no": "CSE2023999",
            "email": "intruder@test.edu",
            "branch_id": seeded["branch_id"],
            "semester": 3,
            "admission_year": 2023,
        },
        headers=auth_header(alice_token),
    )
    assert response.status_code == 403


def test_students_cannot_reset_passwords(client, seeded, alice_token):
    bob_id = seeded["students"]["CSE2023002"]
    response = client.post(
        f"/api/admin/students/{bob_id}/reset-password", headers=auth_header(alice_token)
    )
    assert response.status_code == 403


def test_faculty_cannot_create_students(client, seeded, faculty_token):
    """Faculty enter marks; they do not manage accounts."""
    response = client.post(
        "/api/admin/students",
        json={
            "name": "New Student",
            "roll_no": "CSE2023998",
            "email": "new@test.edu",
            "branch_id": seeded["branch_id"],
            "semester": 3,
            "admission_year": 2023,
        },
        headers=auth_header(faculty_token),
    )
    assert response.status_code == 403


def test_faculty_can_record_marks(client, seeded, faculty_token):
    response = client.post(
        "/api/admin/assessments",
        json={
            "student_id": seeded["students"]["CSE2023001"],
            "subject_id": seeded["subject_ids"][0],
            "type": "quiz",
            "marks_obtained": 18,
            "max_marks": 20,
        },
        headers=auth_header(faculty_token),
    )
    assert response.status_code == 201


def test_students_cannot_record_marks(client, seeded, alice_token):
    """Otherwise a student could award themselves a perfect score."""
    response = client.post(
        "/api/admin/assessments",
        json={
            "student_id": seeded["students"]["CSE2023001"],
            "subject_id": seeded["subject_ids"][0],
            "type": "final",
            "marks_obtained": 100,
            "max_marks": 100,
        },
        headers=auth_header(alice_token),
    )
    assert response.status_code == 403


def test_staff_account_has_no_student_dashboard(client, seeded, admin_token):
    """An admin is not a student, so /students/me has nothing to return.
    A 404 is correct here; a 500 would mean the code assumed otherwise."""
    response = client.get("/api/students/me", headers=auth_header(admin_token))
    assert response.status_code == 404


def test_admin_password_reset_invalidates_the_old_password(client, seeded, admin_token):
    bob_id = seeded["students"]["CSE2023002"]

    response = client.post(
        f"/api/admin/students/{bob_id}/reset-password", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    new_password = response.get_json()["password"]
    assert login(client, "cse2023002", seeded["password"]) is None
    assert login(client, "cse2023002", new_password) is not None


# --- Security headers and audit accountability -------------------------


def test_security_headers_are_present(client, seeded):
    response = client.get("/")

    csp = response.headers.get("Content-Security-Policy", "")
    assert csp, "no Content-Security-Policy"

    # The point of the policy: injected inline script must not run.
    # `'unsafe-inline'` inside script-src would silently undo that, so it
    # is asserted against specifically rather than trusting the string.
    script_src = next(
        (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
    )
    assert "'unsafe-inline'" not in script_src, f"script-src is unsafe: {script_src}"
    assert "'self'" in script_src

    for directive in ("object-src 'none'", "frame-ancestors 'none'", "base-uri 'self'"):
        assert directive in csp, f"missing: {directive}"

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "same-origin"


def test_api_responses_are_not_cached(client, seeded, admin_token):
    """Marks - and on one route a password - must not sit in the browser's
    disk cache after the user walks away."""
    response = client.get("/api/students", headers=auth_header(admin_token))
    assert "no-store" in response.headers.get("Cache-Control", "")


def test_docs_page_carries_a_nonce_matching_its_policy(client, seeded):
    """The Swagger bootstrap is the one inline script in the project. It
    must be allowed by nonce, not by weakening the policy for everyone."""
    response = client.get("/api/docs")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    csp = response.headers["Content-Security-Policy"]

    match = re.search(r'<script nonce="([^"]+)"', html)
    assert match, "the inline script has no nonce"
    assert f"'nonce-{match.group(1)}'" in csp, "the nonce is not in the policy"


def test_each_request_gets_a_fresh_nonce(client, seeded):
    """A reused nonce is as good as no nonce: anyone who learns it can
    embed script that passes the policy on every later request."""
    first = client.get("/api/docs").headers["Content-Security-Policy"]
    second = client.get("/api/docs").headers["Content-Security-Policy"]
    assert first != second


def test_viewing_a_password_is_audited(client, seeded, admin_token, db_conn):
    """Plaintext storage gives up the guarantee that a password cannot be
    read. What remains is that it cannot be read *anonymously* - so the
    lookup must always leave a trace naming who did it."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute("DELETE FROM audit_log")

    student_id = seeded["students"]["CSE2023001"]
    response = client.get(
        f"/api/admin/students/{student_id}/credentials", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    cur.execute(
        "SELECT actor, action, entity_id, details FROM audit_log "
        "WHERE action = 'password.viewed'"
    )
    rows = cur.fetchall()
    cur.close()

    assert len(rows) == 1, "reading a password left no audit trail"
    assert rows[0]["actor"] == "admin"
    assert rows[0]["entity_id"] == student_id

    # The log records that a lookup happened - never the secret itself.
    assert seeded["password"] not in str(rows[0]["details"])
