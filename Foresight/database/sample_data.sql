-- =====================================================================
--  Foresight - Reference Data
-- =====================================================================
--  Run after schema.sql:
--      mysql -u root -p foresight < database/sample_data.sql
--
--  This file holds only *reference* data - the branches and subjects a
--  college actually offers. It deliberately contains no user accounts
--  and no password hashes: committing credentials to a repository is a
--  habit worth not forming, even on a student project.
--
--  Demo students, marks and attendance history are generated instead by
--      python backend/seed_demo.py
--  which creates the accounts and prints the login details once.
-- =====================================================================

USE foresight;

-- Pin the client character set; see the note in views.sql. Without it
-- the Windows mysql client connects as cp850 and utf8mb4 collations
-- are rejected mid-script.
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- Branches
-- ---------------------------------------------------------------------
INSERT INTO branches (code, name) VALUES
    ('CSE',  'Computer Science & Engineering'),
    ('AIML', 'Artificial Intelligence & Machine Learning'),
    ('ECE',  'Electronics & Communication Engineering')
AS new
ON DUPLICATE KEY UPDATE name = new.name;


-- ---------------------------------------------------------------------
-- Subjects
-- ---------------------------------------------------------------------
-- `pass_mark` is per subject rather than a global constant because a lab
-- or project subject usually carries a different bar than a theory paper.
INSERT INTO subjects (code, name, branch_id, semester, credits, pass_mark)
SELECT t.code, t.name, b.branch_id, t.semester, t.credits, t.pass_mark
FROM (
    -- CSE, semester 3
    SELECT 'CS301' AS code, 'Database Management Systems' AS name,
           'CSE' AS branch, 3 AS semester, 4 AS credits, 40 AS pass_mark
    UNION ALL SELECT 'CS302', 'Operating Systems',           'CSE', 3, 4, 40
    UNION ALL SELECT 'CS303', 'Computer Networks',           'CSE', 3, 3, 40
    UNION ALL SELECT 'CS304', 'Data Structures & Algorithms','CSE', 3, 4, 40
    UNION ALL SELECT 'MA301', 'Discrete Mathematics',        'CSE', 3, 3, 40

    -- CSE, semester 5
    UNION ALL SELECT 'CS501', 'Software Engineering',        'CSE', 5, 4, 40
    UNION ALL SELECT 'CS502', 'Compiler Design',             'CSE', 5, 4, 40
    UNION ALL SELECT 'CS503', 'Web Technologies',            'CSE', 5, 3, 45
    UNION ALL SELECT 'CS504', 'Theory of Computation',       'CSE', 5, 3, 40

    -- AIML, semester 3
    UNION ALL SELECT 'AI301', 'Machine Learning Foundations','AIML', 3, 4, 40
    UNION ALL SELECT 'AI302', 'Python for Data Science',     'AIML', 3, 3, 45
    UNION ALL SELECT 'AI303', 'Linear Algebra & Statistics', 'AIML', 3, 4, 40
    UNION ALL SELECT 'AI304', 'Data Structures',             'AIML', 3, 4, 40
    UNION ALL SELECT 'AI305', 'Neural Networks',             'AIML', 3, 3, 40

    -- ECE, semester 3
    UNION ALL SELECT 'EC301', 'Digital Electronics',         'ECE', 3, 4, 40
    UNION ALL SELECT 'EC302', 'Signals & Systems',           'ECE', 3, 4, 40
    UNION ALL SELECT 'EC303', 'Analog Circuits',             'ECE', 3, 3, 40
    UNION ALL SELECT 'EC304', 'Microprocessors',             'ECE', 3, 4, 40
) AS t
JOIN branches b ON b.code = t.branch
ON DUPLICATE KEY UPDATE
    name     = VALUES(name),
    credits  = VALUES(credits),
    pass_mark= VALUES(pass_mark);
