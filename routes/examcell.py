"""
routes/examcell.py — ExamCell Blueprint  (url_prefix='/examcell')
Routes require session role ∈ {'ExamCell', 'HOD'}.

FSM events triggered here:
    generate_hall_ticket  → HallTicketIssued   (also inserts HALL_TICKETS row)
    confirm_evaluation    → ResultPublished
    revert_evaluation     → Evaluated           (UnderReview → back to Evaluated)
    publish_result        → ResultPublished

Endpoints:
    GET  /dashboard                        — students needing action
    POST /student/<id>/hall_ticket         — generate hall ticket
    POST /student/<id>/confirm             — confirm evaluation
    POST /student/<id>/revert             — revert evaluation (UnderReview → Evaluated)
    POST /student/<id>/publish             — publish result
    GET  /reports                          — aggregate stats + chart data JSON
"""

import json
import random
import string
from functools import wraps

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify
)
from db import get_db
from fsm import fsm as exam_fsm

examcell_bp = Blueprint('examcell', __name__)


# ---------------------------------------------------------------------------
# Access guard
# ---------------------------------------------------------------------------

def examcell_required(f):
    """Allow ExamCell and HOD roles only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') not in ('ExamCell', 'HOD'):
            flash('Access denied: ExamCell/HOD only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_qr() -> str:
    """Generate a pseudo-random QR code string (placeholder)."""
    return 'QR-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


def _random_seat() -> str:
    """Generate a random seat number like A-17."""
    row  = random.choice(string.ascii_uppercase[:10])
    seat = random.randint(1, 30)
    return f'{row}-{seat}'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@examcell_bp.route('/dashboard')
@examcell_required
def dashboard():
    """
    List students that require Exam Cell action:
      - FeePaid        → need hall ticket generation
      - Evaluated      → awaiting confirmation / result publish
      - UnderReview    → needs resolution (confirm or revert)
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
                WHERE  s.exam_status IN ('FeePaid', 'Evaluated', 'UnderReview')
                ORDER  BY s.exam_status, u.name
                """
            )
            cols = [c[0].lower() for c in cursor.description]
            students = [dict(zip(cols, r)) for r in cursor.fetchall()]

        return render_template('examcell/dashboard.html', students=students)

    except Exception as exc:
        flash(f'Error loading dashboard: {exc}', 'danger')
        return redirect(url_for('index'))


# ---------------------------------------------------------------------------

@examcell_bp.route('/student/<int:student_id>/hall_ticket', methods=['POST'])
@examcell_required
def generate_hall_ticket(student_id: int):
    """
    Generate a hall ticket for a FeePaid student.
    FSM event: generate_hall_ticket  →  HallTicketIssued
    Also inserts a row into HALL_TICKETS.

    Form fields (optional overrides):
        exam_date    — e.g. 2026-11-15
        exam_center  — e.g. Main Hall, Block A
    """
    exam_date   = request.form.get('exam_date', '').strip()
    exam_center = request.form.get('exam_center', 'Main Examination Hall').strip()

    # Default exam date
    if not exam_date:
        exam_date = '2026-11-15'

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
                return redirect(url_for('examcell.dashboard'))

            # FSM transition
            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='generate_hall_ticket',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )

            # Insert HALL_TICKETS record
            cursor.execute(
                """
                INSERT INTO HALL_TICKETS
                    (student_id, issue_date, exam_date, exam_center,
                     seat_number, qr_code)
                VALUES
                    (:sid, SYSDATE,
                     TO_DATE(:edate, 'YYYY-MM-DD'),
                     :ecenter, :seat, :qr)
                """,
                {
                    'sid':     student_id,
                    'edate':   exam_date,
                    'ecenter': exam_center,
                    'seat':    _random_seat(),
                    'qr':      _random_qr(),
                }
            )
            conn.commit()
            flash(f'Hall ticket generated for student {student_id}.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot generate hall ticket: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('examcell.dashboard'))


# ---------------------------------------------------------------------------

@examcell_bp.route('/student/<int:student_id>/confirm', methods=['POST'])
@examcell_required
def confirm_evaluation(student_id: int):
    """
    Confirm a student's evaluation result.
    FSM event: confirm_evaluation  →  ResultPublished
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
                return redirect(url_for('examcell.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='confirm_evaluation',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Evaluation confirmed for student {student_id}. Result published.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot confirm evaluation: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('examcell.dashboard'))


# ---------------------------------------------------------------------------

@examcell_bp.route('/student/<int:student_id>/revert', methods=['POST'])
@examcell_required
def revert_evaluation(student_id: int):
    """
    Revert an UnderReview student back to Evaluated for re-assessment.
    FSM event: revert_evaluation  →  Evaluated
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
                return redirect(url_for('examcell.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='revert_evaluation',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Evaluation reverted for student {student_id}. Status: Evaluated.', 'info')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot revert evaluation: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('examcell.dashboard'))


# ---------------------------------------------------------------------------

@examcell_bp.route('/student/<int:student_id>/publish', methods=['POST'])
@examcell_required
def publish_result(student_id: int):
    """
    Publish the final result for a student.
    FSM event: publish_result  →  ResultPublished
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
                return redirect(url_for('examcell.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='publish_result',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Result published for student {student_id}.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot publish result: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('examcell.dashboard'))


# ---------------------------------------------------------------------------

@examcell_bp.route('/reports')
@examcell_required
def reports():
    """
    Aggregate statistics page.
    Returns counts per FSM state plus chart-ready JSON data
    for a simple bar chart.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Count per state
            cursor.execute(
                """
                SELECT exam_status, COUNT(*) AS cnt
                FROM   STUDENTS
                GROUP  BY exam_status
                ORDER  BY exam_status
                """
            )
            state_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Recent registrations by month (last 6 months)
            cursor.execute(
                """
                SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month,
                       COUNT(*) AS cnt
                FROM   FEE_PAYMENTS
                WHERE  payment_date >= ADD_MONTHS(SYSDATE, -6)
                GROUP  BY TO_CHAR(payment_date, 'YYYY-MM')
                ORDER  BY month
                """
            )
            monthly = [{'month': r[0], 'count': r[1]} for r in cursor.fetchall()]

        # Prepare chart data as JSON string for the template
        chart_data = json.dumps({
            'states': {
                'labels': list(state_counts.keys()),
                'data':   list(state_counts.values()),
            },
            'monthly': monthly,
        })

        return render_template(
            'examcell/reports.html',
            state_counts=state_counts,
            monthly=monthly,
            chart_data=chart_data,
        )

    except Exception as exc:
        flash(f'Error loading reports: {exc}', 'danger')
        return redirect(url_for('examcell.dashboard'))
