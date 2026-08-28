"""Authentication routes: sign in, view profile, change password.

Two ways to recover a lost password:

  * `/change-password` - signed in, requires the current password.
  * `/forgot-password` - not signed in, requires the username and the
    email on file for that account to match. That is deliberately more
    than the very first version of this project had: it accepted a bare
    username and changed the password for anyone who typed one in,
    which is a full account takeover with no proof of ownership at all.
    Checking the email is not perfect - anyone who already knows both
    the username and the registered email can still reset it - but it
    is not "type any name, own any account" either, and it is rate
    limited the same way login is.

An administrator can also reset any account from the admin console
(`/api/admin/students/<id>/reset-password`), which does not require
knowing the email - that is what the admin role is for.
"""

from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify

import db
from errors import bad_request, unauthorized
from security import (
    check_login_rate,
    issue_token,
    password_problems,
    record_login_attempt,
    require_auth,
    verify_password,
)
from validators import json_body, require_email, require_str

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    """Exchange a username-or-email and password for a JWT."""
    data = json_body()
    # `max_len` allows for an email address, which is longer than the
    # 50-character username column.
    identifier = require_str(data, "username", max_len=150).lower()
    password = require_str(data, "password", max_len=200, strip=False)

    # Checked before touching the database so a flood of guesses cannot
    # be used to hammer it.
    check_login_rate(identifier)

    # Sign-in accepts either the username or the email address on file.
    # The users table stores both, so someone who has only ever seen
    # their email will naturally try it; refusing that is a support
    # question, not security.
    #
    # A student's address lives on `students`, staff addresses on
    # `users`, hence the COALESCE - the same rule the password-reset
    # route uses, so the two cannot disagree about what identifies an
    # account.
    #
    # ORDER BY makes the result deterministic: were a username ever to
    # equal another account's email, the exact username match wins
    # rather than the row order deciding who signs in.
    user = db.query_one(
        """
        SELECT u.user_id, u.username, u.password, u.role,
               u.student_id, u.is_active, u.must_change_pw,
               s.name AS student_name
        FROM users u
        LEFT JOIN students s ON s.student_id = u.student_id
        WHERE LOWER(u.username) = %s
           OR LOWER(COALESCE(u.email, s.email)) = %s
        ORDER BY (LOWER(u.username) = %s) DESC
        LIMIT 1
        """,
        (identifier, identifier, identifier),
    )

    # `verify_password` is still called when the user does not exist, so
    # that a missing account and a wrong password take the same amount of
    # time. Returning early on "no such user" would let an attacker map
    # valid usernames by timing the responses.
    stored = user["password"] if user else ""
    password_ok = verify_password(password, stored)

    # Rate limiting is also applied to the account's canonical username.
    # Without this, the two ways of naming one account would each get
    # their own budget, doubling the attempts available to a guesser.
    if user and user["username"].lower() != identifier:
        check_login_rate(user["username"].lower())

    if not user or not password_ok or not user["is_active"]:
        record_login_attempt(identifier, succeeded=False)
        if user and user["username"].lower() != identifier:
            record_login_attempt(user["username"].lower(), succeeded=False)
        db.commit()
        # One message for every failure mode - "no such user" would
        # confirm which usernames exist.
        raise unauthorized("Incorrect username or password")

    record_login_attempt(identifier, succeeded=True)
    if user["username"].lower() != identifier:
        record_login_attempt(user["username"].lower(), succeeded=True)

    db.execute(
        "UPDATE users SET last_login_at = NOW() WHERE user_id = %s",
        (user["user_id"],),
    )
    db.set_actor(user["username"])
    db.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, ip_address) "
        "VALUES (%s, 'login.success', 'user', %s, %s)",
        (user["username"], user["user_id"], _client_ip()),
    )
    db.commit()

    token, expires_at = issue_token(user)
    log.info("login ok: %s (%s)", user["username"], user["role"])

    return jsonify(
        {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user["role"],
                "student_id": user["student_id"],
                "name": user["student_name"] or user["username"],
                "must_change_password": bool(user["must_change_pw"]),
            },
        }
    )


