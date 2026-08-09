====================================================================
 Inkwell
====================================================================

Inkwell is a note-taking web application. Users register, sign in,
and can write, search, pin, edit, and delete their own notes.
Administrators additionally get a console for managing accounts.

Every note belongs to exactly one user, enforced both by a foreign
key and by owner-scoped queries in the data layer.

A note on the name: this project was previously called E-Notes. The
MySQL database is still named `enotes`, deliberately - renaming it
would mean migrating live data for no benefit. The repository folder
keeps its old name for the same reason. Only the product name
changed.


--------------------------------------------------------------------
 Technologies Used
--------------------------------------------------------------------
Front-End: React 18 + React Router, built with Vite. Custom CSS
           design system, inline SVG icons - no UI framework, no CDN.
Back-End:  Node.js + Express, exposing a JSON REST API
Database:  MySQL (mysql2 driver, pooled)
Sessions:  express-session, stored in MySQL

There is no Java, JSP, Servlet, Tomcat, Maven or WAR anywhere in this
project any more. The stack is JavaScript end to end; the only thing
carried over from the previous version is the MySQL schema, which is
unchanged apart from the new `role` column.

One Express process serves both the API and the built React app from
the same origin, so there is no CORS setup and nothing extra to run.


--------------------------------------------------------------------
 Features
--------------------------------------------------------------------
- Register / sign in / sign out
- Sign in with Google (optional; see Google Sign-In below)
- Account-setup email after a Google signup, with a one-time link for
  setting a password
- Dashboard with note counts and recent notes
- Write, edit, and delete notes
- Pin notes so they sort to the top
- Search across note titles and bodies
- Show/hide control on password fields
- Single fixed dark theme, responsive down to mobile widths

Administrator console (ADMIN role only)
- Site-wide totals: users, administrators, notes, pinned notes
- Every account listed with its role, note count and join date
- Promote a user to ADMIN or demote them back
- Delete an account, which deletes that user's notes with it


--------------------------------------------------------------------
 Google Sign-In and the account-setup email
--------------------------------------------------------------------
Both are optional and both are OFF until you configure them. Nothing
else in the app depends on either.

How it works
  1. "Continue with Google" appears on the sign-in and register pages
     only when the server reports a configured client id, so it is
     never a button that cannot work.
  2. Google returns an ID token to the browser, which posts it to
     /api/auth/google. The server verifies that token against
     Google's public keys and checks it was issued for this app. A
     token the browser merely claims is valid is never believed.
  3. If the email is new, an account is created (role USER, no
     password) and an account-setup email is sent.
  4. If the email already has a password account, Google is linked to
     that existing account instead of creating a second one.
  5. The email contains a one-time link to /account-setup?token=...
     The link expires in 24 hours and stops working once used. Setting
     a password there lets the person sign in either way afterwards.

Until a password is set, a Google account cannot be signed into with
an email and password - the stored password is NULL and is never
treated as matching anything.

Switching on Google sign-in
  Set GOOGLE_CLIENT_ID in server/.env. server/.env.example has the
  step-by-step for creating one in Google Cloud Console. Add
  http://localhost:3000 as an authorised JavaScript origin. No client
  secret is needed, because this verifies ID tokens rather than
  running a redirect flow.

Switching on real email
  Set MAIL_HOST / MAIL_USER / MAIL_PASSWORD in server/.env. For Gmail
  you need an App Password, not the account password.

  With MAIL_HOST blank (the default) nothing is sent - the whole
  message, including the setup link, is printed to the server console.
  That is enough to click through the flow locally. A failure to send
  never fails the signup that triggered it.


--------------------------------------------------------------------
 Roles
--------------------------------------------------------------------
Each account is either USER or ADMIN, held in user.role.

  - The FIRST account to register becomes ADMIN. Every account after
    that is a USER. This applies to Google signups too.
  - Upgrading an existing database: if no administrator exists,
    startup promotes the oldest account and logs that it did so.
    It never changes anything when an admin already exists.
  - A user cannot make themselves an admin. The role is only ever
    read from the database, never from a request body; sending
    "role":"ADMIN" to the register endpoint is ignored.

Two rules make lockout impossible, enforced on the server (the UI
also disables the corresponding buttons):

  - An admin cannot change their own role.
  - An admin cannot delete their own account.

Together these guarantee at least one administrator always remains,
because the acting admin necessarily survives their own request.


--------------------------------------------------------------------
 API
