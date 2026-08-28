# Foresight

Academic analytics for a college. Marks and attendance go in; a ranked,
**explained** view of which students need help comes out — while there is
still time to act on it.

Built with Flask, MySQL 8 and vanilla JavaScript. JWT authentication,
role-based access control, an audited database, 165 automated tests and
a one-command Docker setup.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Browser    │────▶│  Flask API   │────▶│     MySQL 8      │
│  (no build) │ JWT │  blueprints  │ SQL │  views·triggers  │
│             │◀────│  + services  │◀────│   procedures     │
└─────────────┘     └──────────────┘     └──────────────────┘
```

---

## Documentation

| File | What it covers |
|---|---|
| **README.md** (this file) | What the project is, how it is built, why |
| **[setup.txt](setup.txt)** | Complete first-time setup, both methods, troubleshooting |
| **[RUNNING.md](RUNNING.md)** | Day-to-day operation: start, stop, logs, reset |
| **[MySQL Code.txt](MySQL%20Code.txt)** | Every SQL object in one listing |
| **[../Documentation/](../Documentation/)** | Project reports (.docx) |

---

## Run it

**Docker — nothing to install:**

```bash
cd Foresight
docker compose up --build
```

**Then open → http://localhost:5000**

That is the only port you need. MySQL is also published on **3307** for a
GUI client. Both ports are fixed.

Sign in as `admin` / `Admin@2024`.

Full instructions, including running it without Docker, are in
**[setup.txt](setup.txt)**.

---

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [The database](#the-database)
- [How risk scoring works](#how-risk-scoring-works)
- [Security](#security)
- [API](#api)
- [Testing](#testing)
- [Project layout](#project-layout)

---

## What it does

**For a student** — one dashboard: marks, attendance, class rank and
percentile, how each subject compares to the class average, whether they
are improving or slipping, and a plain-English explanation of their
academic standing with suggested next steps.

**For faculty and administrators** — cohort statistics, grade
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
| **RBAC** | Three roles enforced on every endpoint — a student cannot read another student's records |
| **API docs** | Interactive Swagger UI at `/api/docs` |

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

The views build in layers, each consuming the last:

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
radius, and nothing below it hardcodes a value.

---

## The database

Nine tables, six views, eight triggers, five procedures and two
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
A flat `marks` column makes trend analysis impossible. Each assessment
carries its own `max_marks`, so a 20-mark quiz and a 100-mark final
coexist and the subject percentage is `SUM(obtained)/SUM(max)` —
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
-- Rejected, even typed directly into the MySQL console:
INSERT INTO assessments (enrollment_id, type, marks_obtained, max_marks, assessed_on)
VALUES (1, 'quiz', 99, 20, '2025-01-01');
-- ERROR 1644 (45000): marks_obtained cannot exceed max_marks
```

---

## How risk scoring works

A student is not simply "weak". The score is 0–100, built from four
weighted signals so students can be **ranked** by how much attention they
need rather than merely filtered:

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

A student with no marks yet scores 0 in the `unknown` band rather than
looking like a top performer — `AVG` of nothing is `NULL`, and treating
that as zero is a bug waiting to happen.

---

## Security

Every item below is covered by a test.

