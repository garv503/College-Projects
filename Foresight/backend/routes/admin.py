"""Administrative routes: student management, bulk import, audit log.

Every route in this blueprint is gated by `@require_role("admin")` or
`("admin", "faculty")`. Serving an admin page is not protection in
itself - anyone can type its URL - so the guard sits on the API.
"""

from __future__ import annotations

import json
import logging
import secrets
import string
from datetime import date

from flask import Blueprint, Response, g, jsonify, request

import db
from errors import bad_request, conflict, not_found
from security import require_role
from services import analytics, imports, reports
from validators import (
    json_body,
    pagination,
    query_int,
    require_email,
    require_int,
    require_roll_no,
    require_str,
)

log = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB is ample for a few thousand CSV rows


# ---------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------


@bp.post("/students")
@require_role("admin")
def create_student():
    """Create a student, their login, and their subject enrollments.

    The username is derived from the roll number rather than the name,
    because roll numbers are unique by definition and two students can
    share a name.

    The initial password is randomly generated rather than derived from
    the student's details. It is stored as plain text by design (see
    backend/security.py) and can be read back later from
    GET /students/<id>/credentials.

    Enrollment happens through the `sp_enroll_student` procedure, so the
    student row, the login and every enrollment either all commit or all
    roll back.
    """
    data = json_body()

    name = require_str(data, "name", min_len=2, max_len=100)
    roll_no = require_roll_no(data)
    email = require_email(data)
    branch_id = require_int(data, "branch_id", minimum=1)
    semester = require_int(data, "semester", minimum=1, maximum=8)
    admission_year = require_int(data, "admission_year", minimum=2000, maximum=2100)

    branch = db.query_one(
        "SELECT branch_id, code FROM branches WHERE branch_id = %s", (branch_id,)
    )
    if not branch:
        raise bad_request(f"No branch with id {branch_id}")

    # Checked explicitly so the user gets "that roll number is taken"
    # rather than a driver-level duplicate-key error.
    if db.query_one("SELECT 1 FROM students WHERE roll_no = %s", (roll_no,)):
        raise conflict(f"Roll number {roll_no} already exists")
    if db.query_one("SELECT 1 FROM students WHERE email = %s", (email,)):
        raise conflict(f"Email {email} is already registered")

    student_id = db.execute(
        """
        INSERT INTO students
            (roll_no, name, email, branch_id, semester, admission_year)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (roll_no, name, email, branch_id, semester, admission_year),
    )

    username = roll_no.lower()
    if db.query_one("SELECT 1 FROM users WHERE username = %s", (username,)):
        raise conflict(f"Username {username} is already taken")

    # `users.email` is left NULL here on purpose. This is a student
    # account, and `forgot_password()` already falls back to the linked
    # `students.email` via COALESCE - duplicating it into users.email
    # would give the email two sources of truth that could drift apart
    # the moment someone edits it in one place and not the other.
    password = _generate_password()
    db.execute(
        """
        INSERT INTO users
            (username, password, role, student_id, must_change_pw)
        VALUES (%s, %s, 'student', %s, TRUE)
        """,
        (username, password, student_id),
    )

    # Enroll into every subject for the branch + semester.
    out = db.call_proc_out("sp_enroll_student", (student_id, admission_year, 0))
    enrolled = out[2] if len(out) > 2 else 0

    db.commit()
    log.info("student created: %s (%s) by %s", roll_no, name, g.user["username"])

    return (
        jsonify(
            {
                "student_id": student_id,
                "roll_no": roll_no,
                "name": name,
                "subjects_enrolled": enrolled,
                "credentials": {
                    "username": username,
                    "password": password,
                    "note": (
                        "You can look this up again later from the "
                        "student's row in the admin console."
                    ),
                },
            }
        ),
        201,
    )


@bp.patch("/students/<int:student_id>")
@require_role("admin")
def update_student(student_id: int):
    """Update a student's editable fields. Logged by a trigger."""
    data = json_body()

    student = db.query_one(
        "SELECT student_id FROM students WHERE student_id = %s", (student_id,)
    )
    if not student:
        raise not_found(f"No student with id {student_id}")

    updates: list[str] = []
    params: list = []

    if "name" in data:
        updates.append("name = %s")
        params.append(require_str(data, "name", min_len=2, max_len=100))
    if "email" in data:
        updates.append("email = %s")
        params.append(require_email(data))
    if "semester" in data:
        updates.append("semester = %s")
        params.append(require_int(data, "semester", minimum=1, maximum=8))
    if "branch_id" in data:
        updates.append("branch_id = %s")
        params.append(require_int(data, "branch_id", minimum=1))
    if "is_active" in data:
        updates.append("is_active = %s")
        params.append(bool(data["is_active"]))

    if not updates:
        raise bad_request(
            "Nothing to update. Send at least one of: name, email, "
            "semester, branch_id, is_active"
        )

    params.append(student_id)
    db.execute(
        f"UPDATE students SET {', '.join(updates)} WHERE student_id = %s",
        params,
    )
    db.commit()
    return jsonify({"message": "Student updated", "student_id": student_id})


@bp.delete("/students/<int:student_id>")
@require_role("admin")
def deactivate_student(student_id: int):
    """Deactivate a student.

    A soft delete, not a DELETE. Removing the row would cascade away
    their marks and attendance, destroying the historical record that the
    cohort statistics are built from.
    """
    affected = db.execute(
        "UPDATE students SET is_active = FALSE WHERE student_id = %s AND is_active = TRUE",
        (student_id,),
    )
    if not affected:
        raise not_found(f"No active student with id {student_id}")
    db.commit()
    return jsonify({"message": "Student deactivated", "student_id": student_id})


@bp.post("/students/<int:student_id>/reset-password")
@require_role("admin")
def reset_student_password(student_id: int):
    """Issue a new random password for a student who is locked out."""
    user = db.query_one(
        "SELECT user_id, username FROM users WHERE student_id = %s", (student_id,)
    )
    if not user:
        raise not_found(f"No login account for student {student_id}")

    password = _generate_password()
    db.execute(
        "UPDATE users SET password = %s, must_change_pw = TRUE WHERE user_id = %s",
        (password, user["user_id"]),
    )
    db.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, details) "
        "VALUES (%s, 'password.admin_reset', 'user', %s, %s)",
        (
            g.user["username"],
            user["user_id"],
            json.dumps({"target_username": user["username"]}),
        ),
    )
    db.commit()

    return jsonify(
        {
            "message": "Password reset",
            "username": user["username"],
            "password": password,
        }
    )


