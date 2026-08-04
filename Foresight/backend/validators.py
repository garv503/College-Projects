"""Input validation helpers.

The original routes trusted the request body completely:
`data.get('username').strip()` crashes with AttributeError (a 500) the
moment `username` is missing, and `data['name']` raises KeyError. Marks
were inserted with no range check at all, so a typo could store 9999.

These helpers do one thing each, raise a clear ApiError on failure, and
return a value of the right Python type on success - so a route reads as
a list of requirements rather than a pile of if-statements.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from flask import request

from errors import bad_request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ROLL_NO_RE = re.compile(r"^[A-Za-z0-9\-/]{3,20}$")


def json_body() -> dict:
    """Return the request's JSON body, or raise 400.

    `silent=True` stops Flask raising its own HTML 400 on malformed JSON,
    so the caller gets the same JSON error shape as everything else.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise bad_request("Request body must be a JSON object")
    return data


def require_str(
    data: dict,
    field: str,
    *,
    min_len: int = 1,
    max_len: int = 255,
    strip: bool = True,
) -> str:
    value = data.get(field)
    if value is None:
        raise bad_request(f"'{field}' is required", field=field)
    if not isinstance(value, str):
        raise bad_request(f"'{field}' must be text", field=field)
    if strip:
        value = value.strip()
    if len(value) < min_len:
        raise bad_request(f"'{field}' must be at least {min_len} characters", field=field)
    if len(value) > max_len:
        raise bad_request(f"'{field}' must be at most {max_len} characters", field=field)
    return value


def optional_str(data: dict, field: str, default: str | None = None, **kw) -> str | None:
    if data.get(field) in (None, ""):
        return default
    return require_str(data, field, **kw)


def require_int(
    data: dict,
    field: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = data.get(field)
    if value is None:
        raise bad_request(f"'{field}' is required", field=field)

    # Accept "3" as well as 3: HTML form fields always arrive as strings,
    # and rejecting them would push this conversion into every caller.
    try:
        value = int(str(value).strip())
    except (TypeError, ValueError):
        raise bad_request(f"'{field}' must be a whole number", field=field)

    if minimum is not None and value < minimum:
        raise bad_request(f"'{field}' must be at least {minimum}", field=field)
    if maximum is not None and value > maximum:
        raise bad_request(f"'{field}' must be at most {maximum}", field=field)
    return value


def require_number(
    data: dict,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = data.get(field)
    if value is None:
        raise bad_request(f"'{field}' is required", field=field)
    try:
        value = float(str(value).strip())
    except (TypeError, ValueError):
        raise bad_request(f"'{field}' must be a number", field=field)

    if minimum is not None and value < minimum:
        raise bad_request(f"'{field}' must be at least {minimum}", field=field)
    if maximum is not None and value > maximum:
        raise bad_request(f"'{field}' must be at most {maximum}", field=field)
    return value


def require_choice(data: dict, field: str, allowed: tuple[str, ...]) -> str:
    value = require_str(data, field).lower()
    if value not in allowed:
        raise bad_request(f"'{field}' must be one of: {', '.join(allowed)}", field=field)
    return value


def require_email(data: dict, field: str = "email") -> str:
    value = require_str(data, field, max_len=150).lower()
    if not EMAIL_RE.match(value):
        raise bad_request(f"'{value}' is not a valid email address", field=field)
    return value


def require_roll_no(data: dict, field: str = "roll_no") -> str:
    value = require_str(data, field, min_len=3, max_len=20).upper()
    if not ROLL_NO_RE.match(value):
        raise bad_request(
            "Roll number may only contain letters, digits, '-' and '/'",
            field=field,
        )
    return value


def require_date(data: dict, field: str, *, allow_future: bool = False) -> date:
    raw = require_str(data, field)
    try:
        value = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise bad_request(f"'{field}' must be a date as YYYY-MM-DD", field=field)
    if not allow_future and value > date.today():
        raise bad_request(f"'{field}' cannot be in the future", field=field)
    return value


def require_list(data: dict, field: str, *, min_len: int = 1) -> list:
    value = data.get(field)
    if not isinstance(value, list):
        raise bad_request(f"'{field}' must be a list", field=field)
    if len(value) < min_len:
        raise bad_request(
            f"'{field}' must contain at least {min_len} item(s)", field=field
        )
    return value


# ---------------------------------------------------------------------
# Query-string helpers (for pagination and filters)
# ---------------------------------------------------------------------


def query_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise bad_request(f"Query parameter '{name}' must be a whole number")
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def pagination() -> tuple[int, int, int]:
    """Read ?page= and ?per_page= and return (page, per_page, offset).

    `per_page` is capped so that a caller asking for 10 million rows gets
    100 instead of taking the server down.
    """
    page = query_int("page", 1, minimum=1)
    per_page = query_int("per_page", 20, minimum=1, maximum=100)
    return page, per_page, (page - 1) * per_page


def sort_column(allowed: dict[str, str], default: str) -> str:
    """Resolve ?sort= against a whitelist of sortable columns.

    A column name cannot be a bound parameter - it is part of the SQL
    text - so the only safe way to allow user-chosen sorting is to map
    the input through a fixed dictionary and never use the raw value.
    """
    requested = request.args.get("sort", default)
    if requested not in allowed:
        raise bad_request(f"Cannot sort by '{requested}'. Allowed: {', '.join(allowed)}")
    direction = "DESC" if request.args.get("order", "asc").lower() == "desc" else "ASC"
    return f"{allowed[requested]} {direction}"
