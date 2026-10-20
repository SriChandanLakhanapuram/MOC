# ExamFlow: Code Tour and Postman Walkthrough

This guide explains how the Flask application is put together and how to call its routes with a browser or Postman.

## How a request moves through the project

1. A browser or Postman sends an HTTP request, such as `POST /student/pay_fee`.
2. `app.py` applies shared request checks, then Flask matches the URL and HTTP method to a registered route.
3. A route function in `routes/` checks the user's session and role, reads submitted form fields, and calls the database layer.
4. `db.py` supplies an Oracle connection. Its `get_db()` context manager commits successful work and rolls back on exceptions.
5. For exam status changes, `fsm.py` checks the Python DFA, Oracle transition table, and Oracle role/event permission. It locks the specific exam enrollment, updates its state, and writes an audit record in the same transaction.
6. The route returns HTML or JSON, or redirects the browser to the next page.

## The main files

- `app.py` creates the Flask application, registers route groups, handles shared CSRF checks, and defines public routes such as `/`, `/fsm`, and `/api/fsm`.
- `routes/auth.py` checks credentials, creates the signed-in session, and handles logout.
- `routes/student.py`, `routes/faculty.py`, `routes/admin.py`, and `routes/examcell.py` contain role-specific page and action handlers.
- `routes/hod.py` scopes course catalog and teaching assignments to departments assigned to an HOD.
- `fsm.py` is the Theory of Computation part: states are the set `Q`, events are the alphabet `Σ`, the start state is `q0`, terminal states are `F`, and `DELTA[(state, event)]` is the transition function `δ`.
- `db.py` owns pooled Oracle connections and the transaction boundary.
- `templates/` contains the HTML rendered by routes. `templates/base.html` supplies the green role-specific sidebar and adds CSRF tokens to POST forms.
- `MOC_PROJECT.sql` defines the base tables. `schema_patch.sql` adds the Oracle FSM tables. `schema_exam_features.sql` adds the exam catalogue, faculty assignments, per-exam enrollment, refund workflow, and evaluation history. `demo_accounts.sql` seeds local demonstration accounts.

## What “route” means

A route connects an HTTP method and URL to a Python function. For example, in `routes/student.py`:

```python
@student_bp.route('/pay_fee', methods=['POST'])
@student_required
def pay_fee():
    ...
```

`app.py` registers that blueprint with the prefix `/student`, so the full address becomes `POST /student/pay_fee`. The decorator `@student_required` checks the session before the function runs. A URL part such as `<student_id>` is a value supplied in the address, for example `/faculty/student/S123/attendance`.

## Route map

| Area | Method and path | Purpose |
| --- | --- | --- |
| Sign-in | `GET /login`, `POST /login` | Show the form and authenticate a user |
| Sign-out | `POST /logout` | Clear the session |
| Student | `GET /student/dashboard` | View exam activity and quick counts |
| Student | `GET /student/exams`, `POST /student/exams/<exam_id>/enroll` | Browse course-eligible exams and register |
| Student | `GET /student/my-exams`, `POST /student/pay_fee` | Review registrations and pay per exam |
| Student | `POST /student/refunds/<enrollment_id>` | Ask the Examination Cell to review a refund |
| Student | `GET /student/refunds`, `GET /student/hall-tickets`, `GET /student/results` | Track refund requests, tickets, and published results |
| Faculty | `GET /faculty/dashboard`, `GET /faculty/exams` | View assigned exams and the action queue |
| Faculty | `POST /faculty/enrollment/<id>/attendance`, `/absent`, `/evaluate`, `/flag` | Record attendance and submit marks for assigned exams |
| Faculty | `GET /faculty/evaluations`, `POST /faculty/evaluations/<mark_id>/update` | Review marks and make reasoned, auditable corrections |
| Admin | `GET /admin/dashboard`, `GET /admin/audit`, `GET /admin/users`, `POST /admin/users/add` | Monitor exam enrollments, audit activity, and manage accounts |
| Exam Cell | `GET /examcell/exams`, `POST /examcell/exams/create` | Create exam offerings and assign one or more faculty members |
| Exam Cell | `GET /examcell/refunds`, `POST /examcell/refunds/<id>/review` | Review student-submitted refund requests and approve or decline |
| Exam Cell | `GET /examcell/hall-tickets`, `POST /examcell/enrollment/<id>/hall-ticket` | Issue and review hall tickets |
| Exam Cell | `GET /examcell/evaluations`, `POST /examcell/enrollment/<id>/<action>` | Confirm, return, or publish exam evaluations |
| Exam Cell | `GET /examcell/dashboard`, `GET /examcell/reports` | Monitor queues and exam-level workflow totals |
| HOD | `GET /hod/dashboard`, `GET /hod/courses` | See department totals and create or maintain department courses |
| HOD | `POST /hod/courses/create`, `POST /hod/courses/<code>/update` | Add a course or update its name and credits; code and department ownership stay fixed |
| HOD | `GET /hod/faculty`, `POST /hod/faculty/assign` | Assign a lead, co-instructor, or lab instructor by academic year and term |
| HOD | `POST /hod/faculty/assignments/<id>/end` | End an assignment while preserving it in the history |