--------------------------------------------------------------------
All endpoints return JSON. Authentication is the session cookie;
writes additionally require the session's CSRF token in an
X-CSRF-Token header (a header, not a form field, because the bodies
are JSON and so carry no form parameters).

  GET    /api/auth/session      current user + CSRF token; returns
                                {"user": null} when signed out
  POST   /api/auth/register     create an account
  POST   /api/auth/login        sign in
  POST   /api/auth/logout       sign out
  POST   /api/auth/google       sign in / register with a Google ID
                                token (503 if not configured)
  GET    /api/auth/setup-token/{token}   check a setup link
  POST   /api/auth/setup-password        consume it and set a password

  GET    /api/notes             list; optional ?q= search
  POST   /api/notes             create
  GET    /api/notes/{id}        fetch one
  PUT    /api/notes/{id}        update
  DELETE /api/notes/{id}        delete
  POST   /api/notes/{id}/pin    toggle pinned

  GET    /api/stats             the signed-in user's counters

  GET    /api/admin/users       all accounts             (ADMIN)
  GET    /api/admin/stats       site-wide totals         (ADMIN)
  PATCH  /api/admin/users/{id}/role   set USER or ADMIN  (ADMIN)
  DELETE /api/admin/users/{id}  delete an account        (ADMIN)

Status codes: 401 not signed in, 403 signed in but not permitted
(including a missing or wrong CSRF token), 404 for a note that does
not exist *or* belongs to someone else (deliberately
indistinguishable), 400 for validation failures, 409 duplicate email.


--------------------------------------------------------------------
 Security
--------------------------------------------------------------------
KNOWN AND DELIBERATE EXCEPTION - PASSWORD STORAGE

  Passwords are stored in the database as plain text, by explicit
  project choice. Anyone who can read the user table - through a
  leaked backup, a SQL injection elsewhere, or shared access to the
  machine - therefore obtains every account's real password. Because
  people reuse passwords, that exposure is not limited to this
  application.

  Do not use this build with passwords anyone actually uses
  elsewhere, and do not deploy it on a public network as-is.

  To reverse this, hash on write and verify on read in
  server/src/routes/auth.js (register and login). The column is
  already VARCHAR(255), wide enough for a hash, so no schema change
  is needed.

Everything else below is enforced:

- Every note query is scoped by owner id, so a note cannot be read,
  edited, or deleted by anyone but its author - changing the id in a
  URL simply reports "not found".
- The author of a new note is taken from the session, not from the
  request body, so a note cannot be filed under another account.
- Access is enforced by Express middleware on /api, so protection
  cannot be omitted when an endpoint is added. The React route guards
  are a convenience only - the API is the boundary and is checked on
  every call, whatever the client chooses to render.
- Authorisation is re-read from the database on every API request.
  A deleted account's session stops working immediately, and an
  administrator who is demoted loses admin access on their very next
  request rather than when their session eventually expires.
- Every state-changing method (POST, PUT, PATCH, DELETE) requires a
  valid per-session CSRF token.
- Sign-in regenerates the session id (session fixation defence).
- The session cookie is HttpOnly and SameSite=Lax, and becomes
  Secure automatically when NODE_ENV=production.
- User text is escaped on render by JSX interpolation, so note
  content containing markup is displayed, not executed. The app never
  uses dangerouslySetInnerHTML.
- Every SQL statement uses bound parameters. LIKE wildcards in a
  search term are escaped, so % and _ are searched for literally.
- Sign-in failures give one message for every cause - unknown email,
  wrong password, or a Google account with no password yet - so the
  response cannot be used to enumerate accounts or discover how
  someone signed up.
- Google ID tokens are verified server-side against Google's public
  keys and checked to be issued for this application. A forged or
  self-signed token is rejected and creates no account.
- Account-setup links are 32 random bytes, single-use, and expire in
  24 hours. Using one clears it in the same statement that sets the
  password.
- Server errors are logged but never returned to the client.


--------------------------------------------------------------------
 Project Structure
