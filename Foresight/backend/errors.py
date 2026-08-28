"""Uniform error handling.

Every failure carries a real HTTP status code and one predictable JSON
shape, so the front end has exactly one error path to write:

    {"error": {"code": "not_found", "message": "Student 42 not found"}}

Returning 200 for a failure would defeat that: `response.ok` would be
true in the browser and monitoring would see a healthy endpoint, leaving
the caller to inspect the body to discover the request did not work.
"""

from __future__ import annotations

import logging
import traceback

from flask import jsonify
from mysql.connector import Error as MySQLError
from werkzeug.exceptions import HTTPException

from config import config

log = logging.getLogger(__name__)


class ApiError(Exception):
    """An error that is safe to show the user.

    Raised deliberately by route and service code. Anything *not* raised
    as an ApiError is treated as a bug and reported generically, so an
    unexpected stack trace never leaks to a client.
    """

    def __init__(
        self,
        message: str,
        status: int = 400,
        code: str = "bad_request",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details or {}

    def to_response(self):
        body: dict = {"error": {"code": self.code, "message": self.message}}
        if self.details:
            body["error"]["details"] = self.details
        return jsonify(body), self.status


# --- Shorthand constructors for the cases that come up constantly -----


def bad_request(message: str, **details) -> ApiError:
    return ApiError(message, 400, "bad_request", details or None)


def unauthorized(message: str = "Authentication required") -> ApiError:
    return ApiError(message, 401, "unauthorized")


def forbidden(message: str = "You do not have access to this resource") -> ApiError:
    return ApiError(message, 403, "forbidden")


def not_found(message: str = "Resource not found") -> ApiError:
    return ApiError(message, 404, "not_found")


def conflict(message: str) -> ApiError:
    return ApiError(message, 409, "conflict")


def too_many_requests(message: str, retry_after: int | None = None) -> ApiError:
    details = {"retry_after_seconds": retry_after} if retry_after else None
    return ApiError(message, 429, "too_many_requests", details)


def register_error_handlers(app) -> None:
    """Attach the handlers to the Flask app."""

    @app.errorhandler(ApiError)
    def _handle_api_error(err: ApiError):
        # Expected failures are logged at info: they are not bugs.
        log.info("api error %s: %s", err.code, err.message)
        return err.to_response()

    @app.errorhandler(HTTPException)
    def _handle_http_error(err: HTTPException):
        # Covers Flask's own 404/405/413 etc. so they come back as JSON
        # rather than Werkzeug's HTML error page.
        return (
            jsonify(
                {
                    "error": {
                        "code": (err.name or "http_error").lower().replace(" ", "_"),
                        "message": err.description,
                    }
                }
            ),
            err.code or 500,
        )

    @app.errorhandler(MySQLError)
    def _handle_db_error(err: MySQLError):
        # Triggers and CHECK constraints reject bad data with SQLSTATE
        # 45000 and a message written for humans (see triggers.sql), so
        # those are surfaced to the caller as a 400. Everything else is
        # an infrastructure problem and is deliberately kept vague,
        # because driver messages quote table and column names.
        if getattr(err, "sqlstate", None) == "45000":
            return ApiError(str(err.msg), 400, "constraint_violation").to_response()

        log.error("database error: %s", err, exc_info=True)
        return ApiError(
            "A database error occurred", 503, "database_unavailable"
        ).to_response()

    @app.errorhandler(Exception)
    def _handle_unexpected(err: Exception):
        # A genuine bug. Log the whole trace server-side, tell the client
        # nothing about it - except in debug mode, where seeing the
        # traceback in the browser is the entire point.
        log.error("unhandled exception: %s", err, exc_info=True)
        payload: dict = {
            "error": {
                "code": "internal_error",
                "message": "Something went wrong on our side",
            }
        }
        if config.debug:
            payload["error"]["debug"] = {
                "type": type(err).__name__,
                "message": str(err),
                "traceback": traceback.format_exc().splitlines()[-12:],
            }
        return jsonify(payload), 500
