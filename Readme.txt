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
Front-End: JSP + JSTL, custom CSS design system, inline SVG icons
           (no Bootstrap, no jQuery, no CDN - fully self-contained)
Back-End:  Java Servlets (javax.servlet 4.0), JDBC, MySQL
Pooling:   HikariCP
Build:     Maven
Server:    Apache Tomcat 9.x (NOT 10+ - see Compatibility below)


--------------------------------------------------------------------
 Features
--------------------------------------------------------------------
- Register / sign in / sign out
- Dashboard with note counts and recent notes
- Write, edit, and delete notes
- Pin notes so they sort to the top
- Full-text style search across note titles and bodies
- Light and dark theme, remembered per browser
- Responsive layout down to mobile widths


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
- The author of a new note is taken from the session, not from a
  form field, so a note cannot be filed under another account.
- Sign-in is enforced by a servlet filter rather than a per-page
  check, so protection cannot be omitted on a new page.
- All state-changing actions are POST and carry a per-session CSRF
  token; requests without a valid token are rejected with 403.
- All user-supplied text is escaped on output via <c:out>, so note
  content containing markup is displayed, not executed.
- A new session id is issued on sign-in (session fixation defence).
- Sign-in failures give one message for both unknown email and wrong
  password, so the response cannot be used to enumerate accounts.


--------------------------------------------------------------------
 Project Structure
--------------------------------------------------------------------
src/main/java/com/
  Db/DBConnect.java           HikariCP connection pool
  Db/DatabaseInitializer.java Creates/upgrades the schema at startup
  DAO/UserDAO.java            Registration, credential checking
  DAO/PostDAO.java            Owner-scoped note queries, search, pin
  User/UserDetails.java       User model
  User/Post.java              Note model
  util/Csrf.java              Per-session CSRF tokens
  util/WebUtils.java          Session user, flash messages, validation
  filter/AuthFilter.java      Requires sign-in outside public pages
  filter/CsrfFilter.java      Rejects POSTs without a valid token
  Servlet/UserServlet.java        POST /UserServlet     -> register
  Servlet/loginServlet.java       POST /loginServlet    -> sign in
  Servlet/logoutServlet.java      POST /logoutServlet   -> sign out
  Servlet/AddNotesServlet.java    POST /AddNotesServlet -> create
  Servlet/NoteEditServlet.java    POST /NoteEditServlet -> update
  Servlet/deleteServlet.java      POST /deleteServlet   -> delete
  Servlet/PinServlet.java         POST /PinServlet      -> pin/unpin

src/main/webapp/
  index.jsp        Landing page
  login.jsp        Sign in
  register.jsp     Create account
  home.jsp         Dashboard (counts + recent notes)
  addNotes.jsp     New note form
  edit.jsp         Edit note form
  showNotes.jsp    Note list with search
  errorPage.jsp    Friendly error page
  all_component/   allcss, icons (SVG sprite), navbar, flash,
                   passwordToggle
  css/style.css    The whole design system
  WEB-INF/web.xml  Welcome files (routes come from @WebServlet)

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

Manual alternative, with your own Java 17 + Maven + Tomcat 9:

    1. mvn clean package
    2. Copy target\enotes.war into <tomcat>\webapps\
    3. Start Tomcat (<tomcat>\bin\startup.bat)
    4. Open http://localhost:8080/enotes/


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
