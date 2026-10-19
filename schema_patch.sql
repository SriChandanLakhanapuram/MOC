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

COMMIT;
