Technologies Used:
Front-End: html, css, bootstrap 4, fontawsome
Back-End: jsp, servlet, jdbc, mysql
Modules: register, login, logout, add notes, show notes, delete notes, edit notes


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
