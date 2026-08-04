-- =====================================================================
--  Foresight - Database Schema
-- =====================================================================
--  Engine : MySQL 8.0+
--  Run    : mysql -u root -p < database/schema.sql
--
--  Design notes (worth knowing if you are explaining this project):
--
--  1. An "enrollment" is the link between a student and a subject for a
--     given academic year. Marks and attendance hang off the enrollment,
--     not off (student, subject) directly. This is what lets the same
--     student take the same subject again (a backlog / re-sit) without
--     colliding on a primary key.
--
--  2. Marks are stored as individual `assessments` (quiz, midterm, final)
--     rather than one flat number. That is what makes trend charts and
--     "improving vs declining" analysis possible.
--
--  3. Attendance is stored as dated `attendance_records` (one row per
--     class) rather than a single percentage. The percentage is then a
--     derived value, computed by a view - never stored and never able to
--     drift out of sync with reality.
--
--  4. Every destructive change is written to `audit_log` by a trigger,
--     so the application cannot "forget" to log it.
-- =====================================================================

DROP DATABASE IF EXISTS foresight;
CREATE DATABASE foresight
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE foresight;

-- Pin the client character set; see the note in views.sql. Without it
-- the Windows mysql client connects as cp850 and utf8mb4 collations
-- are rejected mid-script.
SET NAMES utf8mb4;


-- ---------------------------------------------------------------------
-- branches : lookup table for departments
-- ---------------------------------------------------------------------
-- Previously "branch" was a free-text VARCHAR on both students and
-- subjects, so 'CSE', 'cse' and 'C.S.E' were three different branches and
-- a typo silently produced a student nobody could find. A lookup table
-- plus a foreign key makes that impossible.
CREATE TABLE branches (
    branch_id   INT AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(10)  NOT NULL UNIQUE,      -- 'CSE'
    name        VARCHAR(100) NOT NULL,             -- 'Computer Science & Engineering'
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ---------------------------------------------------------------------
-- students
-- ---------------------------------------------------------------------
CREATE TABLE students (
    student_id     INT AUTO_INCREMENT PRIMARY KEY,
    roll_no        VARCHAR(20)  NOT NULL UNIQUE,   -- real-world identifier
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    branch_id      INT          NOT NULL,
    semester       TINYINT      NOT NULL,
    admission_year YEAR         NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_students_branch
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),

    -- A semester outside 1..8 is always a data-entry bug.
    CONSTRAINT chk_students_semester CHECK (semester BETWEEN 1 AND 8),

    -- Cheap sanity check; real validation happens in the API layer.
    CONSTRAINT chk_students_email CHECK (email LIKE '%_@_%._%')
) ENGINE=InnoDB;

-- The admin student list is always filtered by branch + semester, and
-- usually only shows active students, so index that exact combination.
CREATE INDEX idx_students_cohort ON students (branch_id, semester, is_active);
CREATE INDEX idx_students_name   ON students (name);


