#!/bin/sh
# =====================================================================
#  Container entrypoint
# =====================================================================
#  Prepares the database, then hands over to whatever command the image
#  was given (gunicorn, by default).
#
#  Seeding runs here rather than in a separate one-shot container. A
#  dedicated container works, but it exits as soon as it finishes and
#  then sits in the project as a stopped container forever - which makes
#  Docker Desktop report the whole stack as only partially running, even
#  though everything is fine. Folding the step in here leaves exactly two
#  long-running containers, so "all running" means what it looks like.
#
#  seed_demo.py is safe to run on every start: it waits for MySQL to
#  accept connections, then does nothing at all if students already
#  exist. Only `--force` rebuilds the dataset.
# =====================================================================

set -e

echo "[entrypoint] preparing database..."
python seed_demo.py

echo "[entrypoint] starting: $*"

# `exec` replaces this shell with the real process, so the application
# becomes PID 1 and receives Docker's stop signals directly. Without it
# the shell would stay as PID 1, swallow SIGTERM, and every `docker
# compose stop` would wait for the timeout and then kill the container.
exec "$@"
