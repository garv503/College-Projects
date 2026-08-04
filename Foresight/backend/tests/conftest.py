"""Shared pytest fixtures.

The tests run against a real MySQL database, not a mock. That is a
deliberate choice for this project: most of the logic worth testing lives
in SQL - the views compute the percentages, the triggers reject bad
marks, the procedures own the transactions. Mocking the database would
mean asserting that Python calls a query, while never checking the query
is correct, which is where the actual bugs are.

The database used is named by DB_NAME with `_test` appended, so running
the suite can never touch the development data. It is built from the same
schema files that ship with the project, so a schema change that breaks
the app breaks the tests too.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Point the app at the test database before anything imports `config`,
# which reads the environment at import time.
os.environ["DB_NAME"] = os.getenv("DB_NAME", "foresight") + "_test"
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-anywhere-real")
os.environ.setdefault("DEBUG", "true")

import mysql.connector  # noqa: E402

from config import config  # noqa: E402
from security import reset_rate_limits  # noqa: E402

SQL_FILES = (
    "schema.sql",
    "views.sql",
    "triggers.sql",
    "procedures.sql",
    "sample_data.sql",
)


def _split_statements(sql: str) -> list[str]:
    """Split a script into statements, honouring DELIMITER changes.

    The MySQL client understands `DELIMITER $$`, but the Python driver
    does not - it only sees a stream of text. Triggers and procedures
    contain semicolons inside their bodies, so splitting naively on `;`
    would cut them in half. This walks the script tracking the current
    delimiter, which is what lets triggers.sql and procedures.sql load.
    """
    statements: list[str] = []
    delimiter = ";"
    buffer: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()

        if stripped.upper().startswith("DELIMITER "):
            # Flush anything pending before the delimiter changes.
            pending = "\n".join(buffer).strip()
            if pending:
                statements.append(pending)
            buffer = []
            delimiter = stripped.split(None, 1)[1].strip()
            continue

        if not stripped or stripped.startswith("--"):
            continue

        buffer.append(line)

        if stripped.endswith(delimiter):
            statement = "\n".join(buffer).strip()
            statement = statement[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []

    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements


def _server_connection():
    """Connect to the MySQL server without selecting a database."""
    return mysql.connector.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        autocommit=True,
    )


@pytest.fixture(scope="session", autouse=True)
def build_test_database():
    """Create the test database once per session from the SQL files."""
    try:
        conn = _server_connection()
    except mysql.connector.Error as exc:
        pytest.skip(f"MySQL is not reachable, skipping integration tests: {exc}")

    cur = conn.cursor()
    test_db = config.db_name

    for filename in SQL_FILES:
        path = PROJECT_ROOT / "database" / filename
        sql = path.read_text(encoding="utf-8")

        # schema.sql hardcodes the production database name. Rewriting it
        # here keeps a single schema file as the source of truth instead
        # of maintaining a near-identical copy for tests.
        sql = sql.replace("foresight", test_db)

        for statement in _split_statements(sql):
            cur.execute(statement)
            # Some statements return a result set; leaving it unread
            # makes the next execute() fail with "Unread result found".
            while cur.nextset():
                pass

    cur.close()
    conn.close()

    yield

    if os.getenv("KEEP_TEST_DB") != "1":
        conn = _server_connection()
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS `{test_db}`")
        cur.close()
        conn.close()


@pytest.fixture()
def app(build_test_database):
    """A Flask app wired to the test database."""
    from app import create_app

    application = create_app(testing=True)
    yield application


@pytest.fixture()
def client(app):
    """HTTP test client. Rate-limit counters are reset between tests so
    one test's failed logins cannot 429 the next one."""
    reset_rate_limits()
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def db_conn(build_test_database):
    """A direct connection, for arranging data and asserting on it."""
    conn = mysql.connector.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        autocommit=True,
    )
    yield conn
    conn.close()


