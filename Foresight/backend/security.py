"""Authentication, authorisation and password handling.

This module replaces the weakest part of the original project. Before:

  * `/login` returned a role and the front end saved it to localStorage,
    which the browser console can edit - typing
    `localStorage.role = 'admin'` was a complete privilege escalation;
  * no endpoint checked *anything*, so `GET /student-data/7` returned
    student 7's marks to whoever asked.

Now:

  * a successful login returns a signed JWT, and the signature means a
    tampered role or student id fails verification;
  * every protected route declares who may call it via a decorator, and
    a student's own id is read from the *token*, never from the URL.

Passwords are stored as plain text (see the `password` column on
`users`, and `verify_password` below). That is a deliberate choice for
this build - it is run as a personal admin tool, and the owner needs to
read a student's password back directly rather than only ever issuing a
new one. It is a real trade-off: anyone who can read the `users` table
reads every password with it. Comparisons still go through
`hmac.compare_digest`, which costs nothing and closes the one side
channel (timing) that storage format does not affect either way.
"""

from __future__ import annotations

import functools
import hmac
import logging
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from flask import g, request

import db
from config import config
from errors import forbidden, too_many_requests, unauthorized

log = logging.getLogger(__name__)

# Roles that exist, most privileged first. Used by require_role().
ROLES = ("admin", "faculty", "student")


# ---------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------
# Stored and compared as plain text by design - see the module docstring.


def verify_password(plain: str, stored: str) -> bool:
    """Check a password against the one on file.

    `hmac.compare_digest` takes the same time regardless of where the
    two strings first differ, so a failed attempt cannot be used to
    guess the password one character at a time by timing the response.
    """
    if not stored:
        return False
    return hmac.compare_digest(plain, stored)


# Password policy. Deliberately stated as data rather than one dense
# regex, so a failed check can tell the user exactly what is missing
# instead of just "invalid password".
PASSWORD_MIN_LENGTH = 8

_PASSWORD_RULES = (
    (
        lambda p: len(p) >= PASSWORD_MIN_LENGTH,
        f"at least {PASSWORD_MIN_LENGTH} characters",
    ),
    (lambda p: any(c.isupper() for c in p), "an uppercase letter"),
    (lambda p: any(c.islower() for c in p), "a lowercase letter"),
    (lambda p: any(c.isdigit() for c in p), "a number"),
    (lambda p: any(not c.isalnum() for c in p), "a special character"),
)


def password_problems(plain: str) -> list[str]:
    """Return the list of requirements a password fails to meet.

    Empty list means the password is acceptable.
    """
    return [why for rule, why in _PASSWORD_RULES if not rule(plain)]


# ---------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------


def issue_token(user: dict) -> tuple[str, datetime]:
    """Create a signed JWT for a user row. Returns (token, expiry).

    The payload holds only what authorisation decisions need. Notably it
    carries `student_id`, so a student's own record is identified by the
    signed token rather than by a number in the URL that anyone can edit.
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=config.jwt_ttl_minutes)
    payload = {
        "sub": str(user["user_id"]),
        "username": user["username"],
        "role": user["role"],
        "student_id": user.get("student_id"),
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict:
    """Verify a JWT and return its payload, or raise 401.

    `jwt.decode` verifies the signature *and* the expiry. A token whose
    role was edited fails the signature check, because the attacker
    cannot re-sign without the server's secret.
    """
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise unauthorized("Your session has expired, please sign in again")
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid authentication token")


def _token_from_request() -> str | None:
    """Pull the bearer token out of the Authorization header."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip() or None
    return None


# ---------------------------------------------------------------------
# Route decorators
# ---------------------------------------------------------------------


def require_auth(fn):
    """Reject the request unless it carries a valid token.

    On success the decoded payload is put on `g.user`, so handlers can
    read `g.user["student_id"]` without decoding anything themselves.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = _token_from_request()
        if not token:
            raise unauthorized("Missing Authorization header")

        g.user = decode_token(token)
        # Let the audit triggers attribute writes to this user.
        db.set_actor(g.user.get("username"))
        return fn(*args, **kwargs)

    return wrapper


def require_role(*allowed: str):
    """Restrict a route to particular roles.

    Usage:
        @require_role("admin")
        @require_role("admin", "faculty")

    Implies require_auth, so routes only need one decorator.
    """
    unknown = set(allowed) - set(ROLES)
    if unknown:
        raise ValueError(f"unknown role(s) in require_role: {sorted(unknown)}")

    def decorator(fn):
        @functools.wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            if g.user.get("role") not in allowed:
                log.warning(
                    "role check failed: %s (role=%s) tried %s",
                    g.user.get("username"),
                    g.user.get("role"),
                    request.path,
                )
                raise forbidden(f"This action requires one of: {', '.join(allowed)}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_self_or_staff(student_id: int) -> None:
    """Allow access only to that student, or to staff.

    Call this from any route that takes a student id in the URL. It is
    the fix for the original project's worst bug: a student changing the
    number in the URL and reading a classmate's marks.
    """
    user = g.get("user")
    if not user:
        raise unauthorized()

    if user.get("role") in ("admin", "faculty"):
        return

    if user.get("student_id") != student_id:
        log.warning(
            "IDOR attempt: %s (student %s) requested student %s",
            user.get("username"),
            user.get("student_id"),
            student_id,
        )
        raise forbidden("You can only view your own records")


# ---------------------------------------------------------------------
# Login rate limiting
# ---------------------------------------------------------------------
# Two layers, on purpose:
#
#   * an in-process counter, which is instant and costs no query;
#   * a row in `login_attempts`, which survives a restart and gives the
#     audit log something to show.
#
# The in-memory half is a dict of deques keyed by username+IP. It is not
# shared between worker processes, so a multi-process deployment would
# want Redis here - but for a single-process app it is exactly right, and
# the database half is the durable backstop either way.

_attempts: dict[str, deque[float]] = defaultdict(deque)


def _prune(bucket: deque[float], window: int) -> None:
    """Drop attempts that have aged out of the window."""
    cutoff = time.monotonic() - window
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def check_login_rate(username: str) -> None:
    """Raise 429 if this user/IP has failed too many times recently."""
    key = f"{username}|{request.remote_addr}"
    bucket = _attempts[key]
    _prune(bucket, config.login_window_seconds)

    if len(bucket) >= config.login_max_attempts:
        retry_after = int(config.login_window_seconds - (time.monotonic() - bucket[0]))
        raise too_many_requests(
            f"Too many failed sign-in attempts. Try again in "
            f"{max(retry_after, 1)} seconds.",
            retry_after=max(retry_after, 1),
        )


def record_login_attempt(username: str, succeeded: bool) -> None:
    """Record the outcome of a login, in memory and in the database."""
    key = f"{username}|{request.remote_addr}"
    if succeeded:
        # A correct password clears the user's failure streak.
        _attempts.pop(key, None)
    else:
        _attempts[key].append(time.monotonic())

    db.execute(
        "INSERT INTO login_attempts (username, ip_address, succeeded) "
        "VALUES (%s, %s, %s)",
        (username[:50], request.remote_addr, succeeded),
    )


def reset_rate_limits() -> None:
    """Clear the in-memory counters. Used by the test suite."""
    _attempts.clear()
