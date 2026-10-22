-- --------------------------------------------------------
-- schema_patch.sql
-- Adds extra columns to HALL_TICKETS, FEE_PAYMENTS, MARKS
-- that the Flask routes expect.
-- Run this in Oracle SQL*Plus as MOC_project user.
-- --------------------------------------------------------

-- HALL_TICKETS: add issue_date, exam_center, seat_number, qr_code
ALTER TABLE HALL_TICKETS ADD (
    ISSUE_DATE   DATE          DEFAULT SYSDATE,
    EXAM_CENTER  VARCHAR2(100) DEFAULT 'Main Examination Hall',
    SEAT_NUMBER  VARCHAR2(10),
    QR_CODE      VARCHAR2(50)
);

-- FEE_PAYMENTS: add TRANSACTION_ID column
ALTER TABLE FEE_PAYMENTS ADD (
    TRANSACTION_ID VARCHAR2(50)
);

-- MARKS: add SUBJECT_CODE, SUBJECT_NAME, MAX_MARKS, GRADE, EVALUATED_BY, EVALUATION_DATE
-- (keep existing COURSE_CODE, MARKS_OBTAINED, ENTERED_BY, VERIFIED_BY for backward compat)
ALTER TABLE MARKS ADD (
    SUBJECT_CODE    VARCHAR2(10),
    SUBJECT_NAME    VARCHAR2(100),
    MAX_MARKS       NUMBER(5,2) DEFAULT 100,
    GRADE           VARCHAR2(5),
    EVALUATED_BY    NUMBER,
    EVALUATION_DATE DATE
);

-- Add FK for EVALUATED_BY → USERS
ALTER TABLE MARKS ADD CONSTRAINT FK_MARKS_EVAL
    FOREIGN KEY (EVALUATED_BY) REFERENCES USERS(USER_ID);

-- Theory of Computation demonstration: the DFA's transition relation is
-- stored in Oracle and checked against the Python implementation at runtime.
CREATE TABLE FSM_STATES (
    STATE_NAME VARCHAR2(30) PRIMARY KEY,
    IS_TERMINAL CHAR(1) DEFAULT 'N' NOT NULL CHECK (IS_TERMINAL IN ('Y','N'))
);

CREATE TABLE FSM_TRANSITIONS (
    FROM_STATE VARCHAR2(30) NOT NULL REFERENCES FSM_STATES(STATE_NAME),
    EVENT VARCHAR2(30) NOT NULL,
    TO_STATE VARCHAR2(30) NOT NULL REFERENCES FSM_STATES(STATE_NAME),
    CONSTRAINT PK_FSM_TRANSITIONS PRIMARY KEY (FROM_STATE, EVENT)
);

INSERT INTO FSM_STATES VALUES ('Registered','N');
INSERT INTO FSM_STATES VALUES ('FeePaid','N');
INSERT INTO FSM_STATES VALUES ('HallTicketIssued','N');
INSERT INTO FSM_STATES VALUES ('ExamTaken','N');
INSERT INTO FSM_STATES VALUES ('Evaluated','N');
INSERT INTO FSM_STATES VALUES ('UnderReview','N');
INSERT INTO FSM_STATES VALUES ('ResultPublished','Y');
INSERT INTO FSM_STATES VALUES ('Cancelled','Y');
INSERT INTO FSM_STATES VALUES ('Absent','Y');

INSERT INTO FSM_TRANSITIONS VALUES ('Registered','pay_fee','FeePaid');
INSERT INTO FSM_TRANSITIONS VALUES ('Registered','payment_failed','Registered');
INSERT INTO FSM_TRANSITIONS VALUES ('Registered','cancel_registration','Cancelled');
INSERT INTO FSM_TRANSITIONS VALUES ('FeePaid','generate_hall_ticket','HallTicketIssued');
INSERT INTO FSM_TRANSITIONS VALUES ('FeePaid','request_refund','Registered');
INSERT INTO FSM_TRANSITIONS VALUES ('HallTicketIssued','mark_attendance','ExamTaken');
INSERT INTO FSM_TRANSITIONS VALUES ('HallTicketIssued','mark_absent','Absent');
INSERT INTO FSM_TRANSITIONS VALUES ('ExamTaken','submit_evaluation','Evaluated');
INSERT INTO FSM_TRANSITIONS VALUES ('Evaluated','flag_discrepancy','UnderReview');
INSERT INTO FSM_TRANSITIONS VALUES ('Evaluated','publish_result','ResultPublished');
INSERT INTO FSM_TRANSITIONS VALUES ('UnderReview','revert_evaluation','ExamTaken');
INSERT INTO FSM_TRANSITIONS VALUES ('UnderReview','confirm_evaluation','Evaluated');

-- The stated role/event policy is the authority for both UI actions and
-- transition requests. HOD is retained as an account role but is read-only.
UPDATE PERMISSIONS SET ROLE = 'ExamCell'
WHERE ROLE = 'HOD' AND EVENT IN ('confirm_evaluation','revert_evaluation');
MERGE INTO PERMISSIONS p USING (SELECT 'ExamCell' role, 'confirm_evaluation' event FROM dual) s
ON (p.role = s.role AND p.event = s.event)
WHEN NOT MATCHED THEN INSERT (role,event) VALUES (s.role,s.event);
MERGE INTO PERMISSIONS p USING (SELECT 'ExamCell' role, 'revert_evaluation' event FROM dual) s
ON (p.role = s.role AND p.event = s.event)
WHEN NOT MATCHED THEN INSERT (role,event) VALUES (s.role,s.event);

COMMIT;

COMMIT;