@bp.get("/students/<int:student_id>/credentials")
@require_role("admin")
def student_credentials(student_id: int):
    """Look up a student's current username and password.

    Passwords are stored as plain text in this build (see
    backend/security.py), which is what makes this endpoint possible at
    all - with a hashed password there would be nothing to return. It
    exists because the admin console is meant to be usable as a day-to-day
    lookup, not just a one-time reveal at creation time.
    """
    user = db.query_one(
        "SELECT username, password FROM users WHERE student_id = %s",
        (student_id,),
    )
    if not user:
        raise not_found(f"No login account for student {student_id}")

    # Every password read is recorded, and this is not bookkeeping - it is
    # the control that makes plaintext storage defensible at all.
    #
    # Hashing prevents a password from being read. Storing it in the clear
    # gives that up by design here, so the remaining protection is that
    # nobody can read one *anonymously*: the row below names the admin,
    # the student, the time and the IP. Without it this endpoint would be
    # a silent, untraceable way to obtain any student's credentials.
    #
    # The password itself is deliberately NOT written into `details` - the
    # audit log records that a lookup happened, never the secret.
    db.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, details, ip_address) "
        "VALUES (%s, 'password.viewed', 'user', %s, %s, %s)",
        (
            g.user["username"],
            student_id,
            json.dumps({"target_username": user["username"]}),
            request.remote_addr,
        ),
    )
    db.commit()

    log.warning(
        "password viewed: %s looked up credentials for student %s",
        g.user["username"],
        student_id,
    )

    return jsonify({"username": user["username"], "password": user["password"]})


# ---------------------------------------------------------------------
# Marks entry
# ---------------------------------------------------------------------


@bp.post("/assessments")
@require_role("admin", "faculty")
def record_assessment():
    """Record or correct a single assessment mark.

    Delegates to `sp_record_assessment`, which resolves the enrollment
    and does an insert-or-update in one transaction.
    """
    data = json_body()

    student_id = require_int(data, "student_id", minimum=1)
    subject_id = require_int(data, "subject_id", minimum=1)
    assessment_type = require_str(data, "type").lower()
    if assessment_type not in imports.ASSESSMENT_TYPES:
        raise bad_request(
            f"type must be one of: {', '.join(sorted(imports.ASSESSMENT_TYPES))}"
        )

    max_marks = float(data.get("max_marks", 100))
    if max_marks <= 0 or max_marks > 200:
        raise bad_request("max_marks must be between 1 and 200")

    obtained = float(data.get("marks_obtained", -1))
    if obtained < 0:
        raise bad_request("marks_obtained is required and cannot be negative")
    if obtained > max_marks:
        raise bad_request(
            f"marks_obtained ({obtained:g}) cannot exceed max_marks ({max_marks:g})"
        )

    assessed_on = data.get("assessed_on") or date.today().isoformat()

    db.call_proc(
        "sp_record_assessment",
        (student_id, subject_id, assessment_type, obtained, max_marks, assessed_on),
    )
    db.commit()
    return jsonify({"message": "Assessment recorded"}), 201


# ---------------------------------------------------------------------
# Bulk import / export
# ---------------------------------------------------------------------


@bp.post("/import/marks")
@require_role("admin", "faculty")
def import_marks():
    """Bulk-import marks from an uploaded CSV."""
    raw = _read_upload()
    result = imports.import_marks(raw)

    if not result.ok:
        # 422: the file parsed fine but its contents are not acceptable.
        # Nothing was written - the importer validates the whole file
        # before touching the database.
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_rows",
                        "message": f"{len(result.errors)} row(s) rejected. Nothing was imported.",
                        "details": result.to_dict(),
                    }
                }
            ),
            422,
        )

    db.execute(
        "INSERT INTO audit_log (actor, action, entity, details) "
        "VALUES (%s, 'import.marks', 'assessment', %s)",
        (g.user["username"], json.dumps({"rows": result.imported})),
    )
    db.commit()
    return jsonify(result.to_dict())


