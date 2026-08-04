-- =====================================================================
--  Foresight - Views
-- =====================================================================
--  Run after schema.sql:
--      mysql -u root -p foresight < database/views.sql
--
--  Why views instead of doing this in Python?
--
--  Percentages, ranks and pass-rates are *derived* facts. If every route
--  recalculated them inline, two routes would eventually disagree with
--  each other. Defining them once in SQL means the dashboard, the CSV
--  export and the at-risk report are mathematically guaranteed to agree.
--
--  The views build on each other in layers:
--
--      v_enrollment_summary   one row per (student, subject)
--            |
--            +--> v_student_overall    one row per student
--            |         |
--            |         +--> v_student_rank      adds rank + percentile
--            |                   |
--            |                   +--> v_at_risk_students
--            |
--            +--> v_subject_stats      one row per subject
-- =====================================================================

USE foresight;

-- Pin the client connection's character set for the rest of this script.
-- Without it, the mysql command-line client on Windows connects as cp850
-- (the console codepage), and the explicit COLLATE further down fails
-- with "COLLATION 'utf8mb4_unicode_ci' is not valid for CHARACTER SET
-- 'cp850'" - so two views silently never get created. Setting it here
-- makes the file work regardless of how the client was invoked, rather
-- than depending on the caller remembering --default-character-set.
SET NAMES utf8mb4;


-- ---------------------------------------------------------------------
-- v_enrollment_summary : the base layer - one row per student/subject
-- ---------------------------------------------------------------------
-- Two derived numbers are defined here, and everything else in the
-- system inherits them:
--
--   mark_percent
--     SUM(obtained) / SUM(max) * 100.
--     Summing before dividing is deliberate: it weights each assessment
--     by how much it was worth, so a 100-mark final counts five times a
--     20-mark quiz. Averaging the individual percentages instead would
--     wrongly treat them as equally important.
--
--   attendance_percent
--     (present + late) / (total classes - excused) * 100.
--     'late' still means the student showed up. 'excused' is removed
--     from the denominator entirely rather than counted as an absence,
--     because an approved absence should not damage the percentage.
CREATE OR REPLACE VIEW v_enrollment_summary AS
SELECT
    e.enrollment_id,
    e.student_id,
    e.subject_id,
    e.academic_year,
    s.name          AS student_name,
    s.roll_no,
    s.branch_id,
    s.semester,
    sub.code        AS subject_code,
    sub.name        AS subject_name,
    sub.credits,
    sub.pass_mark,

    -- Marks
    COUNT(DISTINCT a.assessment_id) AS assessment_count,
    ROUND(
        CASE WHEN COALESCE(SUM(a.max_marks), 0) = 0 THEN NULL
             ELSE SUM(a.marks_obtained) / SUM(a.max_marks) * 100
        END, 2)                      AS mark_percent,

    -- Attendance. Aggregated in a subquery rather than joined directly,
    -- because joining two child tables at once multiplies the rows and
    -- would silently corrupt both averages.
    att.total_classes,
    att.attended_classes,
    ROUND(
        CASE WHEN COALESCE(att.counted_classes, 0) = 0 THEN NULL
             ELSE att.attended_classes / att.counted_classes * 100
        END, 2)                      AS attendance_percent
FROM enrollments e
JOIN students s   ON s.student_id  = e.student_id
JOIN subjects sub ON sub.subject_id = e.subject_id
LEFT JOIN assessments a ON a.enrollment_id = e.enrollment_id
LEFT JOIN (
    SELECT
        enrollment_id,
        COUNT(*)                          AS total_classes,
        SUM(status IN ('present','late')) AS attended_classes,
        SUM(status <> 'excused')          AS counted_classes
    FROM attendance_records
    GROUP BY enrollment_id
) att ON att.enrollment_id = e.enrollment_id
GROUP BY
    e.enrollment_id, e.student_id, e.subject_id, e.academic_year,
    s.name, s.roll_no, s.branch_id, s.semester,
    sub.code, sub.name, sub.credits, sub.pass_mark,
    att.total_classes, att.attended_classes, att.counted_classes;


