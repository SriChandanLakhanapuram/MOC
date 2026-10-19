-- =============================================================================
-- seed_data.sql — University Examination Management System
-- =============================================================================
-- Inserts realistic seed data into all tables.
-- 
-- ASSUMPTIONS / NOTES:
--   • USER_ID=1 (superadmin), STUDENT_ID='S000123', COURSE_CODE='CS301'
--     already exist — this script starts from USER_ID=10 and uses new IDs.
--   • Password hashes are SHA-256 hex digests:
--       'password123' → ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
--       'admin123'    → 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
--       'faculty123'  → 2a36d4c5f4c2c9d47b3e7f8a1b0c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9
--   • Oracle does not support multi-row VALUES clauses; each INSERT is separate.
-- =============================================================================

-- -------------------------------------------------------
-- SECTION 1: COURSES  (CS301 already exists)
-- -------------------------------------------------------
INSERT INTO courses (course_code, course_name, credits, department)
VALUES ('CS302', 'Design and Analysis of Algorithms', 4, 'Computer Science');

INSERT INTO courses (course_code, course_name, credits, department)
VALUES ('CS303', 'Operating Systems', 4, 'Computer Science');

INSERT INTO courses (course_code, course_name, credits, department)
VALUES ('CS401', 'Database Management Systems', 3, 'Computer Science');

INSERT INTO courses (course_code, course_name, credits, department)
VALUES ('CS402', 'Theory of Computation', 3, 'Computer Science');

-- -------------------------------------------------------
-- SECTION 2: USERS
-- -------------------------------------------------------

-- ---- Admins (user_id 10, 11) ----
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (10, 'Alice Admin', 'admin1@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'Admin');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (11, 'Bob Admin', 'admin2@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'Admin');

-- ---- Students (user_id 20–25) ----
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (20, 'Riya Sharma', 'student1@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (21, 'Arjun Mehta', 'student2@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (22, 'Priya Nair', 'student3@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (23, 'Kiran Patel', 'student4@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (24, 'Sneha Rao', 'student5@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (25, 'Vikram Joshi', 'student6@exam.edu',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'Student');

-- ---- Faculty (user_id 30–32) ----
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (30, 'Dr. Meena Iyer', 'faculty1@exam.edu',
        '2a36d4c5f4c2c9d47b3e7f8a1b0c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9',
        'Faculty');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (31, 'Prof. Suresh Kumar', 'faculty2@exam.edu',
        '2a36d4c5f4c2c9d47b3e7f8a1b0c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9',
        'Faculty');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (32, 'Dr. Anita Desai', 'faculty3@exam.edu',
        '2a36d4c5f4c2c9d47b3e7f8a1b0c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9',
        'Faculty');

-- ---- ExamCell (user_id 40, 41) ----
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (40, 'Ramesh Verma', 'examcell1@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'ExamCell');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (41, 'Sunita Pillai', 'examcell2@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'ExamCell');

-- ---- HOD (user_id 50, 51) ----
INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (50, 'Prof. Rajesh Gupta', 'hod1@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'HOD');

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES (51, 'Prof. Kavitha Menon', 'hod2@exam.edu',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'HOD');

-- -------------------------------------------------------
-- SECTION 3: FACULTY records (linked to user accounts)
-- -------------------------------------------------------
INSERT INTO faculty (faculty_id, user_id, department, designation)
VALUES ('FAC001', 30, 'Computer Science', 'Assistant Professor');

INSERT INTO faculty (faculty_id, user_id, department, designation)
VALUES ('FAC002', 31, 'Computer Science', 'Associate Professor');

INSERT INTO faculty (faculty_id, user_id, department, designation)
VALUES ('FAC003', 32, 'Computer Science', 'Professor');

-- -------------------------------------------------------
-- SECTION 4: STUDENTS (10 students, various FSM states)
-- -------------------------------------------------------
-- S001 & S002 → Registered  (initial state, no payment yet)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S001', 20, 'CS302', 'Registered', 3, '2024-25');

INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S002', 21, 'CS303', 'Registered', 3, '2024-25');

-- S003 & S004 → FeePaid  (paid fee, hall ticket not yet issued)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S003', 22, 'CS302', 'FeePaid', 3, '2024-25');

INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S004', 23, 'CS401', 'FeePaid', 4, '2024-25');

-- S005 & S006 → HallTicketIssued  (hall ticket generated)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S005', 24, 'CS402', 'HallTicketIssued', 4, '2024-25');

INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S006', 25, 'CS303', 'HallTicketIssued', 3, '2024-25');

-- S007 → ExamTaken  (sat the exam, awaiting evaluation)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S007', 20, 'CS401', 'ExamTaken', 4, '2024-25');

-- S008 → Evaluated  (marks submitted, awaiting publication)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S008', 21, 'CS402', 'Evaluated', 4, '2024-25');

-- S009 → UnderReview  (discrepancy flagged)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S009', 22, 'CS303', 'UnderReview', 3, '2024-25');

-- S010 → ResultPublished  (terminal accepting state)
INSERT INTO students (student_id, user_id, course_code, exam_status, semester, academic_year)
VALUES ('S010', 23, 'CS302', 'ResultPublished', 3, '2024-25');

-- -------------------------------------------------------
-- SECTION 5: FEE PAYMENTS  (for FeePaid and beyond)
-- -------------------------------------------------------
-- S003 paid fee
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1001, 'S003', 1500.00, DATE '2024-10-01', 'Success', 'TXN-S003-20241001');

-- S004 paid fee
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1002, 'S004', 1500.00, DATE '2024-10-02', 'Success', 'TXN-S004-20241002');

-- S005 paid fee (HallTicketIssued — payment precedes hall ticket)
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1003, 'S005', 1500.00, DATE '2024-10-01', 'Success', 'TXN-S005-20241001');

-- S006 paid fee
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1004, 'S006', 1500.00, DATE '2024-10-01', 'Success', 'TXN-S006-20241001');

