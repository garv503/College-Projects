# Foresight

A full-stack academic analytics platform. It turns raw marks and
attendance into a ranked, explained view of which students need help —
and reaches them while there is still time to act.

Built with Flask, MySQL 8 and vanilla JavaScript, with JWT authentication,
role-based access control, an audited database, 165 automated tests and a
one-command Docker setup.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Browser    │────▶│  Flask API   │────▶│     MySQL 8      │
│  (no build) │ JWT │  blueprints  │ SQL │  views·triggers  │
│             │◀────│  + services  │◀────│   procedures     │
└─────────────┘     └──────────────┘     └──────────────────┘
```
---

## Contents

- [What it does](#what-it-does)
- [Screens](#screens)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [The database](#the-database)
- [How risk scoring works](#how-risk-scoring-works)
- [Security](#security)
- [API](#api)
- [Testing](#testing)
- [Project layout](#project-layout)
- [What changed from v1](#what-changed-from-v1)

---

## What it does

**For a student** — one dashboard showing their marks, attendance, class
rank and percentile, how each subject compares to the class average,
whether they are improving or slipping, and a plain-English explanation
of their academic standing with suggested next steps.

**For faculty and administrators** — cohort statistics, a grade
distribution, per-subject pass rates that surface which papers are
failing people, and a list of at-risk students ranked by severity *with
the reason for each*. Plus bulk CSV import, CSV export, student
management and a full audit trail.

### Features

| | |
|---|---|
| **Risk scoring** | 0–100 weighted score from four signals, with written reasons and recommendations — not a single `if marks < 40` cliff |
| **Cohort ranking** | Class rank and percentile via SQL window functions, scoped to branch + semester |
| **Trend detection** | Compares the first half of a term's assessments against the second to flag improving vs declining students |
| **Class comparison** | Each subject mark against the class average — 52% reads very differently when the class average is 48% |
| **Bulk CSV import** | Validates the entire file before writing anything; a single bad row rejects the upload with per-line errors |
| **Report cards** | Grades, credit-weighted GPA and rank, as JSON or a CSV download |
| **Audit trail** | Written by database triggers, so a change made directly in a SQL client is recorded too |
| **RBAC** | Three roles, enforced on every endpoint — a student cannot read another student's records |
| **Self-service password reset** | Username + registered email resets a forgotten password with no session required |
| **API docs** | Interactive Swagger UI at `/api/docs` |

---

## Screens

| Student dashboard | Admin console |
|---|---|
| Marks, attendance, rank, trend, per-subject comparison and an explained academic standing | Cohort KPIs, grade distribution, pass rates, and at-risk students ranked with reasons |

> Screenshots: run the project (below) and visit `/` — the demo seed
> produces 78 students across four cohorts, so every chart has real
> shape rather than placeholder data.

---

## Quick start

Both ways of running the project are supported, and they can run at the
same time — Docker uses its own MySQL container, the terminal path uses
the MySQL installed on your machine. One `.env` configures both.

### Option A — Docker (nothing to install)

```bash
git clone https://github.com/garv503/College-Projects.git
cd College-Projects
git checkout Student-Analytics

cp .env.example .env      # optional; sensible defaults are built in
docker compose up --build
```

Open **http://localhost:5000**. Compose starts MySQL, loads the schema,
views, triggers and procedures, seeds a demo dataset, then starts the API
behind gunicorn.

Useful commands:

```bash
docker compose logs -f api                              # follow the API log
docker compose down                                     # stop, keep the data
docker compose down -v                                  # stop and wipe the database
docker compose run --rm seed python seed_demo.py --force  # rebuild the demo data
APP_PORT=5001 docker compose up                         # use a different host port
```

`docker compose up` is safe to run repeatedly — the seed does nothing if
students already exist, so a student you added through the admin console
survives a restart.

### Option B — Terminal

**Requires:** Python 3.11+ and MySQL 8.0+

```bash
# 1. Configuration
cp .env.example .env
#    then edit .env and set DB_PASSWORD to your MySQL root password

# 2. Dependencies
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r backend/requirements.txt

