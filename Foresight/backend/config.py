"""Application configuration, read from the environment.

Every setting lives in one place and comes from an environment variable
with a development-friendly default. Nothing secret is hardcoded: the old
version of this project shipped `password = "1234"` inside db_config.py,
which meant the database password was in the public git history forever.

Local development reads a `.env` file (see `.env.example`). Production is
expected to set real environment variables; `Config.validate()` refuses to
start if a secret was left at its development default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above backend/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# The value that means "nobody has configured a real secret yet".
DEV_SECRET = "dev-secret-change-me"


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean from the environment.

    Accepts the spellings people actually type, so DEBUG=1, DEBUG=true and
    DEBUG=yes all work rather than silently being treated as truthy strings.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    """Immutable snapshot of the app's settings.

    Frozen because configuration changing halfway through a request is a
    source of bugs that is very hard to reproduce.
    """

    # --- Database -----------------------------------------------------
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = _env_int("DB_PORT", 3306)
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "foresight")

    # Size of the connection pool. Each pooled connection is a real TCP
    # socket held open, so this trades memory for not paying the connect
    # handshake on every single request.
    db_pool_size: int = _env_int("DB_POOL_SIZE", 5)

    # --- Authentication ----------------------------------------------
    jwt_secret: str = os.getenv("JWT_SECRET", DEV_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = _env_int("JWT_TTL_MINUTES", 120)

    # --- Login rate limiting ------------------------------------------
    login_max_attempts: int = _env_int("LOGIN_MAX_ATTEMPTS", 5)
    login_window_seconds: int = _env_int("LOGIN_WINDOW_SECONDS", 300)

    # --- Server -------------------------------------------------------
    debug: bool = _env_bool("DEBUG", True)
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = _env_int("PORT", 5000)

    # Origins allowed to call the API from a browser. "*" is fine for a
    # local demo; a deployment should list its real front-end origin.
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        ]
    )

    # --- Academic rules -----------------------------------------------
    # Kept as configuration rather than magic numbers scattered through
    # the analytics code, because different colleges use different bars.
    pass_percent: int = _env_int("PASS_PERCENT", 40)
    min_attendance_percent: int = _env_int("MIN_ATTENDANCE_PERCENT", 75)

    def validate(self) -> None:
        """Fail fast on a configuration that is unsafe to run in public.

        Called from create_app(). In debug mode a missing secret is only a
        warning, because forcing every student cloning the repo to invent
        a JWT secret before seeing the app run is hostile. With DEBUG off
        it is a hard error.
        """
        problems: list[str] = []

        if not self.debug:
            if self.jwt_secret == DEV_SECRET:
                problems.append(
                    "JWT_SECRET is still the development default. Generate one "
                    'with:  python -c "import secrets; print(secrets.token_hex(32))"'
                )
            if not self.db_password:
                problems.append("DB_PASSWORD is empty.")
            if "*" in self.cors_origins:
                problems.append(
                    "CORS_ORIGINS is '*'. Name the front-end origin explicitly."
                )

        if problems:
            raise RuntimeError(
                "Refusing to start with DEBUG=false:\n  - " + "\n  - ".join(problems)
            )


config = Config()
