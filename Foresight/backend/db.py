"""Database access layer.

Everything that talks to MySQL goes through this module. Routes never
import `mysql.connector` themselves, which keeps the driver in one place
and means the connection rules below are impossible to opt out of.

Three problems this solves that the original code had:

1. A new TCP connection was opened for every request and closed again.
   Here a *pool* is opened once at startup and connections are borrowed
   and returned, so the connect handshake is paid once, not per request.

2. `conn.close()` was called on the happy path only. Any query that
   raised leaked the connection until the process died. Here the
   connection is tied to the Flask request and released by a teardown
   handler that runs whether the request succeeded or blew up.

3. Nothing was ever rolled back. A multi-statement write that failed
   halfway left the database in a half-written state. Here an
   uncommitted transaction is always rolled back on the way out, so a
   route that crashes before calling `commit()` changes nothing.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import mysql.connector
from flask import g
from mysql.connector import pooling

from config import config

log = logging.getLogger(__name__)

# Module-level pool, created once by init_app().
_pool: pooling.MySQLConnectionPool | None = None


def init_app(app) -> None:
    """Create the connection pool and register the teardown handler."""
    global _pool

    _pool = pooling.MySQLConnectionPool(
        pool_name="foresight_pool",
        pool_size=config.db_pool_size,
        pool_reset_session=True,
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        # Pin the session time zone to UTC so NOW() and every TIMESTAMP
        # read back in UTC regardless of what the server or the host is
        # set to. Without this the same row means different things in
        # Docker (UTC) and on a developer's machine (local time), and the
        # JSON layer has no way to know which it was handed.
        time_zone="+00:00",
        # The driver's own autocommit is off so that a request is one
        # transaction. Routes decide when to commit.
        autocommit=False,
        # Return DATE/DATETIME as Python date objects rather than strings.
        use_pure=True,
    )

    app.teardown_appcontext(_release_connection)
    log.info(
        "MySQL pool ready: %s@%s:%s/%s (size=%d)",
        config.db_user,
        config.db_host,
        config.db_port,
        config.db_name,
        config.db_pool_size,
    )


def get_db():
    """Return this request's connection, borrowing one if needed.

    Stored on Flask's `g`, which is per-request state, so every query in
    a single request shares one connection and therefore one transaction.
    """
    if _pool is None:
        raise RuntimeError("db.init_app() was never called")

    if "db_conn" not in g:
        g.db_conn = _pool.get_connection()
    return g.db_conn


def _release_connection(exc: BaseException | None = None) -> None:
    """Roll back anything uncommitted and hand the connection back.

    Registered as a teardown handler, so it runs at the end of every
    request - including requests that raised. `rollback()` on a
    connection with nothing pending is a no-op, which is why it is safe
    to call unconditionally: if the route already committed, this does
    nothing; if it did not, the partial write is discarded.
    """
    conn = g.pop("db_conn", None)
    if conn is None:
        return
    try:
        conn.rollback()
    except mysql.connector.Error:
        log.warning("rollback failed while releasing connection", exc_info=True)
    finally:
        # For a pooled connection, close() means "return to the pool".
        conn.close()


def set_actor(username: str | None) -> None:
    """Tell the database who is making the current request.

    The audit triggers read `@app_user` to attribute a change to a person
    (see database/triggers.sql). It is a session variable, so it has to
    be set on the same connection the writes will run on - hence doing it
    here rather than passing a user id into every INSERT.
    """
    if username is None:
        return
    cur = get_db().cursor()
    try:
        cur.execute("SET @app_user = %s", (username,))
    finally:
        cur.close()


# ---------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------
# All of these take a parameterised SQL string. Values are passed as the
# `params` tuple and never formatted into the string, which is what makes
# SQL injection impossible here: the driver sends the query and the data
# separately, so a value like  ' OR 1=1--  is only ever compared as text.


def query_all(sql: str, params: Sequence[Any] = ()) -> list[dict]:
    """Run a SELECT and return every row as a dict."""
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, tuple(params))
        return cur.fetchall()
    finally:
        cur.close()


def query_one(sql: str, params: Sequence[Any] = ()) -> dict | None:
    """Run a SELECT and return the first row, or None."""
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, tuple(params))
        row = cur.fetchone()
        # A cursor with rows left unread cannot be reused, so drain it.
        cur.fetchall()
        return row
    finally:
        cur.close()


def query_value(sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
    """Run a SELECT and return the first column of the first row."""
    row = query_one(sql, params)
    if not row:
        return default
    return next(iter(row.values()))


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid for inserts,
    otherwise the number of affected rows.

    Does *not* commit - the caller does that once, after all its writes,
    so a multi-step operation stays atomic.
    """
    cur = get_db().cursor()
    try:
        cur.execute(sql, tuple(params))
        return cur.lastrowid or cur.rowcount
    finally:
        cur.close()


def execute_many(sql: str, rows: Sequence[Sequence[Any]]) -> int:
    """Run one statement against many rows in a single round-trip.

    Used by the CSV importer: inserting 500 marks one at a time is 500
    network round-trips, this is one.
    """
    if not rows:
        return 0
    cur = get_db().cursor()
    try:
        cur.executemany(sql, [tuple(r) for r in rows])
        return cur.rowcount
    finally:
        cur.close()


def call_proc(name: str, args: Sequence[Any] = ()) -> list[list[dict]]:
    """Call a stored procedure and return each result set as dicts.

    Procedures such as sp_student_report_card return more than one result
    set, so this always returns a list of them rather than flattening.
    """
    cur = get_db().cursor(dictionary=True)
    try:
        cur.callproc(name, tuple(args))
        return [list(result.fetchall()) for result in cur.stored_results()]
    finally:
        cur.close()


def call_proc_out(name: str, args: Sequence[Any]) -> tuple:
    """Call a procedure that has OUT parameters and return them.

    The driver wants placeholders for OUT parameters, so pass `0` (or any
    value) in those positions and read the real values from the result.
    """
    cur = get_db().cursor()
    try:
        return cur.callproc(name, tuple(args))
    finally:
        cur.close()


def commit() -> None:
    """Commit this request's transaction."""
    get_db().commit()


def ping() -> bool:
    """Cheap connectivity check used by the /api/health endpoint."""
    try:
        return query_value("SELECT 1") == 1
    except mysql.connector.Error:
        return False
