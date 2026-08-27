# How to Run Inkwell

Two ways to run this project. **Both use the same MySQL database**, so the same
accounts and the same notes appear either way — and both can run at once,
because the ports differ.

| | Terminal | Docker |
|---|---|---|
| **App** | http://localhost:3000 | http://localhost:3001 |
| **Runs** | Node on your machine | Node in a container |
| **Database** | your local MySQL — **the same one** | |
| **Needs** | Node 20+, MySQL | Docker Desktop, MySQL |

MySQL runs on your machine in both cases. Docker containerises the *app*, not
the database, so switching between the two never changes what you see.

---

## Option 1 — Terminal

```bash
cd E-Notes
npm run install:all          # once
npm start
```

Open **http://localhost:3000/**

### Everyday commands

```bash
npm start           # build the front end, then serve everything
npm run serve       # serve without rebuilding the front end
npm run build       # build the front end only
npm run check       # report what is configured and what is missing
```

### Development with hot reload

Two terminals:

```bash
npm run dev:api     # Express, restarts on change — port 3000
npm run dev:web     # Vite dev server — port 5173
```

Use **http://localhost:5173/** while developing. Vite proxies `/api` to port
3000, so you keep the same session and API while the UI reloads on save.

---

## Option 2 — Docker

```bash
cd E-Notes
docker compose up --build
```

Open **http://localhost:3001/**

The container reaches your MySQL at `host.docker.internal:3306` — inside a
container, `localhost` means the container itself, so that name is how Docker
exposes the machine it is running on.

### Everyday commands

```bash
docker compose up -d --build    # start in the background
docker compose ps               # status and health
docker compose logs -f app      # follow the log (registration codes appear here)
docker compose down             # stop
```

`npm run docker:up`, `npm run docker:down`, and `npm run docker:logs` are
shortcuts for the same things.

In **Docker Desktop** it appears as `inkwell-app` under the `inkwell` project,
so you can start and stop it with the ▶ / ■ buttons.

---

## First-time setup

Needed once, for either option.

**1. Create the database**

```sql
CREATE DATABASE enotes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Tables are created automatically at startup.

**2. Configure credentials**

```bash
copy server\.env.example server\.env      # macOS/Linux: cp
```

Edit `server/.env` and set `DB_PASSWORD` to your MySQL password.

Docker reads the root `.env` instead (copy `.env.example`), but its defaults
already match `server/.env`, so you only need it to change something.

**3. Install dependencies**

```bash
npm run install:all
```

---

## Accounts

| Email | Password | Role |
|---|---|---|
| `admin_info@gmail.com` | `1234` | ADMIN |
| `bhargavagarv12347890@gmail.com` | `123` | USER |

These work on **both** ports, because there is one database.

`1234` and `123` are shorter than the 8-character minimum registration
enforces — both were set directly in the database, which skips that validation.
Sign-in has no length requirement, so they still work.

> These passwords are stored in the database **as plain text**, by explicit
> project choice. Never reuse a real password here.

### Making someone an admin

```sql
UPDATE user SET role = 'ADMIN' WHERE email = 'you@example.com';
```

Restart afterwards. An admin cannot change their own role or delete their own
account — that is deliberate, and guarantees at least one admin always
survives. If a database somehow ends up with no admin at all, startup promotes
the oldest account and logs that it did so.

### Resetting a password

```sql
UPDATE user SET password = 'newpassword' WHERE email = 'you@example.com';
```

---

## Registering a new account

Signing up takes two steps, because the address is confirmed before the account
exists:

1. `/register` → name, email, password → **Continue**
2. A 6-digit code is emailed → enter it → **Verify and create account**
3. You are redirected to `/login` to sign in

Nothing is written to the `user` table until the code is accepted.

**Where is the code?** With `MAIL_HOST` unset (the default) no mail is sent —
the code is printed to the server console instead:

- Docker: `docker compose logs app --tail 30`
- Terminal: the window running `npm start`

**To send real email**, set these and restart (Gmail needs a 16-character App
Password, not your account password):

```
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USER=you@gmail.com
MAIL_PASSWORD=your16charapppassword
MAIL_FROM=Inkwell <you@gmail.com>
```

Codes expire in 10 minutes, allow 5 wrong guesses, and can be resent once a
minute. `npm run check` reports whether email is configured.

---

## Troubleshooting

**"Invalid email or password" for an account you can see in MySQL**
Check `DB_NAME` / `DB_HOST` actually point at the database you are looking at.
Both run modes should use the same one.

**Port already in use**
Change `PORT` in `server/.env` (terminal) or `APP_PORT` in the root `.env`
(Docker).

**`ECONNREFUSED` at startup**
MySQL is not running, or the credentials are wrong. Run `npm run check`.

**Docker cannot reach MySQL**
MySQL must be running on your machine and accepting connections. Test it:

```bash
docker compose exec app node -e "require('mysql2/promise').createConnection({host:'host.docker.internal',user:'root',password:'1234',database:'enotes'}).then(()=>console.log('OK')).catch(e=>console.log(e.code))"
```

**Blank page or 404s for `/assets/*`**
The front end has not been built. Run `npm run build`, or use `npm start`.

**Signed in, then immediately signed out**
`COOKIE_SECURE` is `true` while you are on plain `http://`. A Secure cookie is
dropped over HTTP, so the session never sticks. Set `COOKIE_SECURE=false`.
`npm run check` flags this.

**Everyone signed out after a restart**
Expected. Sessions are held in memory, not in the database, so restarting the
server discards them.