Admin assigns departments to HOD accounts. HOD course actions are limited to those departments. HOD teaching assignments inform the faculty choices for new exams; Exam Cell separately controls visibility for each exam. Exam workflow actions remain checked against the Oracle `PERMISSIONS` table.

## Using Postman

Postman can exercise the application. Most routes are HTML form actions, not a JSON REST API, so send the fields as `x-www-form-urlencoded`.

1. Set the base URL to the Flask port, for example `http://127.0.0.1:5002` for the local preview or `http://127.0.0.1:5000` when started with `python app.py`.
2. Send `GET {{baseUrl}}/login`. Postman stores the session cookie for the local host. Copy the hidden `csrf_token` value from the returned HTML.
3. Send `POST {{baseUrl}}/login` with **Body → x-www-form-urlencoded** fields `email`, `password`, and `csrf_token`. Keep Postman's cookie jar enabled. The response is a redirect after successful sign-in.
4. For an Admin, send `GET {{baseUrl}}/admin/users` and copy the new CSRF token from its HTML. Then send `POST {{baseUrl}}/admin/users/add` with `name`, `email`, `password`, `role`, and `csrf_token`.
5. For each protected POST, keep the same session cookie and send the current CSRF token. Fetch the role's dashboard again if you need to retrieve its token. POSTs without a valid token receive HTTP 400.

To create a student, use `role=Student`; the server also creates a `STUDENTS` row and selects the first available course. Use `role=Faculty` to create a matching `FACULTY` row. Other accepted roles are `Admin`, `ExamCell`, and `HOD`.

Example form bodies:

```text
POST /admin/users/add
name=Sample Student
email=sample.student@example.test
password=TemporaryPass123!
role=Student
csrf_token=<token copied from the page>
```

```text
POST /faculty/enrollment/<enrollment_id>/evaluate
subject_name=Database Systems
marks_obtained=84
max_marks=100
grade=A
csrf_token=<token copied from the faculty page>
```

The JSON route `GET /api/fsm` does not require sign-in and is a good first Postman request. It returns the states, events, start state, terminal states, and transitions.

## Running and understanding the DFA

The state for each exam registration is stored on `EXAM_ENROLLMENTS.EXAM_STATUS`. The older `STUDENTS.EXAM_STATUS` column is retained for compatibility with the original schema. `fsm.py` defines the allowed transition relation in Python. Oracle stores the same edges in `FSM_TRANSITIONS`; `ExamFSM.transition()` refuses a transition if the two copies disagree or the role lacks permission. This makes it possible to compare the Theory of Computation model with the database state during a demonstration.

For example, when `POST /student/pay_fee` runs, the Student route fetches that student's exam registration, asks `ExamFSM.transition()` to apply `pay_fee`, inserts a payment row, and commits the new state and audit row together. The student dashboard then shows `FeePaid` and the next allowed action.

The payment callback and fee payment pages are classroom simulations. They do not connect to a real payment provider.