-- S007 paid fee (ExamTaken)
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1005, 'S007', 1500.00, DATE '2024-09-28', 'Success', 'TXN-S007-20240928');

-- S008 paid fee (Evaluated)
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1006, 'S008', 1500.00, DATE '2024-09-28', 'Success', 'TXN-S008-20240928');

-- S009 paid fee (UnderReview)
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1007, 'S009', 1500.00, DATE '2024-09-27', 'Success', 'TXN-S009-20240927');

-- S010 paid fee (ResultPublished)
INSERT INTO fee_payments (payment_id, student_id, amount, payment_date, payment_status, transaction_ref)
VALUES (1008, 'S010', 1500.00, DATE '2024-09-25', 'Success', 'TXN-S010-20240925');

-- -------------------------------------------------------
-- SECTION 6: HALL TICKETS  (for HallTicketIssued and beyond)
-- -------------------------------------------------------
-- S005
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S005-CS402', 'S005', DATE '2024-10-10', DATE '2024-11-15', 'Room-A101', 'A-15');

-- S006
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S006-CS303', 'S006', DATE '2024-10-10', DATE '2024-11-14', 'Room-B202', 'B-07');

-- S007 (ExamTaken — had a hall ticket)
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S007-CS401', 'S007', DATE '2024-10-05', DATE '2024-11-10', 'Room-A101', 'A-22');

-- S008 (Evaluated — had a hall ticket)
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S008-CS402', 'S008', DATE '2024-10-05', DATE '2024-11-12', 'Room-C303', 'C-03');

-- S009 (UnderReview — had a hall ticket)
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S009-CS303', 'S009', DATE '2024-10-04', DATE '2024-11-11', 'Room-B202', 'B-18');

-- S010 (ResultPublished — had a hall ticket)
INSERT INTO hall_tickets (ticket_id, student_id, issued_date, exam_date, exam_room, seat_number)
VALUES ('HT-S010-CS302', 'S010', DATE '2024-10-03', DATE '2024-11-09', 'Room-A101', 'A-05');

-- -------------------------------------------------------
-- SECTION 7: MARKS (for Evaluated, UnderReview, ResultPublished)
-- -------------------------------------------------------
-- S008 — Evaluated, marks submitted
INSERT INTO marks (mark_id, student_id, course_code, faculty_id, internal_marks, external_marks, total_marks, grade)
VALUES (2001, 'S008', 'CS402', 'FAC003', 38, 55, 93, 'A+');

