# University Examination Management System

Flask and Oracle prototype for demonstrating role-based examination workflows and a deterministic finite automaton (DFA).

## What is included

- Student, Faculty, Admin, and ExamCell sign-in and dashboard flows.
- Nine lifecycle states and the 12-event transition relation in `fsm.py`.
- Oracle `FSM_STATES` and `FSM_TRANSITIONS` tables, role/event permissions, row locking, and an audit trail.
- Browser DFA diagram at `/fsm` and JSON model at `/api/fsm`.
- Project report at `/papers`.

## Prerequisites

- Python 3.10 or newer.
- Oracle Database XE running locally with a service named `XEPDB1`.
- A schema based on `MOC_PROJECT.sql` and permission to apply the one-time additions in `schema_patch.sql`.

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

3. For a **new, empty schema only**, connect as `MOC_project` and run `MOC_PROJECT.sql`. For an existing installation, inspect its tables and columns before applying `schema_patch.sql`; it is a one-time migration and is not idempotent. Do not rerun the base schema over existing tables. The reviewed migration has been applied to the local database used for this project.

4. Run `demo_accounts.sql` to add missing local demo accounts without replacing existing records. The accounts use `admin@example.com`, `faculty@example.com`, `examcell@example.com`, `demo.student@example.com`, and `flow.student@example.com`; the initial password for each is `password123`. A successful first sign-in upgrades each legacy demo hash. Use `demo.student@example.com` for a fresh Registered record; the separate `flow.student@example.com` record is reserved for a complete lifecycle demonstration. `seed_data.sql` is an older, incompatible seed draft and should not be run.

5. Start the development server:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5000` in a browser. Change demo credentials before sharing the application.

## Demonstration path

1. Sign in as `student@example.com`; inspect the current status and pay the examination fee.
2. Sign in as `examcell@example.com`; issue a hall ticket for the now-eligible student.
3. Sign in as `faculty@example.com`; mark attendance and submit an evaluation.
4. Sign back in as ExamCell and publish the evaluated result.
5. Sign in as `admin@example.com`; inspect the workflow counts and audit trail.
6. Open `/fsm`; compare the visualized DFA with `FSM_TRANSITIONS` in Oracle.

The demo database password hash is seeded for the first login only. Payment callback behavior is simulated and is not a real payment integration. Local demo accounts and sample data are not suitable for production use.

## Database objects

`MOC_PROJECT.sql` creates the base relational schema. `schema_patch.sql` adds columns required by the web forms, then creates `FSM_STATES` and `FSM_TRANSITIONS` and updates ExamCell permissions to match the event table in the report. The Python engine checks the current state/event against both the in-memory DFA and Oracle before persisting the next state. The `get_db` context manager commits or rolls back the associated work as one transaction.

## Known environment note

If SQL*Plus reports `ORA-12638: Credential retrieval failed`, check the local Oracle client authentication configuration and service before treating it as an application schema error. This error occurred during the initial read-only connectivity check in the development environment. Configure `ORACLE_PASSWORD` in the same shell used to run Flask; do not put credentials in source files.

The full web/database flow still needs verification against the target Oracle schema after dependencies are installed and the migration is reviewed. The report deliberately does not claim performance or correctness metrics that have not been measured.