| Control | How |
|---|---|
| **Authentication** | Signed JWT carrying role and student id; a tampered claim fails verification |
| **Authorisation** | Role decorator on every endpoint; three roles |
| **Object-level access** | Student id read from the token, never the URL; `require_self_or_staff` on every per-student route |
| **Brute force** | 5 attempts per 5 minutes per user+IP, plus a durable `login_attempts` record |
| **Password reset** | Requires username **and** the email on file; rate limited |
| **SQL injection** | Every value parameterised; sort columns resolved through a whitelist |
| **Stored XSS** | `textContent` throughout; `escapeHtml()` where a template is clearer |
| **Script injection** | Strict CSP with **no `unsafe-inline` in `script-src`** — injected script cannot execute. The one inline script (Swagger's bootstrap) carries a per-request nonce |
| **Response caching** | `no-store` on every `/api/` response, so marks and credentials never reach the browser's disk cache |
| **Secrets** | `.env`, gitignored, with `.env.example` as the template |
| **Generated passwords** | 12 random characters from `secrets`, never derived from the name |

The app refuses to start with `DEBUG=false` if the JWT secret is still
the development default, the database password is empty, or CORS is `*`.

### Password storage — a deliberate trade-off

**Passwords are stored as plain text in this build.** It is run as a
personal admin tool where the operator needs to read a student's existing
password back, not merely issue a new one, so
`GET /api/admin/students/{id}/credentials` returns it.

The consequence is stated plainly: anyone who can read the `users` table
reads every password with it.

Two compensating measures apply. Comparison uses `hmac.compare_digest`,
which is constant-time and closes a timing side channel regardless of
storage format. More importantly, **every password read is audited** with
the administrator, the student, the time and the IP. Plain storage gives
up the guarantee that a password cannot be read; auditing preserves the
guarantee that it cannot be read *anonymously*. The audit row records
that a lookup happened, never the secret.

Switching to a salted hash is a one-function change in
`backend/security.py`.

---

## API

Interactive documentation: **http://localhost:5000/api/docs**

36 endpoints. Everything except `/api/health` and `/api/auth/login`
requires `Authorization: Bearer <token>`.

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
GET    /api/admin/students/{id}/credentials   look up username + password (audited)
POST   /api/admin/students/{id}/reset-password
POST   /api/admin/assessments                 record or correct one mark
POST   /api/admin/import/marks                bulk CSV, all-or-nothing
POST   /api/admin/import/attendance           bulk CSV
GET    /api/admin/export/cohort.csv           export
GET    /api/admin/audit-log                   audit trail (admin only)
POST   /api/admin/cohorts/promote             promote a semester
```

Errors are real HTTP status codes with one predictable shape:

```json
{ "error": { "code": "forbidden", "message": "You can only view your own records" } }
```

---

## Testing

```bash
cd Foresight/backend
pytest
```

**165 tests**, run against a real MySQL database rather than a mock.
That is deliberate: most of the logic worth testing lives in SQL — the
views compute the percentages, the triggers reject bad marks. Mocking the
database would assert that Python calls a query while never checking the
query is correct, which is exactly where the bugs are.

The suite builds a `foresight_test` database from the same schema files
that ship with the project, so a schema change that breaks the app breaks
the tests too. It is dropped afterwards.

| File | Covers |
|---|---|
| `test_auth.py` | Passwords, tokens, tampering, expiry, policy, rate limiting |
| `test_authorization.py` | Every route × every role, object-level access, security headers |
| `test_analytics.py` | Risk scoring, trends, and that SQL and Python agree |
| `test_data_integrity.py` | Triggers, constraints, CSV import, timestamps, injection |

CI runs the suite plus `ruff` on every push, and separately loads all
five SQL files into a clean MySQL to verify every view, trigger and
procedure still creates.

---

## Project layout

```
Foresight/
├── backend/
│   ├── app.py               application factory
│   ├── config.py            environment-driven settings
│   ├── db.py                connection pool, query helpers, transactions
│   ├── security.py          passwords, JWT, RBAC decorators, rate limiting
│   ├── security_headers.py  CSP and related HTTP headers
│   ├── validators.py        input validation
│   ├── errors.py            uniform JSON error handling
│   ├── json_provider.py     DECIMAL → number, timestamps → ISO 8601 with offset
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
├── docker-compose.yml       MySQL + API, fixed on ports 5000 and 3307
├── Dockerfile
├── setup.txt                complete setup guide
├── RUNNING.md               operational runbook
└── MySQL Code.txt           all SQL in one listing
```

The CI workflow lives at `../.github/workflows/ci.yml` — GitHub only
reads workflows from the repository root, so it sits one level above this
directory and reaches down into it.

---

## Licence

MIT — see the repository root.