@bp.post("/import/attendance")
@require_role("admin", "faculty")
def import_attendance():
    """Bulk-import attendance from an uploaded CSV."""
    raw = _read_upload()
    result = imports.import_attendance(raw)

    if not result.ok:
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_rows",
                        "message": f"{len(result.errors)} row(s) rejected. Nothing was imported.",
                        "details": result.to_dict(),
                    }
                }
            ),
            422,
        )

    db.execute(
        "INSERT INTO audit_log (actor, action, entity, details) "
        "VALUES (%s, 'import.attendance', 'attendance', %s)",
        (g.user["username"], json.dumps({"rows": result.imported})),
    )
    db.commit()
    return jsonify(result.to_dict())


@bp.get("/import/template.csv")
@require_role("admin", "faculty")
def marks_template():
    """Download a pre-filled CSV template for the marks importer."""
    filename, body = reports.marks_template_csv()
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.get("/export/cohort.csv")
@require_role("admin", "faculty")
def export_cohort():
    """Download the cohort summary as CSV."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None
    filename, body = reports.cohort_csv(branch_id, semester)
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------


@bp.get("/audit-log")
@require_role("admin")
def audit_log():
    """Paginated audit trail.

    Most entries here are written by database triggers rather than by
    this application, which is what makes the log trustworthy: a change
    made directly in a SQL client is recorded too.
    """
    page, per_page, offset = pagination()
    action = request.args.get("action", "").strip() or None

    total = db.query_value(
        "SELECT COUNT(*) FROM audit_log WHERE (%s IS NULL OR action = %s)",
        (action, action),
        default=0,
    )
    rows = db.query_all(
        """
        SELECT log_id, actor, action, entity, entity_id, details,
               ip_address, created_at
        FROM audit_log
        WHERE (%s IS NULL OR action = %s)
        ORDER BY created_at DESC, log_id DESC
        LIMIT %s OFFSET %s
        """,
        (action, action, per_page, offset),
    )

    # `created_at` is deliberately left as a datetime object. Calling
    # .isoformat() here would hand jsonify a *string*, which the JSON
    # provider then passes through untouched - losing the UTC offset it
    # exists to add. Naive timestamps are read by the browser as local
    # time, so the audit log showed every entry hours adrift.
    return jsonify(
        {
            "entries": rows,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if total else 0,
            },
        }
    )


# ---------------------------------------------------------------------
# Cohort operations
# ---------------------------------------------------------------------


@bp.post("/cohorts/promote")
@require_role("admin")
def promote_cohort():
    """Promote a branch/semester to the next semester.

    Students carrying two or more backlogs are held back, which is why
    this calls a procedure rather than issuing a bare UPDATE.
    """
    data = json_body()
    branch_id = require_int(data, "branch_id", minimum=1)
    semester = require_int(data, "semester", minimum=1, maximum=7)

    out = db.call_proc_out("sp_promote_semester", (branch_id, semester, 0, 0))
    db.commit()

    return jsonify(
        {
            "message": "Cohort promoted",
            "promoted": out[2] if len(out) > 2 else 0,
            "held_back": out[3] if len(out) > 3 else 0,
        }
    )


@bp.get("/overview")
@require_role("admin", "faculty")
def admin_overview():
    """Everything the admin dashboard needs in one call."""
    branch_id = query_int("branch_id", 0) or None
    semester = query_int("semester", 0) or None

    return jsonify(
        {
            "summary": analytics.get_cohort_summary(branch_id, semester),
            "grade_distribution": analytics.get_grade_distribution(branch_id, semester),
            "subject_stats": analytics.get_subject_statistics(branch_id, semester),
            "at_risk": analytics.get_at_risk_students(branch_id, semester, limit=10),
        }
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _read_upload() -> bytes:
    """Pull the uploaded file out of the request, with size limits."""
    if "file" not in request.files:
        raise bad_request("No file uploaded. Send it as multipart field 'file'.")

    upload = request.files["file"]
    if not upload.filename:
        raise bad_request("Uploaded file has no name")
    if not upload.filename.lower().endswith(".csv"):
        raise bad_request("Only .csv files are accepted")

    raw = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise bad_request(f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not raw:
        raise bad_request("Uploaded file is empty")
    return raw


def _generate_password(length: int = 12) -> str:
    """Generate a random initial password.

    Uses `secrets`, not `random`: `random` is a Mersenne Twister seeded
    predictably enough that generated passwords could be reproduced.

    Built by picking one character from each required class and filling
    the rest at random, so the result always satisfies the password
    policy rather than being regenerated until it happens to.
    """
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%*?&"

    required = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    pool = lower + upper + digits + symbols
    rest = [secrets.choice(pool) for _ in range(length - len(required))]

    chars = required + rest
    # Shuffle so the required characters are not always in the same
    # positions, which would shrink the effective search space.
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
