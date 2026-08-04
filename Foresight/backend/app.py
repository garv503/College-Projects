"""Application entry point.

Uses the *application factory* pattern: `create_app()` builds and returns
a configured Flask app rather than creating one at import time.

That matters for two reasons. The test suite can build an app with test
settings instead of inheriting whatever the module-level app was
configured with. And a production server (gunicorn, waitress) can call
the factory itself, which is not possible when the app is a global that
already opened a database pool as a side effect of being imported.

Run locally:
    python backend/app.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# The backend directory is added to the import path so the modules below
# can be imported as `db`, `config`, `routes.auth` and so on regardless of
# the directory the process was started from. Without this, running
# `python backend/app.py` from the project root fails on `import db`.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask, jsonify, send_from_directory  # noqa: E402
from flask_cors import CORS  # noqa: E402

import db  # noqa: E402
import security_headers  # noqa: E402
from config import config  # noqa: E402
from errors import register_error_handlers  # noqa: E402
from json_provider import ApiJSONProvider  # noqa: E402

FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


def create_app(testing: bool = False) -> Flask:
    """Build and configure the Flask application."""
    _configure_logging()

    # Refuse to boot with unsafe settings when DEBUG is off.
    config.validate()

    app = Flask(__name__, static_folder=None)
    # Must be set before any request runs: this is what stops MySQL
    # DECIMAL columns reaching the browser as strings.
    app.json = ApiJSONProvider(app)
    app.config["TESTING"] = testing
    # Reject oversized uploads at the server level, before the request
    # body is read into memory.
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    # Only the API needs CORS. The front end is served from this same
    # app in development, so same-origin requests do not use it at all -
    # it exists for the case where the pages are hosted separately.
    CORS(
        app,
        resources={r"/api/*": {"origins": config.cors_origins}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    )

    db.init_app(app)
    security_headers.init_app(app)
    register_error_handlers(app)
    _register_blueprints(app)
    _register_frontend(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from routes import admin, analytics, auth, catalog, docs, students

    app.register_blueprint(auth.bp)
    app.register_blueprint(students.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(docs.bp)

    @app.get("/api/health")
    def health():
        """Liveness probe. Reports whether the database is reachable.

        Returns 503 when the database is down so that a load balancer or
        `docker compose --wait` sees the failure, instead of a 200 that
        claims everything is fine while every real request errors.
        """
        database_ok = db.ping()
        return (
            jsonify(
                {
                    "status": "ok" if database_ok else "degraded",
                    "database": "up" if database_ok else "down",
                }
            ),
            200 if database_ok else 503,
        )


def _register_frontend(app: Flask) -> None:
    """Serve the frontend directory.

    Convenient for development and for the Docker image: one process
    serves both the API and the pages, so there is no second server to
    start and no CORS configuration to get wrong before anything works.
    """

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename: str):
        # `send_from_directory` refuses paths that escape the directory,
        # so a request for ../../backend/config.py cannot read the source.
        return send_from_directory(FRONTEND_DIR, filename)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # The driver logs every statement at DEBUG, which drowns out
    # everything else during development.
    logging.getLogger("mysql.connector").setLevel(logging.WARNING)


app = create_app()


if __name__ == "__main__":
    print(f"  API      http://{config.host}:{config.port}/api")
    print(f"  Docs     http://{config.host}:{config.port}/api/docs")
    print(f"  App      http://{config.host}:{config.port}/")
    app.run(host=config.host, port=config.port, debug=config.debug)
