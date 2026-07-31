====================================================================
 E-Notes
====================================================================

E-Notes is a simple note-taking web application. Users register,
log in, and can add, view, edit, and delete their own notes. Each
note belongs to exactly one user (enforced via a foreign key with
cascading delete).


--------------------------------------------------------------------
 Technologies Used
--------------------------------------------------------------------
Front-End: HTML, CSS, Bootstrap 4, Font Awesome
Back-End:  JSP, Java Servlets (javax.servlet 4.0.1), JDBC, MySQL
Build:     Maven
Server:    Apache Tomcat 9.x (NOT 10+ - see Compatibility below)


--------------------------------------------------------------------
 Features / Modules
--------------------------------------------------------------------
- Register    - create an account (full name, email, password)
- Login       - authenticate with email + password
- Logout      - end the session
- Add Notes   - create a note (title + content) tied to the logged-in user
- Show Notes  - list all notes belonging to the logged-in user
- Edit Notes  - update an existing note's title/content
- Delete Notes- remove a note


--------------------------------------------------------------------
 Project Structure
--------------------------------------------------------------------
src/main/java/com/
  Db/DBConnect.java        Shared JDBC connection (see Configuration)
  DAO/UserDAO.java         User insert / login queries
  DAO/PostDAO.java         Note insert / read / update / delete queries
  User/UserDetails.java    User model
  User/Post.java           Note model
  Servlet/UserServlet.java     POST /UserServlet     -> register
  Servlet/loginServlet.java    POST /loginServlet    -> login
  Servlet/logoutServlet.java   GET  /logoutServlet   -> logout
  Servlet/AddNotesServlet.java POST /AddNotesServlet -> create note
  Servlet/NoteEditServlet.java POST /NoteEditServlet -> update note
  Servlet/deleteServlet.java   GET  /deleteServlet   -> delete note

src/main/webapp/
  index.jsp, login.jsp, register.jsp, home.jsp,
  addNotes.jsp, edit.jsp, showNotes.jsp, errorPage.jsp
  all_component/  shared navbar, footer, CSS includes
  css/style.css, img/                page assets
  WEB-INF/web.xml                    welcome-file list only (routes are
                                      defined via @WebServlet annotations)

src/main/resources/
  db.properties.example    Template for local DB credentials
  db.properties            Your real credentials (gitignored, you create this)

scripts/run-enotes.ps1     Build + deploy + start/stop helper (see below)
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
- MySQL Server, running locally with a database named "enotes"
  (schema below)
- VS Code with the "Extension Pack for Java" and "Community Server
  Connector" extensions (recommended, see .vscode/extensions.json)


--------------------------------------------------------------------
 Database Setup
--------------------------------------------------------------------
Database Name: enotes

User Table:
create table user
(
    id int primary key auto_increment,
    full_name varchar(100),
    email varchar(100),
    password varchar(100)
);

Post Table:
CREATE TABLE post (
    id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(45) NOT NULL,
    content VARCHAR(45) NOT NULL,
    date TIMESTAMP NULL DEFAULT NOW(),
    uid INT NOT NULL,
    PRIMARY KEY (id),
    INDEX uid_idx (uid ASC),
    CONSTRAINT uid FOREIGN KEY (uid) REFERENCES user (id) ON DELETE CASCADE ON UPDATE CASCADE
);


--------------------------------------------------------------------
 Configuration
--------------------------------------------------------------------
Copy src/main/resources/db.properties.example to
src/main/resources/db.properties and fill in your MySQL credentials:

    db.url=jdbc:mysql://localhost:3306/enotes?useSSL=false&serverTimezone=UTC
    db.username=root
    db.password=your_password_here

db.properties is gitignored - it is never committed. DBConnect.java
also honours these overrides, checked in this order, so you can avoid
editing the file at all in CI or a shared environment:
    1. JVM system properties: -Denotes.db.url / -Denotes.db.username / -Denotes.db.password
    2. Environment variables:  ENOTES_DB_URL / ENOTES_DB_USERNAME / ENOTES_DB_PASSWORD
    3. src/main/resources/db.properties


--------------------------------------------------------------------
 Running the Project
--------------------------------------------------------------------
Easiest: VS Code tasks (uses a project-local Java-17/Maven/Tomcat-9
toolchain under .tools/, no machine-wide install required)

    Ctrl+Shift+P -> Run Task -> E-Notes: Build   (compiles + packages the WAR only)
    Ctrl+Shift+P -> Run Task -> E-Notes: Start   (build, deploy, launch Tomcat)
    Ctrl+Shift+P -> Run Task -> E-Notes: Stop    (shuts Tomcat down)

    Then open: http://localhost:8080/enotes/

Equivalent from a terminal:

    powershell -ExecutionPolicy Bypass -File .\scripts\run-enotes.ps1 -Action start
    powershell -ExecutionPolicy Bypass -File .\scripts\run-enotes.ps1 -Action stop

Manual alternative (no helper script), if you have your own Java 17 +
Maven + Tomcat 9 install:

    1. mvn clean package
    2. Copy target\enotes.war into <tomcat>\webapps\
    3. Start Tomcat (<tomcat>\bin\startup.bat)
    4. Open http://localhost:8080/enotes/


--------------------------------------------------------------------
 Troubleshooting
--------------------------------------------------------------------
- Blank/connection error on any page: MySQL isn't running, or the
  "enotes" database / credentials in db.properties are wrong.
- 404 on http://localhost:8080/enotes/: the WAR didn't deploy - check
  the Tomcat logs directory for a stack trace during deployment.
- ClassNotFoundException / NoClassDefFoundError for javax.servlet.*:
  you deployed to a Tomcat 10+ instance - use Tomcat 9.x instead (see
  Compatibility note above).
- Port 8080 already in use: another process (or another Tomcat) is
  bound to it; stop that process or change the port in
  <tomcat>\conf\server.xml.
