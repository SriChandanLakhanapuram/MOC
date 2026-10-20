-- Safe, repeatable demo-account seed for an existing MOC_PROJECT schema.
-- All demo accounts use password: password123 (legacy hash; upgraded on login).
-- Run only in the local coursework schema after schema_hod_courses.sql.

MERGE INTO USERS u USING (
  SELECT 'Mira Administrator' name, 'admin@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'Admin' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO USERS u USING (
  SELECT 'Dev Faculty' name, 'faculty@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'Faculty' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO USERS u USING (
  SELECT 'Esha Exam Cell' name, 'examcell@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'ExamCell' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO USERS u USING (
  SELECT 'Kiran Department Head' name, 'hod@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'HOD' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO USERS u USING (
  SELECT 'Nila Demo Student' name, 'demo.student@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'Student' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO USERS u USING (
  SELECT 'Ravi Workflow Student' name, 'flow.student@example.com' email,
         'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f' password_hash,
         'Student' role FROM dual
) d ON (u.email = d.email)
WHEN NOT MATCHED THEN INSERT (name,email,password_hash,role)
VALUES (d.name,d.email,d.password_hash,d.role);

MERGE INTO FACULTY f USING (
  SELECT user_id FROM USERS WHERE email = 'faculty@example.com'
) d ON (f.user_id = d.user_id)
WHEN NOT MATCHED THEN INSERT (faculty_id,user_id,department)
VALUES ('FDEMO01',d.user_id,'CSE');

MERGE INTO HOD_DEPARTMENTS h USING (
  SELECT user_id,'CSE' department FROM users WHERE email='hod@example.com'
) d ON (h.user_id=d.user_id AND h.department=d.department)
WHEN NOT MATCHED THEN INSERT (user_id,department,assigned_by)
VALUES (d.user_id,d.department,(SELECT user_id FROM users WHERE email='admin@example.com'));

MERGE INTO STUDENTS s USING (
  SELECT user_id, (SELECT MIN(course_code) FROM COURSES) course_code
  FROM USERS WHERE email = 'demo.student@example.com'
) d ON (s.user_id = d.user_id)
WHEN NOT MATCHED THEN INSERT (student_id,user_id,course_code,exam_status)
VALUES ('SDEMO02',d.user_id,d.course_code,'Registered');

MERGE INTO STUDENTS s USING (
  SELECT user_id, (SELECT MIN(course_code) FROM COURSES) course_code
  FROM USERS WHERE email = 'flow.student@example.com'
) d ON (s.user_id = d.user_id)
WHEN NOT MATCHED THEN INSERT (student_id,user_id,course_code,exam_status)
VALUES ('SDEMO03',d.user_id,d.course_code,'Registered');

COMMIT;