--------------------------------------------------------------------
server/                     Node + Express API and static host
  src/index.js              App bootstrap, middleware order, startup
  src/config.js             Environment configuration
  src/db.js                 MySQL connection pool
  src/schema.js             Creates/upgrades the schema at startup
  src/mailer.js             Outgoing email; logs to console without SMTP
  src/userView.js           The user shape sent to the client
  src/middleware/security.js  CSRF, requireAuth, requireAdmin,
                              per-request session refresh
  src/routes/auth.js        /api/auth/*
  src/routes/notes.js       /api/notes/*
  src/routes/stats.js       /api/stats
  src/routes/admin.js       /api/admin/*
  .env                      Your credentials (gitignored)
  .env.example              Template

frontend/                   React single-page app
  index.html                Vite entry point
  vite.config.js            Build config; dev-server proxy to the API
  src/main.jsx              Bootstrap (Router + AuthProvider)
  src/App.jsx               Routes and the auth/admin route guards
  src/api.js                fetch wrapper: cookies + CSRF header
  src/auth.jsx              Auth context; resolves session on load
  src/styles.css            The whole design system
  src/components/           Icon, Navbar, Alert, PasswordInput,
                            NoteCard, GoogleButton
  src/pages/                Landing, Login, Register, Dashboard,
                            Notes, NoteEditor, Admin, AccountSetup,
                            NotFound

db/schema.sql               Reference schema for a fresh database
package.json                Root scripts that drive both halves


--------------------------------------------------------------------
 Prerequisites
--------------------------------------------------------------------
- Node.js 20 or newer (includes npm)
- MySQL Server running locally

That is the whole list. No JDK, no Maven, no Tomcat.


--------------------------------------------------------------------
 Setup
--------------------------------------------------------------------
1. Create the database (the tables are created for you at startup):

     CREATE DATABASE enotes
         CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

2. Configure credentials:

     copy server\.env.example server\.env

   then edit server/.env and set DB_PASSWORD (and SESSION_SECRET if
   you are deploying). server/.env is gitignored.

3. Install dependencies:

     npm run install:all

4. Start it:

     npm start

   Then open http://localhost:3000/

   The first account you register becomes the administrator.


--------------------------------------------------------------------
 Database Setup Detail
--------------------------------------------------------------------
server/src/schema.js runs on every startup and brings the schema up
to date. Each step is guarded by an existence check, so it is safe to
run repeatedly: a fresh database is created, an older one is upgraded
in place, and a current one is left alone. It will, as needed:

  - create the user and post tables
  - widen user.password to VARCHAR(255)
  - widen user.email and add a UNIQUE constraint on it
  - add user.created_at and user.role
  - make user.password nullable (Google accounts have none until the
    holder sets one)
  - add user.google_id (unique), user.email_verified,
    user.setup_token and user.setup_token_expires
  - widen post.title to VARCHAR(200)
  - convert post.content to TEXT (it was VARCHAR(45), which silently
    truncated almost every real note)
  - rename post.date to post.created_at, preserving the data
  - add post.pinned and post.updated_at
  - add the (uid, pinned, created_at) listing index
  - promote the oldest account to ADMIN if no admin exists

If the user table already contains duplicate emails, the unique
constraint is skipped and a warning is logged rather than deleting
rows; remove the duplicates and restart to finish the upgrade.

A `sessions` table is also created automatically at runtime by
express-mysql-session.

db/schema.sql is the authoritative reference and can set up a fresh
database by hand:

    mysql -u root -p < db/schema.sql


--------------------------------------------------------------------
 Running the Project
--------------------------------------------------------------------
From the project root:

    npm run install:all   Install both halves' dependencies (once)
    npm start             Build the front end, then serve everything
    npm run serve         Serve without rebuilding the front end
    npm run build         Build the front end only
    npm run check         Report what is configured and what is missing

    Then open: http://localhost:3000/

The same commands are available as VS Code tasks:
Ctrl+Shift+P -> Run Task -> Inkwell: ...


Development with hot reload (optional)
--------------------------------------
Two terminals:

    npm run dev:api    Express, restarts on change (port 3000)
    npm run dev:web    Vite dev server (port 5173)

Then use http://localhost:5173/ while developing. Vite proxies /api
to port 3000, so the same session and API are used while the UI
reloads on save. The built app is same-origin and needs no proxy.


--------------------------------------------------------------------
 Troubleshooting
--------------------------------------------------------------------
- "ECONNREFUSED" or schema warnings at startup: MySQL isn't running,
  or the credentials in server/.env are wrong. The server still
  starts so it can report the problem clearly.
- Blank page, or 404s for /assets/*: the front end has not been
  built. Run `npm run build`, or use `npm start` which does it.
- "EADDRINUSE: address already in use :::3000": something else holds
  the port. Stop it, or set PORT in server/.env.
- "Invalid or missing security token": the page sat open long enough
  for the session to expire. Reload and try again.
- Locked out of the admin console: no account has the ADMIN role.
  Set one directly, then restart:
      UPDATE user SET role = 'ADMIN' WHERE email = 'you@example.com';
- Cannot promote or delete yourself: that is deliberate. Use another
  administrator account, or the SQL above.
- No "Continue with Google" button: GOOGLE_CLIENT_ID is not set in
  server/.env, so it is hidden on purpose. Restart after setting it.
- Google sign-in returns "could not be verified": the client id in
  server/.env does not match the one that issued the token, or
  http://localhost:3000 is not listed as an authorised JavaScript
  origin on that OAuth client.
- No setup email arrives: with MAIL_HOST blank the message is printed
  to the server console instead - look there for the link.
- Setup link says invalid or expired: they are single-use and last 24
  hours. Sign in with Google again to be issued a new one.


--------------------------------------------------------------------
 Accounts on this installation
--------------------------------------------------------------------
  admin_info@gmail.com / 1234   ADMIN - the administrator account
  bhargavagarv12347890@gmail.com / 123   USER

Note that 1234 and 123 are shorter than the 8-character minimum the
registration form enforces. Both were set directly in the database,
which does not go through that validation. Sign-in has no length
requirement, so they work.
