"""
routes/faculty.py — Faculty Blueprint  (url_prefix='/faculty')
All routes require session role == 'Faculty'.

FSM events triggered here:
    mark_attendance    → ExamTaken          (student attended the exam)
    mark_absent        → Absent             (student did not appear)
    submit_evaluation  → Evaluated          (marks entered)
    flag_discrepancy   → UnderReview        (evaluation dispute flagged)

DB tables accessed:
    STUDENTS — read/update exam_status
    MARKS    — insert marks on evaluation
"""

from functools import wraps

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash
)
from db import get_db
from fsm import fsm as exam_fsm

faculty_bp = Blueprint('faculty', __name__)


# ---------------------------------------------------------------------------
# Access guard
# ---------------------------------------------------------------------------

def faculty_required(f):
    """Ensure only Faculty role can access the decorated view."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Faculty':
            flash('Access denied: Faculty only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@faculty_bp.route('/dashboard')
@faculty_required
def dashboard():
    """
    List students whose exam_status is 'HallTicketIssued' or 'ExamTaken'.
    These are students the faculty needs to take action on (attendance / evaluation).
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT s.student_id, u.name, u.email,
                       s.course_code, s.exam_status
                FROM   STUDENTS s
                JOIN   USERS    u ON u.user_id = s.user_id
                WHERE  s.exam_status IN ('HallTicketIssued', 'ExamTaken', 'Evaluated')
                ORDER  BY s.exam_status, u.name
                """
            )
            cols = [c[0].lower() for c in cursor.description]
            students = [dict(zip(cols, r)) for r in cursor.fetchall()]

        return render_template('faculty/dashboard.html', students=students)

    except Exception as exc:
        flash(f'Error loading dashboard: {exc}', 'danger')
        return redirect(url_for('index'))


# ---------------------------------------------------------------------------

@faculty_bp.route('/student/<student_id>/attendance', methods=['POST'])
@faculty_required
def mark_attendance(student_id: int):
    """
    Mark the student as having attended the exam.
    FSM event: mark_attendance  →  ExamTaken
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT exam_status FROM STUDENTS WHERE student_id = :sid",
                {'sid': student_id}
            )
            row = cursor.fetchone()
            if not row:
                flash(f'Student {student_id} not found.', 'danger')
                return redirect(url_for('faculty.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='mark_attendance',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Attendance marked for student {student_id}.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot mark attendance: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('faculty.dashboard'))


# ---------------------------------------------------------------------------

@faculty_bp.route('/student/<student_id>/absent', methods=['POST'])
@faculty_required
def mark_absent(student_id: int):
    """
    Mark the student as absent.
    FSM event: mark_absent  →  Absent
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT exam_status FROM STUDENTS WHERE student_id = :sid",
                {'sid': student_id}
            )
            row = cursor.fetchone()
            if not row:
                flash(f'Student {student_id} not found.', 'danger')
                return redirect(url_for('faculty.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='mark_absent',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Student {student_id} marked as absent.', 'info')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot mark absent: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('faculty.dashboard'))


# ---------------------------------------------------------------------------

@faculty_bp.route('/student/<student_id>/evaluate', methods=['POST'])
@faculty_required
def evaluate(student_id: int):
    """
    Submit evaluation / marks for a student.
    FSM event: submit_evaluation  →  Evaluated
    Also inserts/updates a record in the MARKS table.

    Form fields expected:
        subject_code    — e.g. CS301
        subject_name    — e.g. Database Systems
        marks_obtained  — numeric
        max_marks       — numeric (default 100)
        grade           — e.g. A, B, C, F
    """
    subject_code   = request.form.get('subject_code', '').strip()
    subject_name   = request.form.get('subject_name', '').strip()
    marks_obtained = request.form.get('marks_obtained', '0').strip()
    max_marks      = request.form.get('max_marks', '100').strip()
    grade          = request.form.get('grade', '').strip().upper()

    if not subject_code:
        flash('Subject code is required to submit evaluation.', 'warning')
        return redirect(url_for('faculty.dashboard'))

    try:
        marks_obtained = float(marks_obtained)
        max_marks      = float(max_marks)
    except ValueError:
        flash('Marks must be numeric values.', 'warning')
        return redirect(url_for('faculty.dashboard'))

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT exam_status FROM STUDENTS WHERE student_id = :sid",
                {'sid': student_id}
            )
            row = cursor.fetchone()
            if not row:
                flash(f'Student {student_id} not found.', 'danger')
                return redirect(url_for('faculty.dashboard'))

            # FSM transition
            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='submit_evaluation',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )

            # Insert marks record
            cursor.execute("SELECT faculty_id FROM FACULTY WHERE user_id = :user_id_param", {'user_id_param': session['user_id']})
            faculty_row = cursor.fetchone()
            if not faculty_row:
                raise ValueError('Your account is not linked to a faculty record.')
            cursor.execute(
                """
                INSERT INTO MARKS
                    (student_id, subject_code, subject_name,
                     course_code, marks_obtained, max_marks, grade,
                     entered_by, evaluated_by, evaluation_date)
                VALUES
                    (:sid, :sc, :sn, :sc, :mo, :mm, :gr, :faculty_id, :ev, SYSDATE)
                """,
                {
                    'sid': student_id,
                    'sc':  subject_code,
                    'sn':  subject_name,
                    'mo':  marks_obtained,
                    'mm':  max_marks,
                    'gr':  grade,
                    'faculty_id': faculty_row[0],
                    'ev':  session['user_id'],
                }
            )
            conn.commit()
            flash(f'Evaluation submitted for student {student_id} — {subject_code}.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot submit evaluation: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('faculty.dashboard'))


# ---------------------------------------------------------------------------

@faculty_bp.route('/student/<student_id>/flag', methods=['POST'])
@faculty_required
def flag_discrepancy(student_id: int):
    """
    Flag an evaluation discrepancy for further review.
    FSM event: flag_discrepancy  →  UnderReview
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT exam_status FROM STUDENTS WHERE student_id = :sid",
                {'sid': student_id}
            )
            row = cursor.fetchone()
            if not row:
                flash(f'Student {student_id} not found.', 'danger')
                return redirect(url_for('faculty.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='flag_discrepancy',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Discrepancy flagged for student {student_id}. Status: UnderReview.', 'warning')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot flag discrepancy: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('faculty.dashboard'))
