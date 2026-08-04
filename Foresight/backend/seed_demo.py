"""Generate a realistic demo dataset.

    python backend/seed_demo.py            seed an empty database
    python backend/seed_demo.py --force    wipe and re-seed

Creates staff logins and a cohort of students with a full term of marks
and daily attendance, so the dashboard has something worth looking at
the first time it is opened.

Running it against a database that already has students does nothing
unless `--force` (or `SEED_FORCE=1`) is given. That is what makes
`docker compose up` safe to run repeatedly: the seed container restarts
every time, and without the guard it would delete any student added
through the admin console.

The generated data is deliberately *shaped* rather than uniformly
random - a fixed proportion of students are strong, average, struggling
or declining. Uniform random marks would put every student near 50% with
a flat trend, and none of the analytics (ranking, risk banding, trend
detection) would have anything to show.

The random seed is fixed, so re-running produces the same dataset and
screenshots stay reproducible.
"""

from __future__ import annotations

import os
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import mysql.connector  # noqa: E402

from config import config  # noqa: E402

RANDOM_SEED = 20240815
rng = random.Random(RANDOM_SEED)

# Demo passwords. Fine for a local demo; the README says to change them
# before this is ever exposed to a network. Stored as plain text (see
# backend/security.py), so what is typed here is exactly what ends up in
# the database.
ADMIN_PASSWORD = "Admin@2024"
FACULTY_PASSWORD = "Faculty@2024"
STUDENT_PASSWORD = "Student@2024"

# users.email for the two staff accounts, so /api/auth/forgot-password
# has something to check for them. Students don't need one here - their
# email lives on the students row and forgot-password falls back to it.
ADMIN_EMAIL = "admin@foresight.local"
FACULTY_EMAIL = "faculty@foresight.local"

FIRST_NAMES = [
    "Aarav",
    "Ananya",
    "Arjun",
    "Diya",
    "Ishaan",
    "Kavya",
    "Rohan",
    "Meera",
    "Vivaan",
    "Sara",
    "Aditya",
    "Nisha",
    "Karan",
    "Pooja",
    "Rahul",
    "Sneha",
    "Vikram",
    "Tanya",
    "Aryan",
    "Riya",
    "Dev",
    "Anjali",
    "Kabir",
    "Neha",
    "Manav",
    "Shreya",
    "Yash",
    "Aditi",
    "Nikhil",
    "Prisha",
    "Siddharth",
    "Isha",
    "Om",
    "Lakshmi",
    "Harsh",
    "Divya",
    "Raj",
    "Simran",
    "Varun",
    "Kritika",
    "Aman",
    "Swara",
    "Tarun",
    "Ira",
    "Zain",
    "Naina",
]

LAST_NAMES = [
    "Sharma",
    "Verma",
    "Patel",
    "Reddy",
    "Nair",
    "Iyer",
    "Gupta",
    "Singh",
    "Kumar",
    "Joshi",
    "Mehta",
    "Desai",
    "Rao",
    "Chopra",
    "Bose",
    "Malhotra",
    "Kapoor",
    "Banerjee",
    "Pillai",
    "Shetty",
    "Bhat",
    "Menon",
]

# Student archetypes: (label, share of cohort, base mark %, attendance %,
# per-assessment drift). The drift is what the trend detector picks up.
PROFILES = [
    ("high", 0.24, (78, 94), (88, 98), 0.4),  # strong, slowly improving
    ("steady", 0.43, (61, 78), (79, 94), 0.0),  # solid, flat
    ("borderline", 0.19, (47, 60), (69, 85), -0.3),  # passing but slipping
    ("declining", 0.09, (53, 66), (62, 78), -2.2),  # clear downward trend
    ("at_risk", 0.05, (24, 38), (42, 63), -0.6),  # failing
]

ASSESSMENTS = [
    # (type, max marks, week of term it was held)
    ("quiz", 20, 3),
    ("assignment", 25, 5),
    ("midterm", 50, 8),
    ("quiz", 20, 11),
    ("final", 100, 15),
]

TERM_START = date.today() - timedelta(weeks=17)
CLASSES_PER_SUBJECT = 30


def connect():
    return mysql.connector.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        autocommit=False,
    )


def pick_profile() -> tuple:
    """Choose an archetype according to the configured shares."""
    roll = rng.random()
    cumulative = 0.0
    for profile in PROFILES:
        cumulative += profile[1]
        if roll <= cumulative:
            return profile
    return PROFILES[-1]


