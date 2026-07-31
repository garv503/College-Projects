Technologies Used:
Front-End: html, css, bootstrap 4, fontawsome
Back-End: jsp, servlet, jdbc, mysql
Modules: register, login, logout, add notes, show notes, delete notes, edit notes

Development setup:
1. Install Java 17, Maven, and Apache Tomcat 9.x. Tomcat 10+ is not compatible because this project uses javax.servlet.
2. Create the enotes database using the schema below.
3. Copy src/main/resources/db.properties.example to src/main/resources/db.properties and set your MySQL credentials.
4. Run mvn clean package. Deploy target/enotes.war to Tomcat, then open http://localhost:8080/enotes/.
5. In VS Code, install the recommended Java and Community Server Connector extensions. Open this folder and let VS Code import the Maven project.
6. After the project-local tool setup is complete, use Terminal > Run Task > E-Notes: Start in VS Code. Use E-Notes: Stop when finished.


Database Name: enotes

User Table Structure:
create table user
(
id int primary key auto_increment,
full_name varchar(100),
email varchar(100),
password varchar(100)
);


Post Table Structure:
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
