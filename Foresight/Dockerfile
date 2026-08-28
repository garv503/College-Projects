# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------
# Foresight API
# ---------------------------------------------------------------------
# `-slim` rather than the full image: ~120 MB instead of ~1 GB, and this
# app needs no compiler at runtime.
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE - no .pyc files in a layer that is rebuilt anyway.
# PYTHONUNBUFFERED        - logs appear in `docker logs` immediately rather
#                           than sitting in a buffer until the app exits.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies are copied and installed before the source, so editing a
# .py file does not invalidate the cached pip layer. Getting this order
# wrong means re-downloading every package on every build.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir gunicorn==23.0.0

COPY backend/ backend/
COPY frontend/ frontend/
COPY database/ database/

# Normalise line endings and make the entrypoint executable. Both matter
# on Windows: git may check the file out with CRLF, and `\r` on the
# shebang line makes Linux report the confusing "no such file or
# directory" for a script that plainly exists.
RUN sed -i 's/\r$//' backend/docker-entrypoint.sh \
    && chmod +x backend/docker-entrypoint.sh

# Run as a non-root user. A container process running as root that gets
# compromised has root on the container filesystem.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/health').status==200 else 1)"

WORKDIR /app/backend

# The entrypoint seeds the database, then execs the CMD below. Keeping
# them separate means `docker compose run api <something else>` still
# gets the same preparation.
ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]

# gunicorn, not `flask run`. The development server is single-threaded
# and explicitly not for production use.
#
# `create_app()` is called by gunicorn itself - that is the reason the
# app factory pattern exists. Two workers with two threads is plenty for
# a demo and keeps the MySQL pool small.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "app:create_app()"]
