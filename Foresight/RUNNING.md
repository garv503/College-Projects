# Running Foresight

Day-to-day operational guide: how to start it, stop it, reset it, and
what to do when it misbehaves.

First-time setup is in **[setup.txt](setup.txt)**. What the project *is*
and how it is built is in **[README.md](README.md)**.

> Run every command in this file from the `Foresight/` directory — the
> one containing `docker-compose.yml`. Compose resolves its paths
> relative to that file, so running from the repository root fails with
> `no configuration file provided`.

---

## Ports

Both are **fixed**, not configurable — there is one answer to "which
port is it on".

| Service | URL / address | Notes |
|---|---|---|
| **Application + API** | **http://localhost:5000** | The only one you normally need |
| API documentation | http://localhost:5000/api/docs | Interactive Swagger UI |
| Health check | http://localhost:5000/api/health | Returns 503 if the database is down |
| MySQL | `localhost:3307` | For Workbench/DBeaver. **Not 3306** — that is left free for a locally installed MySQL |

Inside the Docker network the API reaches the database at `db:3306`.
That is container-to-container and never changes, regardless of the
host port.

---

## Start and stop

```bash
docker compose up -d --build     # start (build first time / after code changes)
docker compose up -d             # start (no rebuild)
docker compose ps                # what is running
docker compose stop              # stop, keep containers and data
docker compose down              # remove containers, KEEP the data volume
docker compose down -v           # remove containers AND WIPE the database
```

A healthy stack looks like this:

```
NAME            STATUS                    PORTS
foresight-api   Up 20 seconds (healthy)   0.0.0.0:5000->5000/tcp
foresight-db    Up 28 seconds (healthy)   0.0.0.0:3307->3306/tcp
```

`foresight-seed` is **expected to show as `Exited (0)`**. It is a
one-shot container that loads demo data and stops; it is not a failure.
Only `api` and `db` are long-running, and only those two report a health
status. In Docker Desktop the stack is fine when both show green — the
seed row sitting at `Exited (0)` alongside them is normal.

### Startup order

Compose enforces it, so you do not have to:

```
db  ──(waits for healthcheck)──▶  seed  ──(waits for exit 0)──▶  api
```

The database healthcheck is why the API never starts against a MySQL
that is still initialising.

---

## Logs

```bash
docker compose logs -f api       # follow the API
docker compose logs db           # database, including schema loading
docker compose logs seed         # demo-data loader
docker compose logs --tail 50    # last 50 lines, all services
```

---

## Signing in

Sign in with **either the username or the email address** on file — both
reach the same account.

| Username | Email | Password | Role |
|---|---|---|---|
| `admin` | `admin@foresight.local` | `Admin@2024` | Everything |
| `faculty` | `faculty@foresight.local` | `Faculty@2024` | Analytics, marks entry, CSV import |
| a roll number, e.g. `cse2025001` | that student's college email | `Student@2024` | Own records only |

The seed prints a working roll number when it runs:
`docker compose logs seed | grep Student@`

To look up an account's email:

```bash
docker compose exec db mysql -uroot -p foresight \
  -e "SELECT username, email FROM users WHERE role <> 'student';"
```

---

## The demo data

```bash
# Re-seed from scratch (wipes students, marks, attendance)
docker compose run --rm seed python seed_demo.py --force
```

Plain `docker compose up` is **safe to run repeatedly** — the seed
detects an already-populated database and does nothing, so a student you
added through the admin console survives a restart. Only `--force` and
`down -v` destroy data.

---

## Connecting a SQL client

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `3307` |
| User | `root` |
| Password | the `DB_PASSWORD` in your `.env` |
| Database | `foresight` |

Or from the shell:

```bash
docker compose exec db mysql -uroot -p foresight
```

> Avoid `SELECT * FROM users` — passwords are stored in plain text in
> this build, so that prints every one of them to your screen and shell
> history. Name the columns you actually need.

---

## Rebuilding after a change

| You changed | What to run |
|---|---|
| Python, HTML, CSS, JS | `docker compose up -d --build` |
| `database/*.sql` | `docker compose down -v` then `up --build` — the SQL scripts run **only** when the data volume is empty |
| `.env` | `docker compose up -d --force-recreate` |

That second row is the one that catches people: editing `schema.sql` and
running `up` again appears to do nothing, because MySQL only executes
`docker-entrypoint-initdb.d` on a fresh volume.

---

## Troubleshooting

### Docker Desktop shows the stack as not healthy

Expand the `foresight` group and look at the individual containers. The
stack is fine when **`foresight-api` and `foresight-db` both report
healthy**; `foresight-seed` sitting at `Exited (0)` beside them is normal
and does not make the stack unhealthy.

```bash
docker compose ps -a
docker inspect foresight-api --format '{{.State.Health.Status}}'
docker inspect foresight-db  --format '{{.State.Health.Status}}'
```

Both should print `healthy`. If they do, the application is working
whatever the collapsed group row suggests — confirm with
`curl http://localhost:5000/api/health`.

### `no configuration file provided: not found`

You are in the wrong directory. `cd` into `Foresight/`.

### Port 5000 already in use

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

A local `python backend/app.py` is the usual culprit.

### The app responds but shows the wrong data (Windows)

This one is nasty because nothing errors. A local Flask server binding
`127.0.0.1:5000` **shadows** Docker's `0.0.0.0:5000`. Your browser
reaches the local server, hitting your local MySQL instead of the
container — so logins fail or data looks stale.

```bash
netstat -ano | grep ":5000"      # a 127.0.0.1:5000 line means a local server is shadowing
```

Stop every local `python backend/app.py` before using Docker.

### `Unknown MySQL server host 'db'` / API restart loop

The database container is not running. Check why:

```bash
docker compose logs db
docker inspect foresight-db --format '{{.State.ExitCode}} {{.State.Error}}'
```

**If you moved or renamed the project folder**, this is almost certainly
the cause. Compose bakes absolute host paths into the containers it
creates; after a move those paths no longer exist, and Docker fails
mounting the SQL files. Fix:

```bash
docker compose down          # discard the stale containers
docker compose up -d --build # recreate them with the new paths
```

Your data survives — it lives in a named volume, not in the containers.

### Database container exits with 127

Same cause as above: a bind-mount source that no longer exists. Docker
creates the missing path as a *directory*, then fails mounting a
directory onto a file. `docker compose down && docker compose up --build`.

### Everything is broken, start clean

```bash
docker compose down -v          # removes containers and the data volume
docker compose up -d --build    # rebuilds and re-seeds from scratch
```

Takes about 30 seconds and discards all data.

---

## Running without Docker

See **[setup.txt](setup.txt)**. In short, from `Foresight/`:

```bash
python backend/app.py
```

Both modes can run at once — each uses its own database — but only if
they do not share a host port. Since the Docker port is fixed at 5000,
give the local server a different one:

```bash
PORT=5001 python backend/app.py       # macOS / Linux
$env:PORT=5001; python backend/app.py # Windows PowerShell
```

---

## Health check

```bash
curl http://localhost:5000/api/health
```

```json
{"status": "ok", "database": "up"}
```

Returns HTTP 503 with `"database": "down"` if MySQL is unreachable, so
`docker compose ps` marking the API unhealthy is a real signal, not a
timing artefact.
