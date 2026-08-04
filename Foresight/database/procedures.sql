-- =====================================================================
--  Foresight - Stored Procedures & Functions
-- =====================================================================
--  Run after schema.sql + views.sql:
--      mysql -u root -p foresight < database/procedures.sql
--
--  When is a stored procedure the right tool here?
--
--  Enrolling a student touches five tables. Done from Python that is
--  five round-trips to the database, and a crash halfway through leaves
--  a student with a login but no subjects. `sp_enroll_student` does the
--  whole thing in one call inside one transaction: it either all lands
--  or none of it does.
--
--  The reporting procedures exist for a different reason - they are the
--  queries that are painful to express as a view because they need a
--  parameter (a specific student, a specific cohort).
-- =====================================================================

USE foresight;

-- Pin the client character set; see the note in views.sql. Without it
-- the Windows mysql client connects as cp850 and utf8mb4 collations
-- are rejected mid-script.
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS sp_enroll_student;
DROP PROCEDURE IF EXISTS sp_record_assessment;
DROP PROCEDURE IF EXISTS sp_student_report_card;
DROP PROCEDURE IF EXISTS sp_cohort_summary;
DROP PROCEDURE IF EXISTS sp_promote_semester;
DROP FUNCTION  IF EXISTS fn_letter_grade;
DROP FUNCTION  IF EXISTS fn_grade_point;

DELIMITER $$

-- ---------------------------------------------------------------------
-- fn_letter_grade : percentage -> letter
-- ---------------------------------------------------------------------
-- A function rather than a CASE repeated in six queries. Change the
-- grading scale here and every report follows automatically.
CREATE FUNCTION fn_letter_grade(pct DECIMAL(6,2))
RETURNS VARCHAR(2)
DETERMINISTIC
BEGIN
    IF pct IS NULL   THEN RETURN '-';  END IF;
    IF pct >= 90     THEN RETURN 'A+'; END IF;
    IF pct >= 80     THEN RETURN 'A';  END IF;
    IF pct >= 70     THEN RETURN 'B';  END IF;
    IF pct >= 60     THEN RETURN 'C';  END IF;
    IF pct >= 50     THEN RETURN 'D';  END IF;
    IF pct >= 40     THEN RETURN 'E';  END IF;
    RETURN 'F';
END$$


-- ---------------------------------------------------------------------
-- fn_grade_point : percentage -> 10-point scale
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_grade_point(pct DECIMAL(6,2))
RETURNS DECIMAL(3,1)
DETERMINISTIC
BEGIN
    IF pct IS NULL THEN RETURN 0.0; END IF;
    IF pct < 40    THEN RETURN 0.0; END IF;
    -- 40% -> 4.0, 90%+ -> 10.0, linear in between.
    RETURN LEAST(10.0, ROUND(pct / 10, 1));
END$$


-- ---------------------------------------------------------------------
-- sp_enroll_student : register a student for every subject in a cohort
-- ---------------------------------------------------------------------
-- Creates the enrollment rows for whichever subjects belong to the
-- student's branch and semester. Safe to re-run: `INSERT IGNORE` relies
-- on the uq_enrollment key, so a second call adds only new subjects
-- instead of erroring or duplicating.
CREATE PROCEDURE sp_enroll_student(
    IN  p_student_id    INT,
    IN  p_academic_year YEAR,
    OUT p_enrolled      INT
)
BEGIN
    DECLARE v_branch   INT;
    DECLARE v_semester TINYINT;

    -- Roll back and re-raise if anything below fails, so a partial
    -- enrollment can never be committed.
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT branch_id, semester INTO v_branch, v_semester
    FROM students WHERE student_id = p_student_id;

    IF v_branch IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'student not found';
    END IF;

    INSERT IGNORE INTO enrollments (student_id, subject_id, academic_year)
    SELECT p_student_id, s.subject_id, p_academic_year
    FROM subjects s
    WHERE s.branch_id = v_branch
      AND s.semester  = v_semester;

    SET p_enrolled = ROW_COUNT();

    INSERT INTO audit_log (actor, action, entity, entity_id, details)
    VALUES (@app_user, 'student.enroll', 'student', p_student_id,
            JSON_OBJECT('academic_year', p_academic_year,
                        'subjects_added', p_enrolled));

    COMMIT;
END$$


-- ---------------------------------------------------------------------
-- sp_record_assessment : upsert a mark by student + subject
-- ---------------------------------------------------------------------
-- The API works in terms of "student X, subject Y" but the assessments
-- table is keyed on enrollment_id. This resolves that lookup in one
-- place so no route has to know the mapping.
CREATE PROCEDURE sp_record_assessment(
    IN p_student_id INT,
    IN p_subject_id INT,
    IN p_type       VARCHAR(20),
    IN p_obtained   DECIMAL(5,2),
    IN p_max        DECIMAL(5,2),
    IN p_date       DATE
)
BEGIN
    DECLARE v_enrollment INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT enrollment_id INTO v_enrollment
    FROM enrollments
    WHERE student_id = p_student_id
      AND subject_id = p_subject_id
    ORDER BY academic_year DESC
    LIMIT 1;

    IF v_enrollment IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'student is not enrolled in that subject';
    END IF;

    -- One assessment of each type per enrollment: re-submitting the
    -- midterm mark corrects it rather than stacking a second row.
    IF EXISTS (SELECT 1 FROM assessments
               WHERE enrollment_id = v_enrollment AND type = p_type) THEN
        UPDATE assessments
        SET marks_obtained = p_obtained,
            max_marks      = p_max,
            assessed_on    = p_date
        WHERE enrollment_id = v_enrollment AND type = p_type;
    ELSE
        INSERT INTO assessments
            (enrollment_id, type, marks_obtained, max_marks, assessed_on)
        VALUES
            (v_enrollment, p_type, p_obtained, p_max, p_date);
    END IF;

    COMMIT;
