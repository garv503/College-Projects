-- ---------------------------------------------------------------------------
-- E-Notes reference schema.
--
-- The application also self-migrates at startup (see DatabaseInitializer),
-- so you normally do not need to run this by hand. It is kept as the
-- authoritative description of the expected shape of the database, and for
-- setting up a fresh database from scratch:
--
--     mysql -u root -p < src/main/resources/schema.sql
-- ---------------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS enotes
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE enotes;

CREATE TABLE IF NOT EXISTS user (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    email      VARCHAR(190) NOT NULL,
    -- Stores the password as plain text, by explicit project choice. Anyone
    -- who can read this table can read every account's real password.
    password   VARCHAR(255) NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Stops two accounts sharing one email, which previously let a duplicate
    -- registration silently shadow an existing login.
    CONSTRAINT uq_user_email UNIQUE (email)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS post (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    title      VARCHAR(200) NOT NULL,
    -- Was VARCHAR(45), which silently truncated almost every real note.
    content    TEXT         NOT NULL,
    pinned     BOOLEAN      NOT NULL DEFAULT FALSE,
    uid        INT          NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_post_uid (uid),
    -- Supports the default "pinned first, newest first" listing.
    INDEX idx_post_uid_pinned_created (uid, pinned DESC, created_at DESC),
    CONSTRAINT fk_post_user FOREIGN KEY (uid) REFERENCES user (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;