-- ---------------------------------------------------------------------
-- subjects
-- ---------------------------------------------------------------------
CREATE TABLE subjects (
    subject_id   INT AUTO_INCREMENT PRIMARY KEY,
    code         VARCHAR(20)  NOT NULL UNIQUE,     -- 'CS301'
    name         VARCHAR(100) NOT NULL,
    branch_id    INT          NOT NULL,
    semester     TINYINT      NOT NULL,
    credits      TINYINT      NOT NULL DEFAULT 4,
    pass_mark    TINYINT      NOT NULL DEFAULT 40, -- percent needed to pass
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_subjects_branch
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    CONSTRAINT chk_subjects_semester CHECK (semester BETWEEN 1 AND 8),
    CONSTRAINT chk_subjects_credits  CHECK (credits BETWEEN 1 AND 10),
    CONSTRAINT chk_subjects_pass     CHECK (pass_mark BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE INDEX idx_subjects_cohort ON subjects (branch_id, semester);


-- ---------------------------------------------------------------------
-- users : login accounts
-- ---------------------------------------------------------------------
-- `password` is stored as plain text, by design: this runs as a personal
-- admin tool and the owner needs to read a password back directly rather
-- than only ever issuing a new one. See the note in backend/security.py
-- for the trade-off that comes with that choice.
--
-- `email` is what the self-service "forgot password" flow checks before
-- letting someone set a new password (backend/routes/auth.py). Students
-- already have an email on the `students` row; this lets admin and
-- faculty accounts - which have no student row - use the same flow.
CREATE TABLE users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL UNIQUE,
    password       VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NULL UNIQUE,
    role           ENUM('admin','faculty','student') NOT NULL,
    student_id     INT          NULL,              -- NULL for admin/faculty
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login_at  TIMESTAMP    NULL,
    must_change_pw BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_users_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE,

    -- Exactly one login per student. MySQL lets a UNIQUE column hold many
    -- NULLs, which is precisely what is wanted here: every admin and
    -- faculty row has student_id NULL and they do not collide.
    --
    -- Beyond being correct domain modelling, this is what makes the
    -- `LEFT JOIN users` in the admin student list safe. Without it, a
    -- student with two login rows would appear twice in the list and be
    -- counted twice in the pagination total.
    CONSTRAINT uq_users_student UNIQUE (student_id),

    -- A student account must point at a student row; staff accounts must
    -- not. Enforcing this in SQL means no application bug can create an
    -- orphaned student login.
    CONSTRAINT chk_users_student_link CHECK (
        (role = 'student' AND student_id IS NOT NULL) OR
        (role IN ('admin','faculty') AND student_id IS NULL)
    )
) ENGINE=InnoDB;

CREATE INDEX idx_users_role ON users (role, is_active);


-- ---------------------------------------------------------------------
-- enrollments : student <-> subject, per academic year
-- ---------------------------------------------------------------------
CREATE TABLE enrollments (
    enrollment_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT      NOT NULL,
    subject_id     INT      NOT NULL,
    academic_year  YEAR     NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_enroll_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_enroll_subject
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        ON DELETE CASCADE,

    -- One enrollment per student/subject/year. Re-sitting the subject in
    -- a later year is allowed because the year is part of the key.
    CONSTRAINT uq_enrollment UNIQUE (student_id, subject_id, academic_year)
) ENGINE=InnoDB;

CREATE INDEX idx_enroll_subject ON enrollments (subject_id);


-- ---------------------------------------------------------------------
-- assessments : individual graded items
-- ---------------------------------------------------------------------
-- Storing `max_marks` per row rather than assuming everything is out of
-- 100 means a 20-mark quiz and a 100-mark final can live in the same
-- table and still be averaged correctly (as a percentage).
CREATE TABLE assessments (
    assessment_id  INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_id  INT     NOT NULL,
    type           ENUM('quiz','assignment','midterm','final') NOT NULL,
    marks_obtained DECIMAL(5,2) NOT NULL,
    max_marks      DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    assessed_on    DATE    NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_assess_enroll
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_assess_max      CHECK (max_marks > 0),
    CONSTRAINT chk_assess_obtained CHECK (marks_obtained >= 0),
    -- Note: "obtained <= max" is enforced by a trigger, not here, so the
    -- error message can name the actual numbers. See triggers.sql.
    CONSTRAINT chk_assess_type_max CHECK (max_marks <= 200)
) ENGINE=InnoDB;

-- Trend queries read "all assessments for this enrollment, oldest first".
CREATE INDEX idx_assess_trend ON assessments (enrollment_id, assessed_on);


-- ---------------------------------------------------------------------
-- attendance_records : one row per class held
-- ---------------------------------------------------------------------
CREATE TABLE attendance_records (
    record_id      INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_id  INT   NOT NULL,
    class_date     DATE  NOT NULL,
    status         ENUM('present','absent','late','excused') NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_attend_enroll
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
        ON DELETE CASCADE,

    -- A student cannot be marked twice for the same class.
    CONSTRAINT uq_attendance UNIQUE (enrollment_id, class_date)
) ENGINE=InnoDB;

CREATE INDEX idx_attend_date ON attendance_records (enrollment_id, class_date);


-- ---------------------------------------------------------------------
-- audit_log : who changed what
-- ---------------------------------------------------------------------
-- Written by triggers (for data changes) and by the API (for logins and
-- bulk imports). `details` is JSON so the shape can vary by action
-- without needing a schema change every time.
CREATE TABLE audit_log (
    log_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    actor        VARCHAR(50)  NULL,        -- username, NULL for system/trigger
    action       VARCHAR(50)  NOT NULL,    -- 'login.success', 'marks.update', ...
    entity       VARCHAR(50)  NULL,        -- 'assessment', 'student', ...
    entity_id    INT          NULL,
    details      JSON         NULL,
    ip_address   VARCHAR(45)  NULL,        -- 45 chars fits IPv6
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_audit_created ON audit_log (created_at DESC);
CREATE INDEX idx_audit_action  ON audit_log (action, created_at DESC);


-- ---------------------------------------------------------------------
-- login_attempts : brute-force tracking
-- ---------------------------------------------------------------------
-- The rate limiter also keeps an in-process counter for speed, but that
-- dies when the server restarts. This table is the durable record.
CREATE TABLE login_attempts (
    attempt_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50) NOT NULL,
    ip_address   VARCHAR(45) NULL,
    succeeded    BOOLEAN     NOT NULL,
    attempted_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_attempts_lookup ON login_attempts (username, attempted_at DESC);
