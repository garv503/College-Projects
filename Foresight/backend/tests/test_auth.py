"""Authentication: login, tokens, password rules, rate limiting."""

from __future__ import annotations

from datetime import UTC

import jwt
import pytest
from conftest import auth_header, login

from config import config
from security import password_problems, verify_password

# --- Password storage ---------------------------------------------------
# Passwords are stored as plain text in this build - a deliberate choice
# (see backend/security.py) so the owner can read one back rather than
# only ever issuing a new one. These tests assert that behaviour exactly,
# rather than asserting nothing and leaving the choice undocumented.


def test_password_is_stored_exactly_as_set(seeded, db_conn):
    """What was inserted is what is on file - no hashing step in between."""
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT username, password FROM users")
    rows = cur.fetchall()
    cur.close()

    assert rows, "expected seeded users"
    for row in rows:
        assert row["password"] == seeded["password"]


def test_verify_password_round_trip():
    assert verify_password("Correct@123", "Correct@123")
    assert not verify_password("correct@123", "Correct@123")  # case matters
    assert not verify_password("", "Correct@123")
    assert not verify_password("Correct@123", "")  # nothing on file


# --- Login -------------------------------------------------------------


def test_login_succeeds_with_valid_credentials(client, seeded):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": seeded["password"]},
    )
    assert response.status_code == 200

    body = response.get_json()
    assert body["user"]["role"] == "admin"
    assert body["token"]
    # The password must never be echoed back, in any form.
    assert seeded["password"] not in response.get_data(as_text=True)


def test_login_rejects_wrong_password(client, seeded):
    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "WrongPass@1"}
    )
    assert response.status_code == 401


def test_login_is_case_insensitive_on_username(client, seeded):
    response = client.post(
        "/api/auth/login", json={"username": "ADMIN", "password": seeded["password"]}
    )
    assert response.status_code == 200


def test_login_does_not_reveal_whether_a_username_exists(client, seeded):
    """Both failures must return the same status and message, or an
    attacker can enumerate valid usernames by comparing responses."""
    missing = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "Whatever@1"}
    )
    wrong = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Whatever@1"}
    )

    assert missing.status_code == wrong.status_code == 401
    assert missing.get_json()["error"]["message"] == wrong.get_json()["error"]["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "admin"},
        {"password": "x"},
        {"username": None, "password": None},
        {"username": 12345, "password": True},
        {"username": "", "password": ""},
    ],
)
def test_malformed_login_returns_400_not_500(client, seeded, payload):
    """The original code did `data.get('username').strip()`, which raised
    AttributeError - a 500 - on every one of these."""
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 400, response.get_data(as_text=True)


def test_login_with_non_json_body_returns_400(client, seeded):
    response = client.post(
        "/api/auth/login", data="not json", content_type="application/json"
    )
    assert response.status_code == 400


def test_inactive_account_cannot_sign_in(client, seeded, db_conn):
    cur = db_conn.cursor()
    cur.execute("UPDATE users SET is_active = FALSE WHERE username = 'cse2023001'")
    cur.close()

    response = client.post(
        "/api/auth/login",
        json={"username": "cse2023001", "password": seeded["password"]},
    )
    assert response.status_code == 401


# --- Tokens ------------------------------------------------------------


def test_token_carries_role_and_student_id(client, seeded):
    token = login(client, "cse2023001", seeded["password"])
    payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])

    assert payload["role"] == "student"
    assert payload["student_id"] == seeded["students"]["CSE2023001"]
    assert "exp" in payload


def test_tampered_token_is_rejected(client, seeded):
    """Editing the payload breaks the signature. This is why the role can
    live in the token at all - unlike localStorage, it cannot be edited."""
    token = login(client, "cse2023001", seeded["password"])

    forged = jwt.encode(
        {**jwt.decode(token, config.jwt_secret, algorithms=["HS256"]), "role": "admin"},
        "the-wrong-secret",
        algorithm="HS256",
    )

    response = client.get("/api/auth/me", headers=auth_header(forged))
    assert response.status_code == 401


def test_expired_token_is_rejected(client, seeded):
    from datetime import datetime, timedelta

    expired = jwt.encode(
        {
            "sub": "1",
            "username": "admin",
            "role": "admin",
            "student_id": None,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        config.jwt_secret,
        algorithm="HS256",
    )

    response = client.get("/api/auth/me", headers=auth_header(expired))
    assert response.status_code == 401
    assert "expired" in response.get_json()["error"]["message"].lower()


def test_missing_and_malformed_authorization_headers(client, seeded):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "abc"}).status_code == 401
    assert (
        client.get("/api/auth/me", headers={"Authorization": "Bearer "}).status_code
        == 401
    )