@bp.get("/me")
@require_auth
def me():
    """Return the signed-in user, for restoring a session on page load.

    The front end calls this on startup instead of trusting whatever it
    stored in localStorage: if the token has expired or been revoked, the
    401 from here is what tells it to show the login screen again.
    """
    user = db.query_one(
        """
        SELECT u.user_id, u.username, u.role, u.student_id, u.must_change_pw,
               u.last_login_at, s.name AS student_name, s.roll_no,
               s.semester, b.code AS branch_code
        FROM users u
        LEFT JOIN students s  ON s.student_id = u.student_id
        LEFT JOIN branches b  ON b.branch_id  = s.branch_id
        WHERE u.user_id = %s AND u.is_active = TRUE
        """,
        (g.user["sub"],),
    )
    if not user:
        raise unauthorized("Account no longer exists")

    return jsonify(
        {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "student_id": user["student_id"],
            "name": user["student_name"] or user["username"],
            "roll_no": user["roll_no"],
            "branch": user["branch_code"],
            "semester": user["semester"],
            "must_change_password": bool(user["must_change_pw"]),
            # Passed through as a datetime, not a pre-formatted string, so
            # the JSON provider can stamp the UTC offset on it.
            "last_login_at": user["last_login_at"],
        }
    )


@bp.post("/change-password")
@require_auth
def change_password():
    """Change the signed-in user's own password.

    Requires the current password.
    """
    data = json_body()
    current = require_str(data, "current_password", max_len=200, strip=False)
    new_password = require_str(data, "new_password", max_len=200, strip=False)

    user = db.query_one(
        "SELECT user_id, username, password FROM users WHERE user_id = %s",
        (g.user["sub"],),
    )
    if not user or not verify_password(current, user["password"]):
        raise unauthorized("Current password is incorrect")

    if current == new_password:
        raise bad_request("New password must be different from the current one")

    problems = password_problems(new_password)
    if problems:
        raise bad_request("Password needs " + ", ".join(problems))

    db.execute(
        "UPDATE users SET password = %s, must_change_pw = FALSE WHERE user_id = %s",
        (new_password, user["user_id"]),
    )
    db.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, ip_address) "
        "VALUES (%s, 'password.change', 'user', %s, %s)",
        (user["username"], user["user_id"], _client_ip()),
    )
    db.commit()

    return jsonify({"message": "Password updated successfully"})


@bp.post("/forgot-password")
def forgot_password():
    """Self-service password reset, for a user who is not signed in.

    Requires the username and the email on file to match before a new
    password is accepted. Admin and faculty accounts carry their own
    `users.email`; a student account has none of its own and falls back
    to the email on their linked `students` row.

    Rejected the same way whether the username does not exist or the
    email does not match it, and rate limited on the same budget as
    `/login` - both are what stop this from being "type any username,
    take the account".
    """
    data = json_body()
    username = require_str(data, "username", max_len=50).lower()
    email = require_email(data)
    new_password = require_str(data, "new_password", max_len=200, strip=False)

    check_login_rate(username)

    user = db.query_one(
        """
        SELECT u.user_id, u.username,
               COALESCE(u.email, s.email) AS email_on_file
        FROM users u
        LEFT JOIN students s ON s.student_id = u.student_id
        WHERE LOWER(u.username) = %s AND u.is_active = TRUE
        """,
        (username,),
    )

    email_matches = bool(
        user and user["email_on_file"] and user["email_on_file"].lower() == email
    )

    if not user or not email_matches:
        record_login_attempt(username, succeeded=False)
        db.commit()
        raise unauthorized("No account matches that username and email")

    record_login_attempt(username, succeeded=True)

    problems = password_problems(new_password)
    if problems:
        raise bad_request("Password needs " + ", ".join(problems))

    db.execute(
        "UPDATE users SET password = %s, must_change_pw = FALSE WHERE user_id = %s",
        (new_password, user["user_id"]),
    )
    db.set_actor(user["username"])
    db.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, ip_address) "
        "VALUES (%s, 'password.self_reset', 'user', %s, %s)",
        (user["username"], user["user_id"], _client_ip()),
    )
    db.commit()
    log.info("self-service password reset: %s", user["username"])

    return jsonify({"message": "Password updated. You can sign in with it now."})


@bp.get("/password-policy")
def password_policy():
    """Publish the password rules so the UI can show them live.

    Keeping the rules in one place means the checklist the user sees
    while typing cannot disagree with what the server will accept.
    """
    from security import PASSWORD_MIN_LENGTH

    return jsonify(
        {
            "min_length": PASSWORD_MIN_LENGTH,
            "requirements": [
                f"At least {PASSWORD_MIN_LENGTH} characters",
                "An uppercase letter",
                "A lowercase letter",
                "A number",
                "A special character",
            ],
        }
    )


def _client_ip() -> str | None:
    from flask import request

    return request.remote_addr