END$$


-- ---------------------------------------------------------------------
-- sp_student_report_card : everything needed to render one report card
-- ---------------------------------------------------------------------
-- Returns two result sets: the per-subject rows, then a summary row.
-- (backend/services/reports.py reads both.)
CREATE PROCEDURE sp_student_report_card(IN p_student_id INT)
BEGIN
    SELECT
        v.subject_code,
        v.subject_name,
        v.credits,
        v.assessment_count,
        v.mark_percent,
        v.attendance_percent,
        fn_letter_grade(v.mark_percent) AS grade,
        fn_grade_point(v.mark_percent)  AS grade_point,
        CASE WHEN v.mark_percent IS NULL THEN 'pending'
             WHEN v.mark_percent >= v.pass_mark THEN 'pass'
             ELSE 'fail' END            AS result
    FROM v_enrollment_summary v
    WHERE v.student_id = p_student_id
    ORDER BY v.subject_code;

    SELECT
        r.student_name,
        r.roll_no,
        r.branch_code,
        r.semester,
        r.subject_count,
        r.avg_mark_percent,
        r.avg_attendance_percent,
        r.backlog_count,
        r.class_rank,
        r.cohort_size,
        r.percentile,
        fn_letter_grade(r.avg_mark_percent) AS overall_grade,
        -- Credit-weighted GPA across all subjects.
        (SELECT ROUND(SUM(fn_grade_point(v2.mark_percent) * v2.credits)
                      / NULLIF(SUM(v2.credits), 0), 2)
         FROM v_enrollment_summary v2
         WHERE v2.student_id = p_student_id)  AS gpa
    FROM v_student_rank r
    WHERE r.student_id = p_student_id;
END$$


-- ---------------------------------------------------------------------
-- sp_cohort_summary : headline numbers for the admin dashboard
-- ---------------------------------------------------------------------
-- Pass NULL for either parameter to mean "all". That keeps the admin
-- filters as one call instead of four near-identical queries.
CREATE PROCEDURE sp_cohort_summary(
    IN p_branch_id INT,
    IN p_semester  TINYINT
)
BEGIN
    -- The CASTs matter: SUM() of a boolean is DECIMAL in MySQL, so
    -- without them these counts reach the front end as 14.0 instead of
    -- 14 and every dashboard tile has to strip the ".0" itself.
    SELECT
        COUNT(*)                                        AS student_count,
        ROUND(AVG(avg_mark_percent), 2)                 AS avg_mark_percent,
        ROUND(AVG(avg_attendance_percent), 2)           AS avg_attendance_percent,
        CAST(SUM(backlog_count > 0)   AS SIGNED)        AS students_with_backlogs,
        CAST(SUM(risk_band = 'high')  AS SIGNED)        AS high_risk_count,
        CAST(SUM(risk_band = 'medium') AS SIGNED)       AS medium_risk_count,
        CAST(SUM(risk_band = 'low')   AS SIGNED)        AS low_risk_count,
        ROUND(AVG(risk_score), 1)                       AS avg_risk_score
    FROM v_at_risk_students
    WHERE (p_branch_id IS NULL OR branch_code =
              (SELECT code FROM branches WHERE branch_id = p_branch_id))
      AND (p_semester  IS NULL OR semester = p_semester);
END$$


-- ---------------------------------------------------------------------
-- sp_promote_semester : move a whole cohort up one semester
-- ---------------------------------------------------------------------
-- An end-of-year administrative action. Students carrying two or more
-- backlogs are held back, which is why this cannot be a plain UPDATE.
CREATE PROCEDURE sp_promote_semester(
    IN  p_branch_id INT,
    IN  p_semester  TINYINT,
    OUT p_promoted  INT,
    OUT p_held      INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT COUNT(*) INTO p_held
    FROM v_student_overall
    WHERE branch_id = p_branch_id
      AND semester  = p_semester
      AND backlog_count >= 2;

    UPDATE students s
    SET s.semester = s.semester + 1
    WHERE s.branch_id = p_branch_id
      AND s.semester  = p_semester
      AND s.semester  < 8
      AND s.is_active = TRUE
      AND s.student_id NOT IN (
          SELECT student_id FROM v_student_overall
          WHERE backlog_count >= 2
      );

    SET p_promoted = ROW_COUNT();

    INSERT INTO audit_log (actor, action, entity, details)
    VALUES (@app_user, 'cohort.promote', 'branch',
            JSON_OBJECT('branch_id', p_branch_id, 'from_semester', p_semester,
                        'promoted', p_promoted, 'held_back', p_held));

    COMMIT;
END$$

DELIMITER ;