-- S009 — UnderReview (discrepancy flagged on these marks)
INSERT INTO marks (mark_id, student_id, course_code, faculty_id, internal_marks, external_marks, total_marks, grade)
VALUES (2002, 'S009', 'CS303', 'FAC002', 30, 41, 71, 'B');

-- S010 — ResultPublished
INSERT INTO marks (mark_id, student_id, course_code, faculty_id, internal_marks, external_marks, total_marks, grade)
VALUES (2003, 'S010', 'CS302', 'FAC001', 35, 58, 93, 'A+');

-- -------------------------------------------------------
-- SECTION 8: AUDIT LOG  (history of FSM transitions)
-- -------------------------------------------------------

-- S003: Registered → FeePaid  (student paid fee)
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (22, 'S003', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-10-01 10:15:00');

-- S004: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (23, 'S004', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-10-02 09:30:00');

-- S005: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (24, 'S005', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-10-01 11:00:00');

-- S005: FeePaid → HallTicketIssued  (exam cell issued ticket)
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (40, 'S005', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-10 14:00:00');

-- S006: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (25, 'S006', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-10-01 12:00:00');

-- S006: FeePaid → HallTicketIssued
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (40, 'S006', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-10 14:05:00');

-- S007: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (20, 'S007', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-09-28 10:00:00');

-- S007: FeePaid → HallTicketIssued
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (40, 'S007', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-05 09:00:00');

-- S007: HallTicketIssued → ExamTaken  (faculty marked attendance)
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (30, 'S007', 'mark_attendance', 'HallTicketIssued', 'ExamTaken', TIMESTAMP '2024-11-10 10:30:00');

-- S008: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (21, 'S008', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-09-28 11:00:00');

-- S008: FeePaid → HallTicketIssued
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (41, 'S008', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-05 09:30:00');

-- S008: HallTicketIssued → ExamTaken
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (32, 'S008', 'mark_attendance', 'HallTicketIssued', 'ExamTaken', TIMESTAMP '2024-11-12 10:00:00');

-- S008: ExamTaken → Evaluated  (faculty submitted evaluation)
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (32, 'S008', 'submit_evaluation', 'ExamTaken', 'Evaluated', TIMESTAMP '2024-11-20 16:00:00');

-- S009: Registered → FeePaid
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (22, 'S009', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-09-27 10:00:00');

-- S009: FeePaid → HallTicketIssued
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (41, 'S009', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-04 09:00:00');

-- S009: HallTicketIssued → ExamTaken
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (31, 'S009', 'mark_attendance', 'HallTicketIssued', 'ExamTaken', TIMESTAMP '2024-11-11 10:00:00');

-- S009: ExamTaken → Evaluated
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (31, 'S009', 'submit_evaluation', 'ExamTaken', 'Evaluated', TIMESTAMP '2024-11-18 15:00:00');

-- S009: Evaluated → UnderReview  (student or faculty flagged discrepancy)
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (31, 'S009', 'flag_discrepancy', 'Evaluated', 'UnderReview', TIMESTAMP '2024-11-22 11:00:00');

-- S010: Full journey — Registered → FeePaid → HallTicketIssued → ExamTaken → Evaluated → ResultPublished
INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (23, 'S010', 'pay_fee', 'Registered', 'FeePaid', TIMESTAMP '2024-09-25 10:00:00');

INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (40, 'S010', 'generate_hall_ticket', 'FeePaid', 'HallTicketIssued', TIMESTAMP '2024-10-03 09:00:00');

INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (30, 'S010', 'mark_attendance', 'HallTicketIssued', 'ExamTaken', TIMESTAMP '2024-11-09 10:00:00');

INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (30, 'S010', 'submit_evaluation', 'ExamTaken', 'Evaluated', TIMESTAMP '2024-11-16 14:00:00');

INSERT INTO audit_log (user_id, student_id, event, old_state, new_state, changed_at)
VALUES (40, 'S010', 'publish_result', 'Evaluated', 'ResultPublished', TIMESTAMP '2024-11-25 10:00:00');

-- -------------------------------------------------------
-- COMMIT all changes
-- -------------------------------------------------------
COMMIT;
