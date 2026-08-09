====================================================================
 E-Notes
====================================================================

E-Notes is a note-taking web application. Users register, sign in,
and can write, search, pin, edit, and delete their own notes. Every
note belongs to exactly one user, enforced both by a foreign key and
by owner-scoped queries in the data layer.


--------------------------------------------------------------------
 Technologies Used
--------------------------------------------------------------------
Front-End: React 18 + React Router (Vite build), custom CSS design
           system, inline SVG icons - no UI framework, no CDN
Back-End:  Java Servlets (javax.servlet 4.0) exposing a JSON REST
           API, JDBC, MySQL
JSON:      Jackson
Pooling:   HikariCP
Build:     Maven (drives the npm build too - one command)
Server:    Apache Tomcat 9.x (NOT 10+ - see Compatibility below)

The front end was migrated from JSP to React. The database schema and
the whole data layer (DBConnect, UserDAO, PostDAO, the models) carried
over unchanged; the servlets became JSON endpoints instead of
forwarding to pages, and the JSPs were replaced by React components.

React and the API ship in a single WAR and are served from one origin,
so there is no CORS setup and nothing extra to run.


--------------------------------------------------------------------
 Features
--------------------------------------------------------------------
- Register / sign in / sign out
- Dashboard with note counts and recent notes
- Write, edit, and delete notes
- Pin notes so they sort to the top
- Search across note titles and bodies
- Show/hide control on password fields
- Single fixed dark theme
- Responsive layout down to mobile widths


--------------------------------------------------------------------
 API
--------------------------------------------------------------------
All endpoints return JSON. Authentication is the Tomcat session
cookie; writes additionally require the session's CSRF token in an
X-CSRF-Token header (a header, not a form field, because the bodies
are JSON and so carry no request parameters).

  GET    /api/auth/session     current user + CSRF token; returns
                               {"user": null} when signed out
  POST   /api/auth/register    create an account
  POST   /api/auth/login       sign in
  POST   /api/auth/logout      sign out

  GET    /api/notes            list; optional ?q= search
  POST   /api/notes            create
  GET    /api/notes/{id}       fetch one
  PUT    /api/notes/{id}       update
  DELETE /api/notes/{id}       delete
  POST   /api/notes/{id}/pin   toggle pinned

  GET    /api/stats            dashboard counters

Status codes: 401 when not signed in, 403 when the CSRF token is
missing or wrong, 404 for a note that does not exist *or* belongs to
someone else (the two are deliberately indistinguishable), 400 for
validation failures.


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
  com/DAO/UserDAO.java (addUser and loginUser). The column is already
  VARCHAR(255), which is wide enough for a hash, so no schema change
  is needed.

Everything else below is enforced. Each replaced a real weakness in
the original version:

- Every note query is scoped by owner id, so a note cannot be read,
  edited, or deleted by anyone but its author - changing the id in a
  URL simply reports "not found".
- The author of a new note is taken from the session, not from the
  request body, so a note cannot be filed under another account.