def test_me_returns_the_signed_in_user(client, seeded, alice_token):
    response = client.get("/api/auth/me", headers=auth_header(alice_token))
    assert response.status_code == 200

    body = response.get_json()
    assert body["username"] == "cse2023001"
    assert body["role"] == "student"
    assert body["name"] == "Alice Alpha"


# --- Password policy ---------------------------------------------------


@pytest.mark.parametrize(
    "password,expected_ok",
    [
        ("Str0ng!Pass", True),
        ("short1!A", True),  # exactly 8 characters
        ("nouppercase1!", False),
        ("NOLOWERCASE1!", False),
        ("NoDigits!!", False),
        ("NoSpecial123", False),
        ("Ab1!", False),  # too short
        ("", False),
    ],
)
def test_password_policy(password, expected_ok):
    assert (password_problems(password) == []) is expected_ok


def test_change_password_requires_the_current_one(client, seeded, alice_token):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "TotallyWrong@9", "new_password": "Brand@New1"},
        headers=auth_header(alice_token),
    )
    assert response.status_code == 401


def test_change_password_rejects_a_weak_new_password(client, seeded, alice_token):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": seeded["password"], "new_password": "weak"},
        headers=auth_header(alice_token),
    )
    assert response.status_code == 400


def test_change_password_rejects_reusing_the_same_password(client, seeded, alice_token):
    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": seeded["password"],
            "new_password": seeded["password"],
        },
        headers=auth_header(alice_token),
    )
    assert response.status_code == 400


def test_change_password_works_and_the_old_one_stops_working(client, seeded, alice_token):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": seeded["password"], "new_password": "Fresh@Pass9"},
        headers=auth_header(alice_token),
    )
    assert response.status_code == 200

    assert login(client, "cse2023001", "Fresh@Pass9") is not None
    assert login(client, "cse2023001", seeded["password"]) is None


# --- Forgot password (self-service, no session required) ---------------
# Requires the username AND the email on file to match before a new
# password is accepted - stricter than the very first version of this
# project, which changed a password for anyone who supplied just a
# username, with no proof they owned the account.


def test_forgot_password_works_with_the_correct_email(client, seeded):
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": seeded["emails"]["CSE2023001"],
            "new_password": "Brand@New1",
        },
    )
    assert response.status_code == 200

    assert login(client, "cse2023001", "Brand@New1") is not None
    assert login(client, "cse2023001", seeded["password"]) is None


def test_forgot_password_rejects_the_wrong_email(client, seeded):
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": "not-their-email@test.edu",
            "new_password": "Brand@New1",
        },
    )
    assert response.status_code == 401
    # The old password must still work - nothing should have changed.
    assert login(client, "cse2023001", seeded["password"]) is not None


def test_forgot_password_rejects_an_unknown_username(client, seeded):
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "nobody",
            "email": "whoever@test.edu",
            "new_password": "Brand@New1",
        },
    )
    assert response.status_code == 401


def test_forgot_password_unknown_user_and_wrong_email_read_the_same(client, seeded):
    """Same reasoning as the login endpoint: distinguishable failure
    messages let an attacker enumerate which usernames exist."""
    unknown = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "nobody",
            "email": "x@test.edu",
            "new_password": "Brand@New1",
        },
    )
    wrong_email = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": "x@test.edu",
            "new_password": "Brand@New1",
        },
    )
    assert unknown.status_code == wrong_email.status_code == 401
    assert (
        unknown.get_json()["error"]["message"]
        == wrong_email.get_json()["error"]["message"]
    )


def test_forgot_password_rejects_a_weak_new_password(client, seeded):
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": seeded["emails"]["CSE2023001"],
            "new_password": "weak",
        },
    )
    assert response.status_code == 400
    # Rejected before anything was written.
    assert login(client, "cse2023001", seeded["password"]) is not None


def test_forgot_password_works_for_staff_accounts_too(client, seeded):
    """Staff have no `students` row, so this exercises `users.email`
    directly rather than the join fallback students use."""
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "admin",
            "email": seeded["emails"]["admin"],
            "new_password": "AdminNew@1",
        },
    )
    assert response.status_code == 200
    assert login(client, "admin", "AdminNew@1") is not None


def test_forgot_password_is_case_insensitive_on_email(client, seeded):
    response = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": seeded["emails"]["CSE2023001"].upper(),
            "new_password": "Brand@New1",
        },
    )
    assert response.status_code == 200