# 3. Database — order matters, each file builds on the last
mysql -u root -p < database/schema.sql
mysql -u root -p foresight < database/views.sql
mysql -u root -p foresight < database/triggers.sql
mysql -u root -p foresight < database/procedures.sql
mysql -u root -p foresight < database/sample_data.sql

# 4. Demo data (78 students with a full term of marks and attendance)
python backend/seed_demo.py
#    already have data? re-seed from scratch with:
#    python backend/seed_demo.py --force

# 5. Run
python backend/app.py
```

Open **http://localhost:5000**.

### Running both at once

They collide only on the host port, so give one of them a different one:

```bash
PORT=5001 python backend/app.py     # terminal on 5001, Docker keeps 5000
# or
APP_PORT=5001 docker compose up     # Docker on 5001, terminal keeps 5000
```

The MySQL container is already published on **3307**, not 3306, so it
never fights a locally installed MySQL. Override with `DB_HOST_PORT`.

> **How one `.env` serves both:** Compose reads `.env` to fill in the
> `${...}` values in `docker-compose.yml`, so `DB_PASSWORD` and
> `JWT_SECRET` are shared. The two settings that *must* differ inside a
> container — `DB_HOST` and `DB_PORT` — are hardcoded to `db:3306` in the
> compose file rather than substituted, so a `.env` written for the
> terminal (where `DB_HOST` is `localhost`) cannot break the containers.

### Demo logins

The seed script prints these when it finishes:

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@2024` | Full access |
| `faculty` | `Faculty@2024` | Analytics + marks entry |
| any roll number | `Student@2024` | Their own records only |

Roll numbers look like `CSE2025001` — the seed prints a working example.

> These are demo credentials for a local database. Change them before
> exposing the app to a network.

---

## Architecture

### Request flow

```
routes/         HTTP only — read request, check permission, return JSON
   │            Thin by design. No business decisions live here.
   ▼
services/       Business logic — risk scoring, CSV parsing, report building
   │            Testable without an HTTP request.
   ▼
db.py           Pooled connections, parameterised queries, transactions
   │
   ▼
MySQL           Views compute the derived numbers.
                Triggers enforce what must never be bypassed.
                Procedures own the multi-table transactions.
```

### Why the logic sits in SQL

Percentages, ranks and pass rates are *derived* facts. If the dashboard,
the CSV export and the at-risk report each recalculated them inline, they
would eventually disagree. Defining them once as a view means all three
are mathematically guaranteed to match.

The views build in layers, each one consuming the last:

```
v_enrollment_summary       one row per (student, subject)
      │
      ├──▶ v_student_overall        credit-weighted per-student totals
      │          │
      │          └──▶ v_student_rank         + rank and percentile
      │                     │
      │                     └──▶ v_at_risk_students     + risk score
      │
      └──▶ v_subject_stats          per-subject averages and pass rates
```

### The frontend has no build step

Open `frontend/index.html` and it runs. No npm, no bundler, no
`node_modules`. Three ES modules do the work:

- **`api.js`** — the only file that knows about `fetch`, tokens and error
  shapes. Pages call `api.get(...)`.
- **`ui.js`** — toasts, modals, formatting and safe DOM building.
- **`charts.js`** — every chart, so styling rules are applied once.

Styling is a token system: `tokens.css` declares every colour, space and
radius once, and nothing below it hardcodes a value — the whole palette
can be re-tuned by editing that one file.

---

## The database

Seven tables, six views, eight triggers, five procedures and two
functions.

### Schema

