# ExamFlow | University Examination Management System

Flask and Oracle application for managing examination workflows and demonstrating a deterministic finite automaton (DFA).

## Start here

- **Run and configure the app:** follow [Setup](#setup) below.
- **Learn the implementation and routes:** read [PROJECT_GUIDE.md](PROJECT_GUIDE.md).
- **Original workflow requirements:** see [PROJECT_SPEC.md](PROJECT_SPEC.md).
- **FSM and stored transitions:** inspect `fsm.py`, `MOC_PROJECT.sql`, and `schema_patch.sql`.

## What is included

- Student, Faculty, Admin, and ExamCell sign-in and dashboard flows.
- Exam catalogue with course-specific student enrollment and per-exam state tracking.
- Exam Cell faculty assignments, refund approval queue, hall-ticket queue, and result review.
- Faculty evaluation corrections with recorded reasons and before/after history.
- Nine lifecycle states and the 12-event transition relation in `fsm.py`.
- Oracle `FSM_STATES` and `FSM_TRANSITIONS` tables, role/event permissions, row locking, and an audit trail.
- Browser DFA diagram at `/fsm` and JSON model at `/api/fsm`.
- Research and project notes can be added as Markdown files in `papers/` and viewed at `/papers`.

## Prerequisites

- Python 3.10 or newer.
- Oracle Database XE running locally with a service named `XEPDB1`.
- A schema based on `MOC_PROJECT.sql` and permission to apply the one-time additions in `schema_patch.sql`.
- Permission to apply the one-time additive migration in `schema_exam_features.sql`.
- Permission to apply the one-time HOD course and teaching-assignment migration in `schema_hod_courses.sql`.

## Setup

1. Create and activate a virtual environment, then install the project dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Configure the Oracle connection and Flask session secret in the current PowerShell window. Use the password for your local Oracle account:

   ```powershell
   $env:ORACLE_USER = 'MOC_project'
   $env:ORACLE_PASSWORD = '<your Oracle password>'
   $env:ORACLE_DSN = 'localhost:1521/XEPDB1'
   $env:FLASK_SECRET_KEY = '<a long random value>'
   ```

3. For a **new, empty schema only**, connect as `MOC_project` and run `MOC_PROJECT.sql`, then `schema_patch.sql`, `schema_exam_features.sql`, and `schema_hod_courses.sql`, in that order. For an existing installation, apply only migrations that have not already been run. These migrations are one-time and are not idempotent. Do not rerun the base schema over existing tables. The exam-features migration adds the catalog and per-exam workflow; the HOD migration adds department ownership and term-based teaching assignments.

4. Run `demo_accounts.sql` to add missing local demo accounts without replacing existing records. The accounts use `admin@example.com`, `faculty@example.com`, `examcell@example.com`, `hod@example.com`, `demo.student@example.com`, and `flow.student@example.com`; the initial password for each is `password123`. A successful first sign-in upgrades each legacy demo hash. The HOD account is assigned to CSE. Use `demo.student@example.com` for a fresh Registered record; the separate `flow.student@example.com` record is reserved for a complete lifecycle demonstration.

5. Start the development server:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5000` in a browser. Change demo credentials before sharing the application.

## Demonstration path

1. Sign in as `demo.student@example.com`; inspect the current status and pay the examination fee.
2. Sign in as `examcell@example.com`; issue a hall ticket for the now-eligible student.
3. Sign in as `faculty@example.com`; mark attendance and submit an evaluation.
4. Sign back in as ExamCell and publish the evaluated result.
5. Sign in as `admin@example.com`; inspect the workflow counts and audit trail.
6. Open `/fsm`; compare the visualized DFA with `FSM_TRANSITIONS` in Oracle.

The demo database password hash is seeded for the first login only. Payment callback behavior is simulated and is not a real payment integration. Local demo accounts and sample data are not suitable for production use.

## Database objects

`MOC_PROJECT.sql` creates the base relational schema. `schema_patch.sql` adds columns required by the initial web forms, then creates `FSM_STATES` and `FSM_TRANSITIONS`. `schema_exam_features.sql` adds exams, per-exam faculty access, enrollments, refund requests, and evaluation history. `schema_hod_courses.sql` adds HOD department ownership and a term-based course-to-faculty assignment history. HOD teaching assignments inform the faculty options for new exams; Exam Cell still chooses exam-specific visibility. The Python engine checks each state/event against both the in-memory DFA and Oracle before persisting a transition. The `get_db` context manager commits or rolls back associated work as one transaction.

To add a course, sign in as an HOD and use **Course catalog → Add a course**. To assign or change instructors, use **Faculty assignments**. Admins choose the home department when creating Faculty and HOD accounts, and choose a student's course when creating Student accounts.

## Known environment note

If SQL*Plus reports `ORA-12638: Credential retrieval failed`, check the local Oracle client authentication configuration and service before treating it as an application schema error. This error occurred during the initial read-only connectivity check in the development environment. Configure `ORACLE_PASSWORD` in the same shell used to run Flask; do not put credentials in source files.

If application login shows a database connection message, check that the Flask process has the correct `ORACLE_USER`, `ORACLE_PASSWORD`, and `ORACLE_DSN` values. `ORA-01017` means Oracle rejected the credentials; repeated rejected logins can lock the schema and produce `ORA-28000`. A database administrator must unlock the account before the app can use it again. Do not repeatedly retry a password that Oracle has rejected.

Add project articles or literature notes as `.md` files in `papers/`; the website lists those files automatically. Do not claim performance results unless you have measured them.