def test_forgot_password_shares_the_login_rate_limit(client, seeded):
    """Otherwise this endpoint would be a second, unlimited channel to
    brute-force the same account the login rate limit protects."""
    for _ in range(config.login_max_attempts):
        client.post(
            "/api/auth/forgot-password",
            json={
                "username": "cse2023001",
                "email": "wrong@test.edu",
                "new_password": "Brand@New1",
            },
        )

    blocked = client.post(
        "/api/auth/forgot-password",
        json={
            "username": "cse2023001",
            "email": seeded["emails"]["CSE2023001"],
            "new_password": "Brand@New1",
        },
    )
    assert blocked.status_code == 429


# --- Rate limiting -----------------------------------------------------


def test_repeated_failures_are_rate_limited(client, seeded):
    for _ in range(config.login_max_attempts):
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "Wrong@123"}
        )

    blocked = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Wrong@123"}
    )
    assert blocked.status_code == 429
    assert "retry_after_seconds" in blocked.get_json()["error"]["details"]


def test_rate_limit_blocks_even_the_correct_password(client, seeded):
    """Otherwise the limiter is trivially bypassed by an attacker who
    happens to guess correctly on the next attempt."""
    for _ in range(config.login_max_attempts):
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "Wrong@123"}
        )

    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": seeded["password"]}
    )
    assert response.status_code == 429


def test_successful_login_clears_the_failure_streak(client, seeded):
    for _ in range(config.login_max_attempts - 1):
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "Wrong@123"}
        )

    assert login(client, "admin", seeded["password"]) is not None

    # The streak is reset, so a fresh run of failures is needed to trip it.
    for _ in range(config.login_max_attempts - 1):
        response = client.post(
            "/api/auth/login", json={"username": "admin", "password": "Wrong@123"}
        )
    assert response.status_code == 401


def test_login_attempts_are_recorded_in_the_database(client, seeded, db_conn):
    client.post("/api/auth/login", json={"username": "admin", "password": "Wrong@123"})
    client.post(
        "/api/auth/login", json={"username": "admin", "password": seeded["password"]}
    )

    cur = db_conn.cursor(dictionary=True)
    cur.execute(
        "SELECT succeeded FROM login_attempts WHERE username = 'admin' "
        "ORDER BY attempt_id"
    )
    rows = cur.fetchall()
    cur.close()

    assert [bool(r["succeeded"]) for r in rows] == [False, True]


# --- Signing in with an email address ----------------------------------
# The users table stores a username and an email, so someone who has only
# ever seen their email will try it. Accepting both is a usability fix;
# these tests pin the behaviour and the limits around it.


def test_staff_can_sign_in_with_their_email(client, seeded):
    assert login(client, "admin@test.edu", seeded["password"]) is not None
    assert login(client, "teacher@test.edu", seeded["password"]) is not None


def test_student_can_sign_in_with_their_college_email(client, seeded):
    """A student's address lives on `students`, not `users`, so this only
    works if the lookup coalesces the two."""
    assert login(client, "alice@test.edu", seeded["password"]) is not None


def test_email_sign_in_is_case_insensitive(client, seeded):
    assert login(client, "ADMIN@TEST.EDU", seeded["password"]) is not None


def test_username_still_works(client, seeded):
    assert login(client, "admin", seeded["password"]) is not None


def test_unknown_email_is_rejected(client, seeded):
    assert login(client, "nobody@test.edu", seeded["password"]) is None


def test_wrong_password_with_a_valid_email_is_rejected(client, seeded):
    assert login(client, "admin@test.edu", "WrongPass@1") is None


def test_email_sign_in_returns_the_same_identity_as_the_username(client, seeded):
    """Both routes to the account must produce the same user, or the two
    identifiers would be different logins that happen to share a password."""
    by_name = client.post(
        "/api/auth/login", json={"username": "admin", "password": seeded["password"]}
    ).get_json()["user"]
    by_email = client.post(
        "/api/auth/login",
        json={"username": "admin@test.edu", "password": seeded["password"]},
    ).get_json()["user"]

    assert by_name["user_id"] == by_email["user_id"]
    assert by_email["username"] == "admin"
    assert by_email["role"] == "admin"


def test_rate_limit_is_shared_between_username_and_email(client, seeded):
    """Otherwise the two names for one account each get their own budget,
    doubling the attempts available to someone guessing passwords."""
    for _ in range(config.login_max_attempts):
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Wrong@123"},
        )

    # The username is now locked out. The email must be locked out too.
    blocked = client.post(
        "/api/auth/login",
        json={"username": "admin@test.edu", "password": "Wrong@123"},
    )
    assert blocked.status_code == 429, "the email address bypassed the rate limit"
