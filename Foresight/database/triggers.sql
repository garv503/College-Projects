-- =====================================================================
--  Foresight - Triggers
-- =====================================================================
--  Run after schema.sql:
--      mysql -u root -p foresight < database/triggers.sql
--
--  Two jobs are done here, and both are done in the database on purpose:
--
--  1. VALIDATION that must never be bypassed.
--     A CHECK constraint cannot compare a value against another column
--     in a way that produces a readable message, and it cannot be
--     skipped - but it also cannot say *which* numbers were wrong.
--     SIGNAL lets the database reject the row with a message the API can
--     surface directly to the user.
--
--  2. AUDITING that the application cannot forget.
--     If the audit write lived in Python, any new code path that
--     forgot to call it would create an untracked change. In a trigger
--     it is structurally impossible to miss - a raw `UPDATE` typed into
--     the MySQL console is logged too.
--
--  Note on `@app_user`: the API sets this session variable right after
--  it checks out a connection (see backend/db.py). Triggers read it to
--  attribute the change to a username. When someone edits data directly
--  in a SQL client the variable is unset, so the row is logged with
--  actor NULL - which is exactly the signal you want.
-- =====================================================================

USE foresight;

-- Pin the client character set; see the note in views.sql. Without it
-- the Windows mysql client connects as cp850 and utf8mb4 collations
-- are rejected mid-script.
SET NAMES utf8mb4;

DROP TRIGGER IF EXISTS trg_assessment_before_insert;
DROP TRIGGER IF EXISTS trg_assessment_before_update;
DROP TRIGGER IF EXISTS trg_assessment_after_insert;
DROP TRIGGER IF EXISTS trg_assessment_after_update;
DROP TRIGGER IF EXISTS trg_assessment_after_delete;
DROP TRIGGER IF EXISTS trg_student_after_update;
DROP TRIGGER IF EXISTS trg_student_after_delete;
DROP TRIGGER IF EXISTS trg_attendance_before_insert;

DELIMITER $$

-- ---------------------------------------------------------------------
-- Guard: a student cannot score more than the paper was worth
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_assessment_before_insert
BEFORE INSERT ON assessments
FOR EACH ROW
BEGIN
    IF NEW.marks_obtained > NEW.max_marks THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'marks_obtained cannot exceed max_marks';
    END IF;

    -- Marks dated in the future are always a typo in the year field.
    IF NEW.assessed_on > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'assessed_on cannot be a future date';
    END IF;
END$$


CREATE TRIGGER trg_assessment_before_update
BEFORE UPDATE ON assessments
FOR EACH ROW
BEGIN
    IF NEW.marks_obtained > NEW.max_marks THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'marks_obtained cannot exceed max_marks';
    END IF;
END$$


-- ---------------------------------------------------------------------
-- Guard: attendance cannot be recorded for a class that has not happened
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_attendance_before_insert
BEFORE INSERT ON attendance_records
FOR EACH ROW
BEGIN
    IF NEW.class_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'class_date cannot be in the future';
    END IF;
END$$


-- ---------------------------------------------------------------------
-- Audit: every mark that is created, changed or removed
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_assessment_after_insert
AFTER INSERT ON assessments
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (actor, action, entity, entity_id, details)
    VALUES (
        @app_user,
        'assessment.create',
        'assessment',
        NEW.assessment_id,
        JSON_OBJECT(
            'enrollment_id', NEW.enrollment_id,
            'type',          NEW.type,
            'marks',         NEW.marks_obtained,
            'max_marks',     NEW.max_marks
        )
    );
END$$


-- Only writes a row when a mark actually moved. Re-saving a form without
-- touching the number should not create audit noise.
CREATE TRIGGER trg_assessment_after_update
AFTER UPDATE ON assessments
FOR EACH ROW
BEGIN
    IF NEW.marks_obtained <> OLD.marks_obtained
       OR NEW.max_marks   <> OLD.max_marks THEN
        INSERT INTO audit_log (actor, action, entity, entity_id, details)
        VALUES (
            @app_user,
            'assessment.update',
            'assessment',
            NEW.assessment_id,
            JSON_OBJECT(
                'enrollment_id', NEW.enrollment_id,
                'type',          NEW.type,
                'old_marks',     OLD.marks_obtained,
                'new_marks',     NEW.marks_obtained,
                'old_max',       OLD.max_marks,
                'new_max',       NEW.max_marks
            )
        );
    END IF;
END$$


CREATE TRIGGER trg_assessment_after_delete
AFTER DELETE ON assessments
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (actor, action, entity, entity_id, details)
    VALUES (
        @app_user,
        'assessment.delete',
        'assessment',
        OLD.assessment_id,
        JSON_OBJECT(
            'enrollment_id', OLD.enrollment_id,
            'type',          OLD.type,
            'marks',         OLD.marks_obtained
        )
    );
END$$


-- ---------------------------------------------------------------------
-- Audit: student record changes
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_student_after_update
AFTER UPDATE ON students
FOR EACH ROW
BEGIN
    IF NEW.name      <> OLD.name
       OR NEW.branch_id <> OLD.branch_id
       OR NEW.semester  <> OLD.semester
       OR NEW.email     <> OLD.email
       OR NEW.is_active <> OLD.is_active THEN
        INSERT INTO audit_log (actor, action, entity, entity_id, details)
        VALUES (
            @app_user,
            'student.update',
            'student',
            NEW.student_id,
            JSON_OBJECT(
                'old', JSON_OBJECT('name', OLD.name, 'branch_id', OLD.branch_id,
                                   'semester', OLD.semester, 'email', OLD.email,
                                   'is_active', OLD.is_active),
                'new', JSON_OBJECT('name', NEW.name, 'branch_id', NEW.branch_id,
                                   'semester', NEW.semester, 'email', NEW.email,
                                   'is_active', NEW.is_active)
            )
        );
    END IF;
END$$


CREATE TRIGGER trg_student_after_delete
AFTER DELETE ON students
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (actor, action, entity, entity_id, details)
    VALUES (
        @app_user,
        'student.delete',
        'student',
        OLD.student_id,
        JSON_OBJECT('roll_no', OLD.roll_no, 'name', OLD.name)
    );
END$$

DELIMITER ;