-- ---------------------------------------------------------------------
-- v_student_overall : one row per student
-- ---------------------------------------------------------------------
-- The overall mark is credit-weighted, matching how a real GPA works:
-- a 4-credit subject moves the average twice as much as a 2-credit one.
CREATE OR REPLACE VIEW v_student_overall AS
SELECT
    v.student_id,
    v.student_name,
    v.roll_no,
    v.branch_id,
    b.code                       AS branch_code,
    v.semester,
    COUNT(*)                     AS subject_count,

    ROUND(
        CASE WHEN SUM(CASE WHEN v.mark_percent IS NULL THEN 0 ELSE v.credits END) = 0
             THEN NULL
             ELSE SUM(v.mark_percent * v.credits)
                  / SUM(CASE WHEN v.mark_percent IS NULL THEN 0 ELSE v.credits END)
        END, 2)                  AS avg_mark_percent,

    ROUND(AVG(v.attendance_percent), 2) AS avg_attendance_percent,

    -- A backlog is a subject sitting below that subject's own pass mark.
    -- SUM() of a boolean returns DECIMAL, which would reach the API as
    -- 2.0 rather than 2; a count should be an integer.
    CAST(SUM(v.mark_percent < v.pass_mark) AS SIGNED) AS backlog_count,
    MIN(v.mark_percent)                 AS lowest_subject_percent,
    MAX(v.mark_percent)                 AS highest_subject_percent
FROM v_enrollment_summary v
JOIN branches b ON b.branch_id = v.branch_id
GROUP BY
    v.student_id, v.student_name, v.roll_no,
    v.branch_id, b.code, v.semester;


-- ---------------------------------------------------------------------
-- v_student_rank : adds cohort rank and percentile
-- ---------------------------------------------------------------------
-- "Cohort" = same branch AND same semester. Ranking a 3rd-semester CSE
-- student against a 2nd-semester AIML student would be meaningless.
--
-- RANK() (not ROW_NUMBER) so that tied averages genuinely share a rank.
-- PERCENT_RANK() returns 0..1 ascending, so ordering ASC makes a high
-- number mean "ahead of most peers" - the familiar percentile reading.
CREATE OR REPLACE VIEW v_student_rank AS
SELECT
    o.student_id,
    o.student_name,
    o.roll_no,
    o.branch_id,
    o.branch_code,
    o.semester,
    o.subject_count,
    o.avg_mark_percent,
    o.avg_attendance_percent,
    o.backlog_count,
    o.lowest_subject_percent,
    o.highest_subject_percent,
    RANK()   OVER (PARTITION BY o.branch_id, o.semester
                   ORDER BY o.avg_mark_percent DESC)      AS class_rank,
    COUNT(*) OVER (PARTITION BY o.branch_id, o.semester)  AS cohort_size,
    ROUND(
        PERCENT_RANK() OVER (PARTITION BY o.branch_id, o.semester
                             ORDER BY o.avg_mark_percent ASC) * 100
    , 1)                                                  AS percentile
FROM v_student_overall o;


-- ---------------------------------------------------------------------
-- v_subject_stats : one row per subject, for the admin console
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_subject_stats AS
SELECT
    v.subject_id,
    v.subject_code,
    v.subject_name,
    v.branch_id,
    b.code                                  AS branch_code,
    v.semester,
    COUNT(*)                                AS enrolled_count,
    ROUND(AVG(v.mark_percent), 2)           AS avg_mark_percent,
    ROUND(MIN(v.mark_percent), 2)           AS min_mark_percent,
    ROUND(MAX(v.mark_percent), 2)           AS max_mark_percent,
    ROUND(STDDEV_SAMP(v.mark_percent), 2)   AS stddev_mark_percent,
    ROUND(AVG(v.attendance_percent), 2)     AS avg_attendance_percent,
    CAST(SUM(v.mark_percent >= v.pass_mark) AS SIGNED) AS passed_count,
    CAST(SUM(v.mark_percent <  v.pass_mark) AS SIGNED) AS failed_count,
    ROUND(
        CASE WHEN COUNT(v.mark_percent) = 0 THEN NULL
             ELSE SUM(v.mark_percent >= v.pass_mark) / COUNT(v.mark_percent) * 100
        END, 1)                             AS pass_rate