| Table | Purpose |
|---|---|
| `branches` | Department lookup — a foreign key, so `CSE`/`cse`/`C.S.E` cannot become three branches |
| `students` | Roll number, email, cohort, soft-delete flag |
| `subjects` | Code, credits, and a **per-subject** pass mark |
| `users` | Login accounts — plain-text passwords by design (see [Security](#security)), three roles |
| `enrollments` | Student ↔ subject for an academic year |
| `assessments` | Individual graded items (quiz / assignment / midterm / final) |
| `attendance_records` | One row per class held |
| `audit_log` | Who changed what, written by triggers |
| `login_attempts` | Durable brute-force record |

### Three design decisions worth explaining

**1. Marks are individual assessments, not one number.**
Storing a flat `marks` column makes trend analysis impossible. Each
assessment carries its own `max_marks`, so a 20-mark quiz and a 100-mark
final coexist and the subject percentage is `SUM(obtained)/SUM(max)` —
weighting each by what it was actually worth. Averaging the individual
percentages instead would treat a quiz as equal to a final.

**2. Attendance is dated rows, not a stored percentage.**
The percentage is derived by a view, so it can never drift out of sync
with the register. `late` counts as attended; `excused` is removed from
the denominator rather than counted against the student.

**3. Marks hang off an enrollment, not off (student, subject).**
That is what allows a student to re-sit a subject in a later year without
colliding on a primary key.

### Triggers do two jobs

*Validation that cannot be bypassed* — `marks_obtained > max_marks` and
future-dated assessments are rejected with `SIGNAL SQLSTATE '45000'` and
a human-readable message the API passes straight through as a `400`.

*Auditing the application cannot forget* — if the audit write lived in
Python, any new code path that skipped it would create an untracked
change. In a trigger it is structurally impossible to miss:

```sql
-- This is rejected, even typed directly into the MySQL console:
INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, assessed_on)
VALUES (1, 'quiz', 99, 20, '2025-01-01');
-- ERROR 1644 (45000): marks_obtained cannot exceed max_marks
```

---

## How risk scoring works

The original version was a single cliff:

```python
status = "Good"
if avg_marks < 40 or avg_attendance < 60:
    status = "Weak"
```

Three problems: it crashed with a `TypeError` when a student had no
marks yet (`AVG` of nothing is `NULL`); 39.9% with three failed subjects
looked identical to 39.9% with none; and it told a student they were
"Weak" without saying why.

The replacement scores 0–100 from four weighted signals:

| Signal | Weight | Rule |
|---|---|---|
| Marks below the pass mark | up to **40** | Scaled by shortfall — 0% marks costs the full 40 |
| Attendance below 75% | up to **30** | Scaled by shortfall |
| Backlogs | **10** each, capped at **20** | Capped so one weak subject does not dominate |
| Bottom-quartile rank | **10** | Standing relative to peers |

Every point is explained:

```json
{
  "score": 64.0,
  "band": "high",
  "reasons": [
    "Average of 20.0% is below the 40% pass mark",
    "Attendance of 40.5% is below the 75% requirement",
    "Failing 5 subjects"
  ],
  "recommendations": [
    "Book remedial sessions for the lowest-scoring subjects",
    "Attendance is low enough to risk exam ineligibility - escalate to the mentor"
  ]
}
```

The same weights exist in **two places on purpose**: the SQL view
(`v_at_risk_students`) scores whole cohorts in a set-based query, and
`services/analytics.py` explains one student. A test asserts the two
agree, so they cannot drift apart and make the dashboard contradict the
report.

---

## Security

This was the weakest part of the original project, and most of what
follows is fixed and covered by a test. One thing is a deliberate
trade-off rather than a fix — see the callout below the table.

| Threat | Before | Now |
|---|---|---|
| **Privilege escalation** | Role in `localStorage`; `localStorage.role = "admin"` worked | Role inside a signed JWT — editing it breaks the signature |
| **Broken access control (IDOR)** | `GET /student-data/7` returned anyone's marks | Student id read from the token; `require_self_or_staff` on every per-student route |
| **Unprotected admin panel** | `admin.html` protected only by not being linked | `@require_role("admin")` on every admin endpoint |
| **Password-reset takeover** | `/forgot-password` reset any password given only a username, no proof of ownership | Requires the username **and** the email on file to match; rate limited on the same budget as login |
| **Brute force** | Unlimited attempts | 5 per 5 minutes per user+IP, plus a durable `login_attempts` record |
| **SQL injection** | — | Every value parameterised; sort columns resolved through a whitelist |
| **Stored XSS** | `innerHTML` with database values | `textContent` throughout; `escapeHtml()` where a template is clearer |
| **Credentials in git** | `db_config.py` had the MySQL password committed | `.env`, gitignored, with `.env.example` as the template |
| **Guessable passwords** | Generated as `Name@123` | 12 random characters from `secrets`, not derived from the name |
| **Script injection** | No headers at all | Strict CSP with **no `unsafe-inline` in `script-src`** — injected script cannot execute. The one inline script (Swagger's bootstrap) carries a per-request nonce. Plus nosniff, `frame-ancestors 'none'`, `object-src 'none'`, Referrer-Policy, Permissions-Policy |
| **Cached sensitive responses** | — | `no-store` on every `/api/` response, so marks and credentials never reach the browser's disk cache |
| **Untraceable password reads** | — | Every `GET .../credentials` writes a `password.viewed` audit row naming the admin, student, time and IP. The row records *that* a lookup happened, never the secret |

> **Passwords are stored as plain text**, on purpose, in this build. It
> is run as a personal admin tool and the owner needs to read a
> student's password back directly — `GET /api/admin/students/{id}/credentials`
> — rather than only ever being able to issue a new one. That is a real
> trade-off, not an oversight: anyone who can read the `users` table
> reads every password with it. Comparisons still go through
> `hmac.compare_digest` (constant-time), which is free and closes the one
> side channel that storage format does not otherwise affect. See the
> docstring in `backend/security.py` for the full reasoning.

The app also refuses to start with `DEBUG=false` if the JWT secret is
still the development default, the database password is empty, or CORS is
set to `*`.

---

## API

Interactive documentation: **http://localhost:5000/api/docs**

Every endpoint except `/api/health`, `/api/auth/login` and
`/api/auth/forgot-password` requires `Authorization: Bearer <token>`.

```
POST   /api/auth/login                        exchange credentials for a JWT
GET    /api/auth/me                           the signed-in user
POST   /api/auth/change-password              requires the current password
POST   /api/auth/forgot-password              requires username + registered email

GET    /api/students/me                       your dashboard (id from the token)
GET    /api/students                          search / filter / sort / paginate (staff)
GET    /api/students/{id}                     full analytics (self or staff)
GET    /api/students/{id}/timeline            assessments over time + trend
GET    /api/students/{id}/comparison          your marks vs the class average
GET    /api/students/{id}/report-card[.csv]   grades, GPA, rank

GET    /api/analytics/cohort                  headline cohort numbers
GET    /api/analytics/at-risk                 ranked, with reasons
GET    /api/analytics/grade-distribution      students per grade band
GET    /api/analytics/subjects                per-subject pass rates

POST   /api/admin/students                    create student + login + enrollments
PATCH  /api/admin/students/{id}               update
DELETE /api/admin/students/{id}               soft delete
POST   /api/admin/students/{id}/reset-password
GET    /api/admin/students/{id}/credentials   look up the current username + password
POST   /api/admin/assessments                 record or correct one mark
POST   /api/admin/import/marks                bulk CSV, all-or-nothing
POST   /api/admin/import/attendance           bulk CSV
GET    /api/admin/export/cohort.csv           export
GET    /api/admin/audit-log                   audit trail (admin only)
POST   /api/admin/cohorts/promote             promote a semester
```

Errors are real HTTP status codes with one predictable shape — the
original answered every failure with `200 {"status": "fail"}`:

```json
{ "error": { "code": "forbidden", "message": "You can only view your own records" } }
```

---

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Run against a real MySQL database rather than a mock. That is
deliberate: most of the logic worth testing lives in SQL — the views
compute the percentages, the triggers reject bad marks. Mocking the
database would assert that Python calls a query while never checking the
query is correct, which is exactly where the bugs are.

The suite builds a `foresight_test` database from the same schema files
that ship with the project, so a schema change that breaks the app
breaks the tests too. It is dropped afterwards.

| File | Covers |
|---|---|
| `test_auth.py` | Login, tokens, tampering, expiry, password policy, forgot-password, rate limiting |
| `test_authorization.py` | Every route × every role, and the IDOR fix |
| `test_analytics.py` | Risk scoring, trends, and that SQL and Python agree |
| `test_data_integrity.py` | Triggers, constraints, CSV import, SQL injection |

CI runs the suite plus `ruff` on every push, and separately loads all
five SQL files into a clean MySQL to verify every view, trigger and
procedure still creates.

---

## Project layout

```
├── backend/
│   ├── app.py               application factory
│   ├── config.py            environment-driven settings
│   ├── db.py                connection pool, query helpers, transactions
│   ├── security.py          password checks, JWT, RBAC decorators, rate limiting
│   ├── validators.py        input validation
│   ├── errors.py            uniform JSON error handling
│   ├── json_provider.py     DECIMAL → number, dates → ISO 8601
│   ├── openapi.yaml         hand-written API specification
│   ├── seed_demo.py         demo dataset generator
│   ├── routes/              HTTP layer (6 blueprints)
│   ├── services/            business logic (analytics, imports, reports)
│   └── tests/               165 tests
│
├── database/
│   ├── schema.sql           tables, constraints, indexes
│   ├── views.sql            the analytical layer
│   ├── triggers.sql         validation + auditing
│   ├── procedures.sql       transactional operations
│   └── sample_data.sql      branches and subjects
│
├── frontend/
│   ├── index.html           sign in
│   ├── dashboard.html       student dashboard
│   ├── admin.html           admin console
│   ├── css/                 tokens · base · components · page styles
│   └── js/                  api · ui · charts · page scripts
│
├── .github/workflows/ci.yml
├── docker-compose.yml
└── Dockerfile
```

---

## What changed from v1

The first version was ~350 lines: one `app.py`, one stylesheet, five
empty SQL files. It worked as a demo. It also compared passwords with
`==` and no thought given to storage, and returned any student's marks
to anyone who asked.

**Database** — five empty files (`schema.sql`, `views.sql`,
`triggers.sql`, `procedures.sql`, `sample_data.sql`) now contain a real
schema with foreign keys, CHECK constraints and indexes, plus the views,
triggers and procedures the project was always meant to demonstrate.

**Backend** — one 218-line file became an application factory with
blueprints, a service layer, connection pooling, request-scoped
transactions with rollback, and uniform error handling.

**Security** — see [the table above](#security). Passwords remain plain
text by deliberate choice; everything else in that table is a fix,
covered by a test.

**Frontend** — a token-based design system, responsive layout,
accessible charts with legends and tooltips, toast notifications instead
of `alert()`, real loading and empty states, and XSS-safe rendering.

**New** — risk scoring, cohort ranking, trend detection, class
comparison, CSV import/export, report cards, an audit log, student
search, self-service password reset, an automated test suite, CI, Docker
and API docs.

### Bugs found and fixed while rebuilding

A few worth naming, because they were caught by actually running the
thing rather than by reading it:

- **DECIMAL serialised as a string.** MySQL returns `DECIMAL` as a Python
  `Decimal`, which Flask renders as `"44.82"`. Chart.js silently plots
  nothing for string values, and `"44.82" > 40` is *false* in JavaScript
  — wrong in a way that looks like it works. Fixed with a custom JSON
  provider.
- **Collation mismatch.** A `CASE` expression's string literals took the
  session's collation while the columns used the database's, so
  `WHERE risk_band IN ('high','medium')` failed at runtime for some
  callers and not others. Fixed by pinning the collation in the view.
- **`hidden` beaten by `display: flex`.** The admin console rendered all
  four tab panels stacked on top of each other, because an author rule
  outranks the user-agent stylesheet's `[hidden]`.
- **Contradictory risk explanation.** A student could be told "medium
  risk" and "meeting all academic requirements" in the same card,
  because the band uses a 55% warning threshold while the score only
  starts accumulating below 40%.
- **Empty "Why" column.** The admin overview used a code path that
  skipped the risk explanations, so the reason column rendered as dashes.

---

## Licence

MIT — see the repository root.
