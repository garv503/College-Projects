"""Database guarantees: constraints, triggers, and the CSV importer.

These assert that bad data cannot get in *even if the application layer
has a bug* - which is the whole reason the rules live in the database.
"""

from __future__ import annotations

import io
import re
from datetime import UTC, datetime

import mysql.connector
import pytest
from conftest import auth_header, login

# --- Triggers ----------------------------------------------------------


def test_marks_cannot_exceed_the_maximum(seeded, db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT enrollment_id FROM enrollments LIMIT 1")
    enrollment_id = cur.fetchone()[0]

    with pytest.raises(mysql.connector.Error) as exc:
        cur.execute(
            "INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, "
            "assessed_on) VALUES (%s, 'quiz', 150, 100, CURDATE())",
            (enrollment_id,),
        )
    assert "exceed max_marks" in str(exc.value)
    cur.close()


def test_marks_cannot_be_dated_in_the_future(seeded, db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT enrollment_id FROM enrollments LIMIT 1")
    enrollment_id = cur.fetchone()[0]

    with pytest.raises(mysql.connector.Error) as exc:
        cur.execute(
            "INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, "
            "assessed_on) VALUES (%s, 'quiz', 10, 20, '2099-01-01')",
            (enrollment_id,),
        )
    assert "future" in str(exc.value)
    cur.close()


def test_negative_marks_are_rejected(seeded, db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT enrollment_id FROM enrollments LIMIT 1")
    enrollment_id = cur.fetchone()[0]

    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, "
            "assessed_on) VALUES (%s, 'quiz', -5, 20, CURDATE())",
            (enrollment_id,),
        )
    cur.close()


def test_changing_a_mark_writes_an_audit_row(seeded, db_conn):
    """The audit trail is written by a trigger, so a change made outside
    the application is recorded too. This test writes raw SQL on purpose."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SET @app_user = 'test_runner'")
    cur.execute("DELETE FROM audit_log")

    cur.execute("SELECT assessment_id FROM assessments LIMIT 1")
    assessment_id = cur.fetchone()["assessment_id"]

    cur.execute(
        "UPDATE assessments SET marks_obtained = 42 WHERE assessment_id = %s",
        (assessment_id,),
    )

    cur.execute(
        "SELECT actor, action, entity_id FROM audit_log WHERE action = 'assessment.update'"
    )
    rows = cur.fetchall()
    cur.close()

    assert len(rows) == 1
    assert rows[0]["actor"] == "test_runner"
    assert rows[0]["entity_id"] == assessment_id


def test_saving_a_mark_unchanged_creates_no_audit_noise(seeded, db_conn):
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SET @app_user = 'test_runner'")
    cur.execute("DELETE FROM audit_log")

    cur.execute("SELECT assessment_id, marks_obtained FROM assessments LIMIT 1")
    row = cur.fetchone()

    cur.execute(
        "UPDATE assessments SET marks_obtained = %s WHERE assessment_id = %s",
        (row["marks_obtained"], row["assessment_id"]),
    )

    cur.execute("SELECT COUNT(*) AS n FROM audit_log WHERE action = 'assessment.update'")
    assert cur.fetchone()["n"] == 0
    cur.close()


# --- Constraints -------------------------------------------------------


def test_roll_numbers_must_be_unique(seeded, db_conn):
    cur = db_conn.cursor()
    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO students (roll_no, name, email, branch_id, semester, "
            "admission_year) VALUES ('CSE2023001', 'Impostor', 'x@test.edu', %s, 3, 2023)",
            (seeded["branch_id"],),
        )
    cur.close()


def test_a_student_cannot_be_marked_twice_for_one_class(seeded, db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT enrollment_id FROM enrollments LIMIT 1")
    enrollment_id = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO attendance_records (enrollment_id, class_date, status) "
        "VALUES (%s, '2024-06-01', 'present')",
        (enrollment_id,),
    )
    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO attendance_records (enrollment_id, class_date, status) "
            "VALUES (%s, '2024-06-01', 'absent')",
            (enrollment_id,),
        )
    cur.close()


def test_a_student_account_must_point_at_a_student(seeded, db_conn):
    """Enforced by a CHECK, so no application bug can create an orphaned
    student login that the dashboard would then crash on."""
    cur = db_conn.cursor()
    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO users (username, password, role, student_id) "
            "VALUES ('orphan', 'x', 'student', NULL)"
        )
    cur.close()


def test_semester_must_be_in_range(seeded, db_conn):
    cur = db_conn.cursor()
    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO students (roll_no, name, email, branch_id, semester, "
            "admission_year) VALUES ('CSE2023777', 'X', 'x777@test.edu', %s, 99, 2023)",
            (seeded["branch_id"],),
        )
    cur.close()


def test_deleting_a_student_cascades_to_their_records(seeded, db_conn):
    cur = db_conn.cursor(dictionary=True)
    student_id = seeded["students"]["CSE2023003"]

    cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))

    for table in ("enrollments", "users"):
        cur.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE student_id = %s", (student_id,)
        )
        assert cur.fetchone()["n"] == 0, f"{table} rows were orphaned"
    cur.close()


# --- CSV import --------------------------------------------------------


def _upload(client, token, text, endpoint="/api/admin/import/marks"):
    return client.post(
        endpoint,
        data={"file": (io.BytesIO(text.encode("utf-8")), "upload.csv")},
        content_type="multipart/form-data",
        headers=auth_header(token),
    )


def test_valid_marks_csv_imports(client, seeded, admin_token):
    csv_text = (
        "roll_no,subject_code,type,marks_obtained,max_marks,assessed_on\n"
        "CSE2023001,CS301,quiz,18,20,2025-01-15\n"
        "CSE2023002,CS301,quiz,12,20,2025-01-15\n"
    )
    response = _upload(client, admin_token, csv_text)

    assert response.status_code == 200
    assert response.get_json()["imported"] == 2


def test_a_bad_row_rejects_the_whole_file(client, seeded, admin_token, db_conn):
    """All-or-nothing. A partial import leaves the operator with no
    straightforward way to work out where to resume."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS n FROM assessments")
    before = cur.fetchone()["n"]

    csv_text = (
        "roll_no,subject_code,type,marks_obtained,max_marks,assessed_on\n"
        "CSE2023001,CS301,quiz,18,20,2025-01-15\n"  # valid
        "CSE2023001,CS301,quiz,999,20,2025-01-15\n"  # over the maximum
    )
    response = _upload(client, admin_token, csv_text)
    assert response.status_code == 422

    cur.execute("SELECT COUNT(*) AS n FROM assessments")
    assert cur.fetchone()["n"] == before, "a rejected file still wrote rows"
    cur.close()


def test_import_errors_name_the_line_and_the_problem(client, seeded, admin_token):
    csv_text = (
        "roll_no,subject_code,type,marks_obtained,max_marks,assessed_on\n"
        "NOSUCH,CS301,quiz,10,20,2025-01-15\n"
        "CSE2023001,CS301,banana,10,20,2025-01-15\n"
    )
    response = _upload(client, admin_token, csv_text)
    errors = response.get_json()["error"]["details"]["errors"]

    assert len(errors) == 2
    assert errors[0]["line"] == 2 and "not enrolled" in errors[0]["message"]
    assert errors[1]["line"] == 3 and "banana" in errors[1]["message"]


def test_missing_columns_are_reported_clearly(client, seeded, admin_token):
    response = _upload(client, admin_token, "roll_no,marks\nCSE2023001,50\n")

    assert response.status_code == 400
    assert "missing required column" in response.get_json()["error"]["message"].lower()


def test_duplicate_rows_in_one_file_are_rejected(client, seeded, admin_token):
    """A duplicate is a mistake in the operator's spreadsheet. Silently
    keeping the last one would hide it."""
    csv_text = (
        "roll_no,subject_code,type,marks_obtained,max_marks,assessed_on\n"
        "CSE2023001,CS301,quiz,18,20,2025-01-15\n"
        "CSE2023001,CS301,quiz,15,20,2025-01-15\n"
    )
    response = _upload(client, admin_token, csv_text)

    assert response.status_code == 422
    assert "duplicate" in str(response.get_json()).lower()


def test_excel_byte_order_mark_is_handled(client, seeded, admin_token):
    """Excel writes a BOM, which would otherwise turn the first header
    into "﻿roll_no" and make the column look missing."""
    csv_text = (
        "﻿roll_no,subject_code,type,marks_obtained,max_marks,assessed_on\n"
        "CSE2023001,CS301,midterm,40,50,2025-01-15\n"
    )
    response = _upload(client, admin_token, csv_text)
    assert response.status_code == 200


def test_attendance_import_accepts_valid_statuses(client, seeded, admin_token):
    csv_text = (
        "roll_no,subject_code,class_date,status\n"
        "CSE2023001,CS301,2025-02-03,present\n"
        "CSE2023002,CS301,2025-02-03,absent\n"
    )
    response = _upload(client, admin_token, csv_text, "/api/admin/import/attendance")
    assert response.status_code == 200
    assert response.get_json()["imported"] == 2


def test_attendance_import_rejects_an_unknown_status(client, seeded, admin_token):
    csv_text = (
        "roll_no,subject_code,class_date,status\n" "CSE2023001,CS301,2025-02-04,maybe\n"
    )
    response = _upload(client, admin_token, csv_text, "/api/admin/import/attendance")
    assert response.status_code == 422


# --- CSV export --------------------------------------------------------
# These endpoints were originally untested, and shipped broken: the
# cohort export selected a column the view did not expose, so it returned
# 503 for every caller. A download that is never asserted on is exactly
# the kind of thing that rots silently.


def test_cohort_export_returns_csv(client, seeded, admin_token):
    response = client.get(
        "/api/admin/export/cohort.csv", headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]

    body = response.get_data(as_text=True)
    assert "Roll No,Name,Branch" in body
    assert "CSE2023001" in body


def test_cohort_export_respects_the_filters(client, seeded, admin_token):
    response = client.get(
        f"/api/admin/export/cohort.csv?branch_id={seeded['branch_id']}&semester=3",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert "CSE2023001" in response.get_data(as_text=True)


def test_marks_template_is_downloadable(client, seeded, admin_token):
    response = client.get(
        "/api/admin/import/template.csv", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    header = response.get_data(as_text=True).splitlines()[0]
    # The template's header must match what the importer requires, or the
    # round trip of "download template, fill in, upload" cannot work.
    assert header == "roll_no,subject_code,type,marks_obtained,max_marks,assessed_on"


def test_report_card_csv_downloads(client, seeded, alice_token):
    student_id = seeded["students"]["CSE2023001"]
    response = client.get(
        f"/api/students/{student_id}/report-card.csv", headers=auth_header(alice_token)
    )
    assert response.status_code == 200
    assert response.mimetype == "text/csv"

    body = response.get_data(as_text=True)
    assert "Alice Alpha" in body
    assert "GPA" in body


def test_report_card_json_includes_grades_and_gpa(client, seeded, alice_token):
    student_id = seeded["students"]["CSE2023001"]
    response = client.get(
        f"/api/students/{student_id}/report-card", headers=auth_header(alice_token)
    )
    assert response.status_code == 200

    card = response.get_json()
    assert card["summary"]["gpa"] is not None
    assert card["summary"]["overall_grade"] == "A"  # 80% -> A
    assert all(subject["grade"] for subject in card["subjects"])


def test_non_csv_upload_is_rejected(client, seeded, admin_token):
    response = client.post(
        "/api/admin/import/marks",
        data={"file": (io.BytesIO(b"whatever"), "notes.txt")},
        content_type="multipart/form-data",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


# --- Student creation --------------------------------------------------


def test_creating_a_student_enrolls_and_issues_credentials(
    client, seeded, admin_token, db_conn
):
    response = client.post(
        "/api/admin/students",
        json={
            "name": "Dana Delta",
            "roll_no": "CSE2023010",
            "email": "dana@test.edu",
            "branch_id": seeded["branch_id"],
            "semester": 3,
            "admission_year": 2023,
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    body = response.get_json()
    assert body["credentials"]["username"] == "cse2023010"
    # Enrolled by the stored procedure into every subject for the cohort.
    assert body["subjects_enrolled"] > 0

    # The generated password is random, not derived from the name - the
    # original built `Name@123`, which anyone could guess.
    password = body["credentials"]["password"]
    assert "dana" not in password.lower()
    assert len(password) >= 12

    # Stored as plain text by design (see backend/security.py), so the
    # value on file is exactly what the response returned - and it stays
    # retrievable afterwards through GET .../credentials, not just here.
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT password FROM users WHERE username = 'cse2023010'")
    assert cur.fetchone()["password"] == password

    lookup = client.get(
        f"/api/admin/students/{body['student_id']}/credentials",
        headers=auth_header(admin_token),
    )
    assert lookup.status_code == 200
    assert lookup.get_json() == {"username": "cse2023010", "password": password}
    cur.close()


def test_duplicate_roll_number_returns_409_not_500(client, seeded, admin_token):
    """The original hit the UNIQUE constraint and died with a raw 500."""
    response = client.post(
        "/api/admin/students",
        json={
            "name": "Clone",
            "roll_no": "CSE2023001",
            "email": "clone@test.edu",
            "branch_id": seeded["branch_id"],
            "semester": 3,
            "admission_year": 2023,
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "not-an-email"),
        ("semester", 99),
        ("roll_no", "!!"),
        ("name", ""),
        ("admission_year", 1200),
    ],
)
def test_invalid_student_fields_are_rejected(client, seeded, admin_token, field, value):
    payload = {
        "name": "Test Student",
        "roll_no": "CSE2023050",
        "email": "test50@test.edu",
        "branch_id": seeded["branch_id"],
        "semester": 3,
        "admission_year": 2023,
        field: value,
    }
    response = client.post(
        "/api/admin/students", json=payload, headers=auth_header(admin_token)
    )
    assert response.status_code == 400, f"{field}={value!r} was accepted"


def test_deactivating_a_student_preserves_their_history(
    client, seeded, admin_token, db_conn
):
    """A soft delete. A hard DELETE would cascade away the marks that the
    cohort statistics are built from."""
    student_id = seeded["students"]["CSE2023002"]

    response = client.delete(
        f"/api/admin/students/{student_id}", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT is_active FROM students WHERE student_id = %s", (student_id,))
    assert cur.fetchone()["is_active"] == 0

    cur.execute(
        "SELECT COUNT(*) AS n FROM assessments a "
        "JOIN enrollments e ON e.enrollment_id = a.enrollment_id "
        "WHERE e.student_id = %s",
        (student_id,),
    )
    assert cur.fetchone()["n"] > 0, "marks were destroyed"
    cur.close()


# --- SQL injection -----------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1",
        "'; DROP TABLE students; --",
        "admin'--",
        '" OR 1=1 --',
    ],
)
def test_injection_attempts_in_login_are_treated_as_text(client, seeded, payload):
    response = client.post(
        "/api/auth/login", json={"username": payload, "password": payload}
    )
    assert response.status_code in (400, 401)


def test_injection_in_search_does_not_execute(client, seeded, admin_token, db_conn):
    response = client.get(
        "/api/students?q='; DROP TABLE students; --", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS n FROM students")
    assert cur.fetchone()["n"] == 3, "the students table did not survive"
    cur.close()


def test_sort_parameter_is_whitelisted(client, seeded, admin_token):
    """A column name cannot be a bound parameter, so it is resolved
    through a fixed map. Anything else must be refused, not interpolated."""
    response = client.get(
        "/api/students?sort=(SELECT+1)", headers=auth_header(admin_token)
    )
    assert response.status_code == 400


# --- Sign-in tracking --------------------------------------------------


def test_a_student_can_have_only_one_login_account(seeded, db_conn):
    """The admin student list LEFT JOINs users to show "last seen". That
    join is only safe if a student has at most one account - otherwise
    they appear twice and the pagination total is inflated. The UNIQUE
    constraint is what makes the join correct rather than merely lucky."""
    cur = db_conn.cursor()
    student_id = seeded["students"]["CSE2023001"]

    with pytest.raises(mysql.connector.Error):
        cur.execute(
            "INSERT INTO users (username, password, role, student_id) "
            "VALUES ('duplicate_login', 'Whatever@1', 'student', %s)",
            (student_id,),
        )
    cur.close()


def test_many_staff_accounts_can_share_a_null_student_id(seeded, db_conn):
    """The flip side: UNIQUE must not stop a second admin existing.
    MySQL allows many NULLs in a UNIQUE column, which is exactly why the
    constraint can sit on a nullable column here."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute(
        "INSERT INTO users (username, password, role, student_id) "
        "VALUES ('second_admin', 'Whatever@1', 'admin', NULL)"
    )
    cur.execute("SELECT COUNT(*) AS n FROM users WHERE student_id IS NULL")
    assert cur.fetchone()["n"] >= 3  # admin, teacher, second_admin
    cur.close()


def test_last_login_is_null_until_the_first_sign_in(client, seeded, admin_token):
    response = client.get("/api/students", headers=auth_header(admin_token))
    assert response.status_code == 200

    students = response.get_json()["students"]
    assert students
    # The seed fixture creates accounts but never signs them in.
    assert all(s["last_login_at"] is None for s in students)


def test_signing_in_records_last_login(client, seeded, admin_token):
    login(client, "cse2023001", seeded["password"])

    response = client.get("/api/students?q=CSE2023001", headers=auth_header(admin_token))
    student = response.get_json()["students"][0]
    assert student["last_login_at"] is not None


def test_timestamps_are_returned_with_a_timezone(client, seeded, admin_token):
    """A naive ISO string is read by JavaScript's `new Date()` as *local*
    time. Because the database session runs in UTC, an unlabelled
    timestamp made a sign-in that just happened render as "5h ago" for a
    viewer in IST. The offset is what stops that."""
    login(client, "cse2023001", seeded["password"])

    response = client.get("/api/students?q=CSE2023001", headers=auth_header(admin_token))
    stamp = response.get_json()["students"][0]["last_login_at"]

    assert stamp is not None
    assert stamp.endswith("+00:00"), f"missing timezone offset: {stamp!r}"

    # And it must actually be close to now, not offset by hours.
    parsed = datetime.fromisoformat(stamp)
    drift = abs((datetime.now(UTC) - parsed).total_seconds())
    assert drift < 120, f"timestamp is {drift:.0f}s away from now"


def _walk_strings(obj, path=""):
    """Yield every (path, string) pair in a nested JSON structure."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_strings(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk_strings(value, f"{path}[{index}]")
    elif isinstance(obj, str):
        yield path, obj


DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
OFFSET_RE = re.compile(r"([+-]\d{2}:\d{2}|Z)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_no_endpoint_returns_a_timezone_naive_timestamp(client, seeded, admin_token):
    """A blanket sweep of the API surface, not a per-field check.

    The first version of the timezone fix lived in the JSON provider, so
    it only worked for routes that passed a real datetime through. Three
    routes called `.isoformat()` themselves and handed jsonify a string,
    which sailed past the provider untouched - and the audit log rendered
    every entry hours adrift. Checking one field would not have caught
    that; walking every response does, including for routes added later.
    """
    login(client, "cse2023001", seeded["password"])
    student_id = seeded["students"]["CSE2023001"]

    endpoints = [
        "/api/auth/me",
        "/api/admin/audit-log",
        "/api/students",
        f"/api/students/{student_id}",
        f"/api/students/{student_id}/timeline",
        f"/api/students/{student_id}/report-card",
        "/api/analytics/at-risk",
        "/api/branches",
        "/api/subjects",
    ]

    naive = []
    checked = 0

    for endpoint in endpoints:
        response = client.get(endpoint, headers=auth_header(admin_token))
        assert response.status_code == 200, endpoint

        for path, value in _walk_strings(response.get_json(), endpoint):
            if DATETIME_RE.match(value):
                checked += 1
                if not OFFSET_RE.search(value):
                    naive.append((path, value))
            elif DATE_RE.match(value):
                # A calendar date has no time zone - an exam sat on the
                # 3rd is the 3rd everywhere. It must NOT gain a fake one.
                checked += 1
                assert "T" not in value, f"{path} turned a date into a datetime"

    assert checked > 0, "the sweep found no timestamps - it is not testing anything"
    assert not naive, f"timezone-naive timestamps returned: {naive}"


def test_students_can_be_sorted_by_last_seen(client, seeded, admin_token):
    login(client, "cse2023001", seeded["password"])

    response = client.get(
        "/api/students?sort=last_seen&order=desc", headers=auth_header(admin_token)
    )
    assert response.status_code == 200

    students = response.get_json()["students"]
    # Descending puts real timestamps ahead of the NULLs.
    assert students[0]["roll_no"] == "CSE2023001"
    assert students[0]["last_login_at"] is not None