FROM v_enrollment_summary v
JOIN branches b ON b.branch_id = v.branch_id
GROUP BY
    v.subject_id, v.subject_code, v.subject_name,
    v.branch_id, b.code, v.semester;


-- ---------------------------------------------------------------------
-- v_at_risk_students : the flagship report
-- ---------------------------------------------------------------------
-- The original project called a student "Weak" if marks < 40 OR
-- attendance < 60. That is a single hard cliff: 39.9 with three backlogs
-- looked identical to 39.9 with none.
--
-- This computes a 0-100 risk score from four weighted signals, so the
-- output can be ranked by severity instead of merely filtered. The
-- Python layer (services/analytics.py) mirrors these exact weights when
-- it explains *why* a student was flagged.
--
--     marks below 40         -> up to 40 points
--     attendance below 75    -> up to 30 points
--     each backlog           -> 10 points, capped at 20
--     bottom-quartile rank   -> 10 points
CREATE OR REPLACE VIEW v_at_risk_students AS
SELECT
    r.student_id,
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

    LEAST(100, GREATEST(0,
          -- Marks shortfall, scaled so 0% marks costs the full 40 points.
          CASE WHEN r.avg_mark_percent IS NULL THEN 0
               WHEN r.avg_mark_percent >= 40 THEN 0
               ELSE (40 - r.avg_mark_percent) / 40 * 40 END
        + -- Attendance shortfall against the standard 75% requirement.
          CASE WHEN r.avg_attendance_percent IS NULL THEN 0
               WHEN r.avg_attendance_percent >= 75 THEN 0
               ELSE (75 - r.avg_attendance_percent) / 75 * 30 END
        + -- Backlogs, capped so one weak subject does not dominate.
          LEAST(20, r.backlog_count * 10)
        + -- Standing relative to peers.
          CASE WHEN r.percentile < 25 THEN 10 ELSE 0 END
    )) AS risk_score,

    -- The explicit COLLATE is not decoration. A CASE expression's string
    -- literals take whatever collation the session had when the view was
    -- created, while the tables are utf8mb4_unicode_ci. Without this,
    -- `WHERE risk_band IN ('high','medium')` fails at runtime with
    -- "Illegal mix of collations" - and only for the caller whose
    -- session default happens to differ, which is a miserable bug to
    -- track down. Pinning it here makes the view's output collation a
    -- property of the view rather than of whoever created it.
    CASE
        WHEN r.avg_mark_percent IS NULL THEN 'unknown'
        WHEN r.avg_mark_percent < 40 OR r.avg_attendance_percent < 60
             OR r.backlog_count >= 2                        THEN 'high'
        WHEN r.avg_mark_percent < 55 OR r.avg_attendance_percent < 75
             OR r.backlog_count = 1                         THEN 'medium'
        ELSE 'low'
    END COLLATE utf8mb4_unicode_ci AS risk_band
FROM v_student_rank r;


-- ---------------------------------------------------------------------
-- v_assessment_trend : marks over time, for the trend chart
-- ---------------------------------------------------------------------
-- Each assessment is normalised to a percentage so that a 20-mark quiz
-- and a 100-mark final can share one axis.
CREATE OR REPLACE VIEW v_assessment_trend AS
SELECT
    e.student_id,
    e.subject_id,
    sub.code                AS subject_code,
    sub.name                AS subject_name,
    a.assessment_id,
    a.type,
    a.assessed_on,
    a.marks_obtained,
    a.max_marks,
    ROUND(a.marks_obtained / a.max_marks * 100, 2) AS percent
FROM assessments a
JOIN enrollments e ON e.enrollment_id = a.enrollment_id
JOIN subjects sub  ON sub.subject_id  = e.subject_id;