@pytest.fixture()
def seeded(db_conn):
    """A small, fully deterministic dataset.

    Hand-built rather than generated so every expected number in the
    tests can be worked out by hand:

        alice  - 80% in both subjects, perfect attendance   -> low risk
        bob    - 30% in both subjects, poor attendance      -> high risk
        carol  - 60%, no attendance recorded                -> medium

    Passwords are stored as plain text throughout (see
    backend/security.py) - `PASSWORD` below is both what is inserted and
    what a test logs in with, with no hashing step in between.
    """
    cur = db_conn.cursor(dictionary=True)

    # Child-first, so foreign keys never block the wipe.
    for table in (
        "attendance_records",
        "assessments",
        "enrollments",
        "users",
        "students",
        "audit_log",
        "login_attempts",
    ):
        cur.execute(f"DELETE FROM {table}")

    cur.execute("SELECT branch_id FROM branches WHERE code = 'CSE'")
    branch_id = cur.fetchone()["branch_id"]

    cur.execute(
        "SELECT subject_id, code FROM subjects "
        "WHERE branch_id = %s AND semester = 3 ORDER BY code LIMIT 2",
        (branch_id,),
    )
    subjects = cur.fetchall()

    people = [
        ("CSE2023001", "Alice Alpha", "alice@test.edu", 80.0, 100.0),
        ("CSE2023002", "Bob Beta", "bob@test.edu", 30.0, 45.0),
        ("CSE2023003", "Carol Gamma", "carol@test.edu", 60.0, None),
    ]

    PASSWORD = "Test@1234"
    created = {}
    today = date.today()

    for roll_no, name, email, mark_pct, attendance_pct in people:
        cur.execute(
            "INSERT INTO students (roll_no, name, email, branch_id, semester, "
            "admission_year) VALUES (%s, %s, %s, %s, 3, 2023)",
            (roll_no, name, email, branch_id),
        )
        student_id = cur.lastrowid
        created[roll_no] = student_id

        # No users.email here: forgot-password falls back to the linked
        # students.email via COALESCE, same as it does in production.
        cur.execute(
            "INSERT INTO users (username, password, role, student_id, "
            "must_change_pw) VALUES (%s, %s, 'student', %s, FALSE)",
            (roll_no.lower(), PASSWORD, student_id),
        )

        for subject in subjects:
            cur.execute(
                "INSERT INTO enrollments (student_id, subject_id, academic_year) "
                "VALUES (%s, %s, 2023)",
                (student_id, subject["subject_id"]),
            )
            enrollment_id = cur.lastrowid

            # Four assessments out of 100 each, so mark_percent is
            # exactly mark_pct and the expected value needs no arithmetic.
            for index in range(4):
                cur.execute(
                    "INSERT INTO assessments (enrollment_id, type, marks_obtained, "
                    "max_marks, assessed_on) VALUES (%s, %s, %s, 100, %s)",
                    (
                        enrollment_id,
                        ("quiz", "assignment", "midterm", "final")[index],
                        mark_pct,
                        today - timedelta(days=30 - index * 7),
                    ),
                )

            if attendance_pct is not None:
                # 20 classes, so the percentage lands on a whole number.
                present = int(round(attendance_pct / 100 * 20))
                for day in range(20):
                    cur.execute(
                        "INSERT INTO attendance_records (enrollment_id, class_date, "
                        "status) VALUES (%s, %s, %s)",
                        (
                            enrollment_id,
                            today - timedelta(days=day + 1),
                            "present" if day < present else "absent",
                        ),
                    )

    # Staff accounts. These carry their own users.email, since they have
    # no students row for forgot-password to fall back to.
    cur.execute(
        "INSERT INTO users (username, password, email, role, must_change_pw) "
        "VALUES ('admin', %s, 'admin@test.edu', 'admin', FALSE)",
        (PASSWORD,),
    )
    cur.execute(
        "INSERT INTO users (username, password, email, role, must_change_pw) "
        "VALUES ('teacher', %s, 'teacher@test.edu', 'faculty', FALSE)",
        (PASSWORD,),
    )

    cur.close()

    return {
        "password": PASSWORD,
        "students": created,
        "subject_ids": [s["subject_id"] for s in subjects],
        "branch_id": branch_id,
        "emails": {
            "CSE2023001": "alice@test.edu",
            "CSE2023002": "bob@test.edu",
            "CSE2023003": "carol@test.edu",
            "admin": "admin@test.edu",
            "teacher": "teacher@test.edu",
        },
    }


# --- Auth helpers ------------------------------------------------------


def login(client, username, password="Test@1234"):
    """Sign in and return the token, or None if rejected."""
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    if response.status_code != 200:
        return None
    return response.get_json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token(client, seeded):
    return login(client, "admin", seeded["password"])


@pytest.fixture()
def faculty_token(client, seeded):
    return login(client, "teacher", seeded["password"])


@pytest.fixture()
def alice_token(client, seeded):
    return login(client, "cse2023001", seeded["password"])