def make_name(used: set[str]) -> str:
    """A name not already taken, so roll numbers stay readable."""
    for _ in range(200):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name not in used:
            used.add(name)
            return name
    # Fall back to a numbered name rather than looping forever.
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} {len(used)}"
    used.add(name)
    return name


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def already_seeded(cur) -> int:
    """How many students are already in the database."""
    cur.execute("SELECT COUNT(*) AS n FROM students")
    return cur.fetchone()["n"]


def seed(force: bool = False) -> None:
    conn = connect()
    cur = conn.cursor(dictionary=True)

    # Refuse to destroy existing data unless explicitly told to.
    #
    # This matters most under Docker: `docker compose up` restarts the
    # seed container every time, and without this guard a student added
    # through the admin console would silently vanish on the next
    # restart. Skipping when data already exists makes `up` safe to run
    # repeatedly, while the first run still populates an empty database.
    existing = already_seeded(cur)
    if existing and not force:
        print(f"Database already has {existing} students - leaving it alone.")
        print("Re-seed from scratch with:  python seed_demo.py --force")
        cur.close()
        conn.close()
        return

    print("Seeding demo data...")

    # --- Wipe previously generated data ------------------------------
    # Ordered child-first. Reference data (branches, subjects) is left
    # alone because it comes from sample_data.sql, not from here.
    if existing:
        print(f"  --force: clearing {existing} existing students and their results")
    cur.execute("SET @app_user = 'seed_script'")
    for statement in (
        "DELETE FROM attendance_records",
        "DELETE FROM assessments",
        "DELETE FROM enrollments",
        "DELETE FROM users WHERE role = 'student'",
        "DELETE FROM students",
        "DELETE FROM users WHERE role IN ('admin','faculty')",
        "DELETE FROM audit_log",
        "DELETE FROM login_attempts",
    ):
        cur.execute(statement)

    # --- Staff accounts ----------------------------------------------
    cur.execute(
        "INSERT INTO users (username, password, email, role, must_change_pw) "
        "VALUES (%s, %s, %s, 'admin', FALSE)",
        ("admin", ADMIN_PASSWORD, ADMIN_EMAIL),
    )
    cur.execute(
        "INSERT INTO users (username, password, email, role, must_change_pw) "
        "VALUES (%s, %s, %s, 'faculty', FALSE)",
        ("faculty", FACULTY_PASSWORD, FACULTY_EMAIL),
    )
    print("  created admin and faculty logins")

    # --- Cohorts ------------------------------------------------------
    cur.execute("SELECT branch_id, code FROM branches ORDER BY branch_id")
    branches = {row["code"]: row["branch_id"] for row in cur.fetchall()}
    if not branches:
        raise SystemExit("No branches found. Load database/sample_data.sql first.")

    cur.execute("SELECT subject_id, code, branch_id, semester FROM subjects")
    subjects = cur.fetchall()

    cohorts = [
        ("CSE", 3, 24),
        ("CSE", 5, 18),
        ("AIML", 3, 20),
        ("ECE", 3, 16),
    ]

    used_names: set[str] = set()

    total_students = 0
    total_assessments = 0
    total_attendance = 0

    for branch_code, semester, count in cohorts:
        branch_id = branches.get(branch_code)
        if branch_id is None:
            continue

        cohort_subjects = [
            s
            for s in subjects
            if s["branch_id"] == branch_id and s["semester"] == semester
        ]
        if not cohort_subjects:
            print(f"  ! no subjects for {branch_code} sem {semester}, skipping")
            continue

        admission_year = date.today().year - (semester // 2)

        for index in range(1, count + 1):
            name = make_name(used_names)
            roll_no = f"{branch_code}{admission_year}{index:03d}"
            email = f"{name.split()[0].lower()}.{roll_no.lower()}@college.edu"

            cur.execute(
                """
                INSERT INTO students
                    (roll_no, name, email, branch_id, semester, admission_year)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (roll_no, name, email, branch_id, semester, admission_year),
            )
            student_id = cur.lastrowid
            total_students += 1

            cur.execute(
                """
                INSERT INTO users
                    (username, password, role, student_id, must_change_pw)
                VALUES (%s, %s, 'student', %s, FALSE)
                """,
                (roll_no.lower(), STUDENT_PASSWORD, student_id),
            )

            label, _, mark_range, attendance_range, drift = pick_profile()
            base_mark = rng.uniform(*mark_range)
            base_attendance = rng.uniform(*attendance_range)

            for subject in cohort_subjects:
                cur.execute(
                    """
                    INSERT INTO enrollments
                        (student_id, subject_id, academic_year)
                    VALUES (%s, %s, %s)
                    """,
                    (student_id, subject["subject_id"], admission_year),
                )
                enrollment_id = cur.lastrowid

                # Each subject sits a little either side of the student's
                # baseline, so a strong student can still have one weak
                # subject - which is what makes the per-subject
                # comparison chart interesting.
                subject_offset = rng.uniform(-9, 9)

                assessment_rows = []
                for order, (kind, max_marks, week) in enumerate(ASSESSMENTS):
                    assessed_on = TERM_START + timedelta(weeks=week)
                    if assessed_on > date.today():
                        continue

                    percent = clamp(
                        base_mark + subject_offset + drift * order * 3 + rng.gauss(0, 5),
                        3,
                        100,
                    )
                    obtained = round(max_marks * percent / 100, 2)
                    assessment_rows.append(
                        (enrollment_id, kind, obtained, max_marks, assessed_on)
                    )

                cur.executemany(
                    """
                    INSERT INTO assessments
                        (enrollment_id, type, marks_obtained, max_marks, assessed_on)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    assessment_rows,
                )
                total_assessments += len(assessment_rows)

                # Daily attendance, two classes a week.
                attendance_rows = []
                for session in range(CLASSES_PER_SUBJECT):
                    class_date = TERM_START + timedelta(days=session * 3)
                    if class_date > date.today():
                        break

                    draw = rng.uniform(0, 100)
                    if draw < base_attendance:
                        status = "present"
                    elif draw < base_attendance + 6:
                        status = "late"
                    elif draw < base_attendance + 9:
                        status = "excused"
                    else:
                        status = "absent"

                    attendance_rows.append((enrollment_id, class_date, status))

                cur.executemany(
                    """
                    INSERT INTO attendance_records
                        (enrollment_id, class_date, status)
                    VALUES (%s, %s, %s)
                    """,
                    attendance_rows,
                )
                total_attendance += len(attendance_rows)

        print(f"  {branch_code} semester {semester}: {count} students")

    conn.commit()

    # --- Summary ------------------------------------------------------
    cur.execute("SELECT COUNT(*) AS n FROM v_at_risk_students WHERE risk_band = 'high'")
    high_risk = cur.fetchone()["n"]
    cur.execute("SELECT ROUND(AVG(avg_mark_percent), 1) AS avg FROM v_student_overall")
    average = cur.fetchone()["avg"]

    # Read a real roll number back out rather than reconstructing one -
    # the generated pattern depends on the current year, so a printed
    # example built by hand would drift out of date.
    cur.execute(
        "SELECT username FROM users WHERE role = 'student' ORDER BY user_id LIMIT 1"
    )
    row = cur.fetchone()
    example_login = row["username"] if row else "<roll_no>"

    cur.close()
    conn.close()

    print()
    print(f"  {total_students} students")
    print(f"  {total_assessments} assessments")
    print(f"  {total_attendance} attendance records")
    print(f"  class average {average}%, {high_risk} students flagged high risk")
    print()
    print("Sign in with:")
    print(f"  admin              / {ADMIN_PASSWORD}")
    print(f"  faculty            / {FACULTY_PASSWORD}")
    print(f"  {example_login:18} / {STUDENT_PASSWORD}   (any roll number works)")
    print()
    print("Change these before exposing the app to a network.")


def wait_for_database(attempts: int = 30, delay: float = 2.0) -> None:
    """Block until MySQL accepts connections.

    Only needed under Docker. Compose waits for the database's
    healthcheck, but "accepting connections" and "finished running the
    scripts in docker-entrypoint-initdb.d" are not the same moment - the
    server answers a ping while the schema is still being created. So
    this waits for a table this script actually needs, not just a socket.
    """
    for attempt in range(1, attempts + 1):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM branches")
            cur.fetchall()
            cur.close()
            conn.close()
            return
        except mysql.connector.Error as exc:
            if attempt == attempts:
                raise
            print(f"  waiting for database ({attempt}/{attempts}): {exc.msg}")
            time.sleep(delay)


if __name__ == "__main__":
    force = "--force" in sys.argv or os.getenv("SEED_FORCE") == "1"

    try:
        # Harmless locally (the database is already up, so this returns
        # immediately); essential in Compose, where this container starts
        # the moment MySQL answers its first ping.
        wait_for_database()
        seed(force=force)
    except mysql.connector.Error as exc:
        raise SystemExit(
            f"\nDatabase error: {exc}\n\n"
            "Check that MySQL is running and that database/schema.sql,\n"
            "views.sql, triggers.sql, procedures.sql and sample_data.sql\n"
            "have all been loaded."
        )
