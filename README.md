<div align="center">

# 📝 Inkwell

**A fast, private place to keep your notes.**

React 18 · Express · MySQL — JavaScript end to end, no Java/JSP/Tomcat left anywhere in the stack.

[![Node](https://img.shields.io/badge/node-%3E%3D20-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![React](https://img.shields.io/badge/frontend-React%2018-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Express](https://img.shields.io/badge/backend-Express-000000?logo=express&logoColor=white)](https://expressjs.com/)
[![MySQL](https://img.shields.io/badge/database-MySQL-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](#-run-with-docker)

</div>

> A note on the name: this project was previously called **E-Notes**. The MySQL database is still named `enotes` and the repo folder keeps its old name, deliberately — renaming either would mean migrating live data for no benefit. Only the product name changed.

---

## ✨ Features

- Register with **email verification** — a 6-digit code confirms the address before the account is created
- Sign in, sign out
- Dashboard with note counts and recent notes
- Write, edit, delete, **pin**, and **search** notes
- Show/hide control on password fields
- Single fixed dark theme, responsive down to mobile widths
- **Admin console** (ADMIN role only): site-wide totals, every account with role/notes/join date, promote/demote, delete accounts

One Express process serves both the JSON API and the built React app from the same origin — no CORS setup, nothing extra to run.

---

## 🧱 Tech Stack

| Layer     | Technology                                                            |
|-----------|------------------------------------------------------------------------|
| Frontend  | React 18 + React Router, built with Vite. Custom CSS design system, inline SVG icons — no UI framework, no CDN |
| Backend   | Node.js + Express, JSON REST API                                     |
| Database  | MySQL (`mysql2` driver, pooled)                                      |
| Sessions  | `express-session`, held in memory (no `sessions` table — a restart signs everyone out) |

---

## 🚀 Quick Start

Pick whichever fits — both are first-class, and **both can run at the same time** without stepping on each other's ports (see [Running Both at Once](#-running-both-at-once)).

> 📖 Prefer a step-by-step guide with admin credentials? See **[RUNNING.md](RUNNING.md)**.

Both need **MySQL running on your machine** — they share one database, so the same accounts and notes appear either way.

```bash
git clone <this-repo-url>
cd E-Notes

# 1. Create the database (tables are created for you at startup)
mysql -u root -p -e "CREATE DATABASE enotes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Configure credentials
copy server\.env.example server\.env      # macOS/Linux: cp
#    then edit server/.env and set DB_PASSWORD
```

### Option A — Terminal

Requires **Node.js 20+**.

```bash
npm run install:all
npm start
```

Open **http://localhost:3000/**

### Option B — Docker

Requires **Docker Desktop**. Node runs in the container; MySQL stays on your machine.

```bash
docker compose up --build
```

Open **http://localhost:3001/**

The first account registered on an empty database becomes the administrator.

<details>
<summary><strong>Development with hot reload</strong></summary>

<br>

Two terminals:

```bash
npm run dev:api    # Express, restarts on change — port 3000
npm run dev:web    # Vite dev server — port 5173
```

Use `http://localhost:5173/` while developing. Vite proxies `/api` to port 3000, so the same session and API are used while the UI reloads on save. These are also available as VS Code tasks (`Ctrl+Shift+P` → `Run Task` → `Inkwell: ...`).

</details>

---

## 🐳 Run with Docker

`docker-compose.yml` runs **one service** — the app. MySQL is not containerised: the app connects to the MySQL already on your machine, the same database a terminal run uses. Running under Docker therefore changes nothing about what the app does or what it shows.

Inside a container `localhost` means the container itself, so the app reaches your machine at `host.docker.internal:3306`.

**Configuration** — copy [`.env.example`](.env.example) to `.env` to override any default. Its defaults already match `server/.env`, so you only need it to change something.

```bash
docker compose up --build       # start (rebuilds the image if the code changed)
docker compose up -d            # start in the background
docker compose logs -f app      # follow the app's logs
docker compose down             # stop
```

In Docker Desktop it appears as `inkwell-app` under the **inkwell** project, so it can be started and stopped from there too.

---

## 🔀 Running Both at Once

The app ports differ, so a terminal run and a Docker run can be up simultaneously:

| | Terminal | Docker |
|---|---|---|
| App | `localhost:3000` | `localhost:3001` |
| Database | `localhost:3306` | the same `localhost:3306` |

Because both talk to one database, an account created or a note written on either port is immediately visible on the other. Change the Docker port with `APP_PORT` in the root `.env`.

---

## ⚙️ Configuration Reference

Terminal runs read `server/.env` ([`server/.env.example`](server/.env.example)); Docker Compose reads the root `.env` ([`.env.example`](.env.example)). Same variables, different file.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Port Express listens on *inside* its process/container |
| `APP_URL` | `http://localhost:$PORT` | Absolute base URL this instance is reached at |
| `DB_HOST` / `DB_PORT` | `localhost` / `3306` | MySQL connection (Docker: `db` / `3306`, set automatically) |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | `root` / — / `enotes` | MySQL credentials |
| `SESSION_SECRET` | dev fallback | Signs the session cookie — **set a long random value before deploying** |
| `COOKIE_SECURE` | on when `NODE_ENV=production` | Marks the session cookie HTTPS-only. Must be `false` over plain HTTP, or sign-in silently never sticks |

Run `npm run check` (terminal) or `docker compose exec app node src/check-config.js` (Docker) at any time for a report of what's configured and what looks wrong.

---

## 📡 API Reference

All endpoints return JSON. Auth is a session cookie; every write additionally requires the session's CSRF token in an `X-CSRF-Token` header.

<details>
<summary><strong>Full endpoint list</strong></summary>

<br>

```
GET    /api/auth/session              current user + CSRF token
POST   /api/auth/register             step 1: validate + email a 6-digit code
POST   /api/auth/verify-otp           step 2: confirm the code, create account
POST   /api/auth/resend-otp           issue a fresh code (60s cooldown)
POST   /api/auth/login                sign in
POST   /api/auth/logout               sign out

GET    /api/notes                     list notes; optional ?q= search
POST   /api/notes                     create
GET    /api/notes/{id}                fetch one
PUT    /api/notes/{id}                update
DELETE /api/notes/{id}                delete
POST   /api/notes/{id}/pin            toggle pinned

GET    /api/stats                     the signed-in user's counters

GET    /api/admin/users               all accounts             (ADMIN)
GET    /api/admin/stats               site-wide totals         (ADMIN)
PATCH  /api/admin/users/{id}/role     set USER or ADMIN        (ADMIN)
DELETE /api/admin/users/{id}          delete an account        (ADMIN)
```

Status codes: `401` not signed in · `403` signed in but not permitted (including a missing/wrong CSRF token) · `404` for a note that doesn't exist *or* belongs to someone else (deliberately indistinguishable) · `400` validation failure · `409` duplicate email.

</details>

---

## 👤 Roles

Each account is `USER` or `ADMIN`. The **first account ever registered becomes ADMIN**; everyone after is `USER`. Two rules make lockout impossible, enforced server-side:

- An admin cannot change their own role
- An admin cannot delete their own account

Together these guarantee at least one administrator always remains.

---

## 🔐 Security Notes

> **⚠️ Known and deliberate exception — passwords are stored in plain text.**
> This is an explicit project choice, not an oversight. Anyone who can read the `user` table obtains every account's real password. **Do not reuse a real password here, and do not deploy this build on a public network as-is.** To reverse it, hash on write and verify on read in `server/src/routes/auth.js` — the column is already `VARCHAR(255)`, wide enough for a hash.

Everything else is enforced:

- Every note query is scoped by owner id — a note can't be read, edited, or deleted by anyone but its author
- The API is the authorization boundary (Express middleware on `/api`), not the React route guards, which are convenience only
- Authorization is re-read from the database on every request — a deleted account's session stops working immediately
- Every state-changing request requires a valid per-session CSRF token
- Sign-in regenerates the session id (session-fixation defence); the cookie is `HttpOnly`, `SameSite=Lax`, and `Secure` automatically once `NODE_ENV=production`
- Every SQL statement uses bound parameters; `LIKE` wildcards in search terms are escaped
- Sign-in failures give one identical message for every cause, so responses can't be used to enumerate accounts
- Registration codes are generated with `crypto.randomInt`, compared in constant time, single-use, expire in 10 minutes, and are burned after 5 wrong guesses — a 6-digit code is otherwise only a million tries from being brute-forced
- An unconfirmed signup lives in `pending_registration`, never in `user`, so an unverified address never becomes an account or squats an email someone else may be entitled to register

---

## 🗂️ Project Structure

```
server/                       Node + Express API and static host
  src/index.js                 App bootstrap, middleware order, startup
  src/config.js                Environment configuration
  src/db.js                    MySQL connection pool
  src/schema.js                Creates/upgrades the schema at startup
  src/userView.js               The user shape sent to the client
  src/middleware/security.js    CSRF, requireAuth, requireAdmin
  src/routes/                   auth.js, notes.js, stats.js, admin.js
  .env                          Your credentials (gitignored)

frontend/                     React single-page app (Vite)
  src/main.jsx                 Bootstrap (Router + AuthProvider)
  src/App.jsx                  Routes and auth/admin route guards
  src/api.js                   fetch wrapper: cookies + CSRF header
  src/components/, src/pages/   UI

db/schema.sql                 Reference schema for a fresh database
docker-compose.yml            App + MySQL stack
Dockerfile                    Multi-stage build (Vite → Express runtime)
package.json                  Root scripts that drive both halves
```

---

## 🛠️ Troubleshooting

| Symptom | Cause |
|---|---|
| `ECONNREFUSED` or schema warnings at startup | MySQL isn't running, or the credentials in `server/.env` / root `.env` are wrong. The server still starts so it can report the problem clearly |
| Blank page, or 404s for `/assets/*` | Front end hasn't been built — run `npm run build`, or use `npm start` |
| `EADDRINUSE: address already in use` | Something else holds the port — stop it, or change `PORT` (terminal) / `APP_PORT` (Docker) |
| "Invalid or missing security token" | Session expired — reload and try again |
| Locked out of the admin console | No account has `ADMIN`. Run `UPDATE user SET role = 'ADMIN' WHERE email = '...';`, then restart |
| Signed in, then immediately signed out | `COOKIE_SECURE` is `true` while you're on plain HTTP — set it to `false` for local use. `npm run check` flags this |

See **[RUNNING.md](RUNNING.md)** for the full run guide, both ways, plus admin credentials.

---

<div align="center">

Built with Node.js, React, and MySQL — no Java, JSP, Servlet, Tomcat, Maven, or WAR anywhere in this project.

</div>