- Access is enforced by a servlet filter on /api/*, so protection
  cannot be omitted when an endpoint is added. The React route guards
  are a convenience only - the API is the boundary, and it is checked
  on every call regardless of what the client renders.
- Every state-changing method (POST, PUT, DELETE) requires a valid
  per-session CSRF token; requests without one are rejected with 403.
- User text is escaped on render by JSX interpolation, so note content
  containing markup is displayed, not executed. The app never uses
  dangerouslySetInnerHTML.
- A new session id is issued on sign-in (session fixation defence).
- The session cookie is HttpOnly, so script cannot read it.
- Sign-in failures give one message for both unknown email and wrong
  password, so the response cannot be used to enumerate accounts.


--------------------------------------------------------------------
 Project Structure
--------------------------------------------------------------------
BACK END - src/main/java/com/
  Db/DBConnect.java           HikariCP connection pool
  Db/DatabaseInitializer.java Creates/upgrades the schema at startup
  DAO/UserDAO.java            Registration, credential checking
  DAO/PostDAO.java            Owner-scoped note queries, search, pin
  User/UserDetails.java       User model
  User/Post.java              Note model
  api/AuthApi.java            /api/auth/* endpoints
  api/NotesApi.java           /api/notes/* endpoints
  api/StatsApi.java           /api/stats
  util/Json.java              JSON request/response helpers
  util/Csrf.java              Per-session CSRF tokens
  util/WebUtils.java          Session user, parameter parsing, validation
  filter/AuthFilter.java      401s unauthenticated API calls
  filter/CsrfFilter.java      Rejects writes without a valid token
  filter/SpaFilter.java       Serves the React shell for client routes

FRONT END - frontend/
  index.html               Vite entry point
  vite.config.js           Build config; dev-server proxy to the API
  src/main.jsx             App bootstrap (Router + AuthProvider)
  src/App.jsx              Routes and the signed-in route guard
  src/api.js               fetch wrapper: cookies + CSRF header
  src/auth.jsx             Auth context; resolves the session on load
  src/styles.css           The whole design system
  src/components/          Icon, Navbar, Alert, PasswordInput, NoteCard
  src/pages/               Landing, Login, Register, Dashboard,
                           Notes, NoteEditor, NotFound

  Built output lands in frontend/dist and Maven packages it into the
  WAR root. node_modules/ and dist/ are gitignored.

src/main/webapp/
  WEB-INF/web.xml  Welcome file + session config (endpoints come from
                   @WebServlet / @WebFilter annotations)
  img/             Static images

src/main/resources/
  schema.sql               Reference schema for a fresh database
  db.properties.example    Template for local DB credentials
  db.properties            Your real credentials (gitignored)

scripts/run-enotes.ps1     Build + deploy + start/stop helper
.vscode/tasks.json         VS Code tasks that call run-enotes.ps1
pom.xml                    Maven build (packaging=war, finalName=enotes)


--------------------------------------------------------------------
 Compatibility note - read this first
--------------------------------------------------------------------
This project uses the javax.servlet API (Servlet 4.0), not
jakarta.servlet. That means it only runs on Tomcat 9.x. Tomcat 10+
renamed the package to jakarta.servlet and will fail to load this
app's servlets. If you have Tomcat 11 (or any 10+) installed
elsewhere on your machine, do not deploy this WAR to it - install or
use a project-local Tomcat 9.x instead.


--------------------------------------------------------------------
 Prerequisites
--------------------------------------------------------------------
- Java 17 (JDK)
- Maven (a project-local copy is used by scripts/run-enotes.ps1, so a
  system-wide install is optional if you use that script)
- Apache Tomcat 9.x (same note - project-local copy works fine)
- MySQL Server running locally with a database named "enotes"
- Node.js is NOT required. Maven downloads its own copy into the
  ignored .tools directory and runs the npm build itself, the same way
  Maven and Tomcat are already kept project-local.
- VS Code with "Extension Pack for Java" and "Community Server
  Connector" (recommended, see .vscode/extensions.json)


--------------------------------------------------------------------
 Database Setup
--------------------------------------------------------------------
Create an empty database named "enotes" and the app does the rest:

    CREATE DATABASE enotes
        CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

DatabaseInitializer runs on every startup and brings the schema up to
date. Each step is guarded by an existence check, so it is safe to run
repeatedly: a fresh database is created, an older one is upgraded in
place, and a current one is left alone. It will, as needed:

  - create the user and post tables
  - widen user.password to VARCHAR(255)
  - widen user.email and add a UNIQUE constraint on it
  - add user.created_at
  - widen post.title to VARCHAR(200)
  - convert post.content to TEXT (it was VARCHAR(45), which silently
    truncated almost every real note)
  - rename post.date to post.created_at, preserving the data
  - add post.pinned and post.updated_at
  - add the (uid, pinned, created_at) listing index

If the user table already contains duplicate emails, the unique
constraint is skipped and a warning is logged rather than deleting
rows; remove the duplicates and restart to finish the upgrade.

src/main/resources/schema.sql is the authoritative reference and can
also set up a fresh database by hand:

    mysql -u root -p < src/main/resources/schema.sql


--------------------------------------------------------------------
 Configuration
--------------------------------------------------------------------
Copy src/main/resources/db.properties.example to
src/main/resources/db.properties and fill in your MySQL credentials:

    db.url=jdbc:mysql://localhost:3306/enotes?useSSL=false&serverTimezone=UTC
    db.username=root
    db.password=your_password_here

db.properties is gitignored - it is never committed. Settings are
read in this order, so you can avoid editing the file entirely in CI
or a shared environment:
    1. JVM system properties: -Denotes.db.url / .username / .password
    2. Environment variables:  ENOTES_DB_URL / _USERNAME / _PASSWORD
    3. src/main/resources/db.properties


--------------------------------------------------------------------
 Running the Project
--------------------------------------------------------------------
Easiest: VS Code tasks (uses a project-local Java-17/Maven/Tomcat-9
toolchain under .tools/, no machine-wide install required)

    Ctrl+Shift+P -> Run Task -> E-Notes: Build   (package the WAR only)
    Ctrl+Shift+P -> Run Task -> E-Notes: Start   (build, deploy, launch)
    Ctrl+Shift+P -> Run Task -> E-Notes: Stop    (shut Tomcat down)

    Then open: http://localhost:8080/enotes/

Equivalent from a terminal:

    powershell -ExecutionPolicy Bypass -File .\scripts\run-enotes.ps1 -Action start
    powershell -ExecutionPolicy Bypass -File .\scripts\run-enotes.ps1 -Action stop

These build the React app as part of the same step - there is no
separate npm command to remember.

Manual alternative, with your own Java 17 + Maven + Tomcat 9:

    1. mvn clean package     (compiles Java and builds React)
    2. Copy target\enotes.war into <tomcat>\webapps\
    3. Start Tomcat (<tomcat>\bin\startup.bat)
    4. Open http://localhost:8080/enotes/


Front-end development with hot reload (optional)
------------------------------------------------
Editing React normally means rebuilding the WAR. For a faster loop,
run Tomcat as usual and start Vite's dev server alongside it:

    cd frontend
    npm install
    npm run dev

Then use http://localhost:5173/enotes/ instead. Vite proxies /api to
Tomcat on 8080 (see vite.config.js), so the same session and API are
used while the UI reloads on save. This is a development convenience
only - the deployed WAR is always same-origin and needs no proxy.


--------------------------------------------------------------------
 Troubleshooting
--------------------------------------------------------------------
- Errors on every page: MySQL isn't running, or the "enotes" database
  / credentials in db.properties are wrong. Check the Tomcat log for
  a "[E-Notes schema]" line reporting the problem.
- "Invalid or missing security token": the page was open long enough
  for the session to expire. Reload it and submit again.
- 404 on http://localhost:8080/enotes/: the WAR didn't deploy - check
  the Tomcat logs directory for a deployment stack trace.
- ClassNotFoundException for javax.servlet.*: you deployed to a
  Tomcat 10+ instance - use Tomcat 9.x (see Compatibility above).
- Port 8080 already in use: another process is bound to it; stop it
  or change the port in <tomcat>\conf\server.xml.
- Blank page with 404s for /enotes/assets/*: the React build did not
  run or its output was not packaged. Run a clean build
  (`mvn clean package`) and confirm frontend/dist exists afterwards.
- The first build is slow: Maven is downloading Node and the npm
  packages into .tools. Later builds reuse them.
