"""
routes/student.py — Student Blueprint  (url_prefix='/student')
All routes are protected: session role must be 'Student'.

FSM events triggered here:
    pay_fee              → FeePaid
    payment_failed       → Registered   (stays; payment gateway rejection)
    cancel_registration  → Cancelled

DB tables accessed:
    STUDENTS      — read exam_status, course_code
    FEE_PAYMENTS  — read payment history
    HALL_TICKETS  — read hall ticket details
    MARKS         — read result/marks (state == ResultPublished)
"""

import random
from functools import wraps

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify
)
from db import get_db
from fsm import fsm as exam_fsm

student_bp = Blueprint('student', __name__)


# ---------------------------------------------------------------------------
# Access guard decorator
# ---------------------------------------------------------------------------

def student_required(f):
    """Redirect non-Student sessions to login / 403."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Student':
            flash('Access denied: Students only.', 'danger')
            return redirect(url_for('index')), 403
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Helper: fetch current student record
# ---------------------------------------------------------------------------

def _get_student(conn, student_id: int) -> dict | None:
    """Return a dict with student details or None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.student_id, s.user_id, s.course_code, s.exam_status,
               u.name, u.email
        FROM   STUDENTS s
        JOIN   USERS    u ON u.user_id = s.user_id
        WHERE  s.student_id = :sid
        """,
        {'sid': student_id}
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        'student_id':  row[0],
        'user_id':     row[1],
        'course_code': row[2],
        'exam_status': row[3],
        'name':        row[4],
        'email':       row[5],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@student_bp.route('/dashboard')
@student_required
def dashboard():
    """
    Show the student's current FSM state, available next events,
    payment history, and hall ticket (if issued).
    """
    student_id = session.get('student_id')
    if not student_id:
        flash('No student record found for your account.', 'danger')
        return redirect(url_for('auth.logout'))

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # --- Student record -------------------------------------------
            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('auth.logout'))

            current_state = student['exam_status']

            # --- FSM: available next events for this state ----------------
            next_events = exam_fsm.available_events(current_state, role='Student')

            # --- Payment history ------------------------------------------
            cursor.execute(
                """
                SELECT payment_id, amount, payment_date, status, transaction_id
                FROM   FEE_PAYMENTS
                WHERE  student_id = :sid
                ORDER  BY payment_date DESC
                """,
                {'sid': student_id}
            )
            cols = [c[0].lower() for c in cursor.description]
            payments = [dict(zip(cols, r)) for r in cursor.fetchall()]

            # --- Hall ticket (if applicable) ------------------------------
            hall_ticket = None
            hall_ticket_states = {
                'HallTicketIssued', 'ExamTaken', 'Evaluated',
                'UnderReview', 'ResultPublished'
            }
            if current_state in hall_ticket_states:
                cursor.execute(
                    """
                    SELECT ticket_id, issue_date, exam_date, exam_center,
                           seat_number, qr_code
                    FROM   HALL_TICKETS
                    WHERE  student_id = :sid
                    ORDER  BY issue_date DESC
                    FETCH  FIRST 1 ROWS ONLY
                    """,
                    {'sid': student_id}
                )
                ht_row = cursor.fetchone()
                if ht_row:
                    ht_cols = [c[0].lower() for c in cursor.description]
                    hall_ticket = dict(zip(ht_cols, ht_row))

        student.update(state=current_state, course=student['course_code'])
        return render_template(
            'student/dashboard.html',
            student=student,
            current_state=current_state,
            next_events=next_events,
            available_events=next_events,
            payments=payments,
            hall_ticket=hall_ticket,
        )

    except Exception as exc:
        flash(f'Error loading dashboard: {exc}', 'danger')
        return redirect(url_for('index'))


# ---------------------------------------------------------------------------

@student_bp.route('/pay_fee', methods=['POST'])
@student_required
def pay_fee():
    """
    Initiate fee payment.
    Triggers the 'pay_fee' FSM event and inserts a FEE_PAYMENTS record.
    Uses PRG pattern — always redirects after POST.
    """
    student_id = session.get('student_id')
    amount     = request.form.get('amount', '1000.00')

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('student.dashboard'))

            # FSM transition
            exam_fsm.transition(
                student_id=student_id,
                current_state=student['exam_status'],
                event='pay_fee',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )

            # Record payment
            cursor.execute(
                """
                INSERT INTO FEE_PAYMENTS
                    (student_id, amount, payment_date, status, transaction_id)
                VALUES
                    (:sid, :amt, SYSDATE, 'Success', :txn)
                """,
                {
                    'sid': student_id,
                    'amt': float(amount),
                    'txn': f'TXN-{student_id}-{random.randint(100000, 999999)}',
                }
            )
            conn.commit()
            flash('Fee payment successful! Your status is now FeePaid.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot process payment: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('student.dashboard'))


# ---------------------------------------------------------------------------

@student_bp.route('/payment_callback', methods=['POST'])
@student_required
def payment_callback():
    """
    Simulate a payment gateway callback for classroom demonstration only.
    80 % chance of success → triggers 'pay_fee'.
    20 % chance of failure → triggers 'payment_failed'.
    The system acts as role=SYSTEM / user_id=0.
    """
    student_id = session.get('student_id')

    try:
        with get_db() as conn:
            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('student.dashboard'))

            success = random.random() < 0.80  # 80 % success rate
            event   = 'pay_fee' if success else 'payment_failed'

            exam_fsm.transition(
                student_id=student_id,
                current_state=student['exam_status'],
                event=event,
                role='Student' if success else 'SYSTEM',
                user_id=session['user_id'] if success else None,
                conn=conn,
            )

            if success:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO FEE_PAYMENTS
                        (student_id, amount, payment_date, status, transaction_id)
                    VALUES
                        (:sid, 1000.00, SYSDATE, 'Success', :txn)
                    """,
                    {
                        'sid': student_id,
                        'txn': f'GW-{student_id}-{random.randint(100000, 999999)}',
                    }
                )
                conn.commit()
                flash('Payment gateway: Transaction approved. Status updated to FeePaid.', 'success')
            else:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO FEE_PAYMENTS (student_id, amount, payment_date, status) VALUES (:sid, 1000, SYSDATE, 'Failed')",
                    {'sid': student_id},
                )
                flash('Payment gateway: Transaction declined. Please try again.', 'warning')

    except (ValueError, PermissionError) as exc:
        flash(f'Payment callback error: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('student.dashboard'))


# ---------------------------------------------------------------------------

@student_bp.route('/cancel', methods=['POST'])
@student_required
def cancel():
    """Cancel the student's exam registration (FSM event: cancel_registration)."""
    student_id = session.get('student_id')

    try:
        with get_db() as conn:
            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('student.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=student['exam_status'],
                event='cancel_registration',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash('Your registration has been cancelled.', 'info')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot cancel registration: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('student.dashboard'))


# ---------------------------------------------------------------------------

@student_bp.route('/hall_ticket')
@student_required
def hall_ticket():
    """
    Display the hall ticket.
    Only accessible when exam_status ∈ {HallTicketIssued, ExamTaken,
    Evaluated, UnderReview, ResultPublished}.
    """
    student_id = session.get('student_id')
    viewable_states = {
        'HallTicketIssued', 'ExamTaken', 'Evaluated',
        'UnderReview', 'ResultPublished'
    }

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('student.dashboard'))

            if student['exam_status'] not in viewable_states:
                flash('Hall ticket is not yet available for your current status.', 'warning')
                return redirect(url_for('student.dashboard'))

            cursor.execute(
                """
                SELECT ticket_id, issue_date, exam_date, exam_center,
                       seat_number, qr_code
                FROM   HALL_TICKETS
                WHERE  student_id = :sid
                ORDER  BY issue_date DESC
                FETCH  FIRST 1 ROWS ONLY
                """,
                {'sid': student_id}
            )
            row = cursor.fetchone()
            if not row:
                flash('Hall ticket record not found. Contact the Exam Cell.', 'warning')
                return redirect(url_for('student.dashboard'))

            cols = [c[0].lower() for c in cursor.description]
            ticket = dict(zip(cols, row))

        return render_template('student/hall_ticket.html', student=student, ticket=ticket)

    except Exception as exc:
        flash(f'Error fetching hall ticket: {exc}', 'danger')
        return redirect(url_for('student.dashboard'))


# ---------------------------------------------------------------------------

@student_bp.route('/result')
@student_required
def result():
    """
    Display exam marks/results.
    Only accessible when exam_status == 'ResultPublished'.
    """
    student_id = session.get('student_id')

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            student = _get_student(conn, student_id)
            if not student:
                flash('Student record not found.', 'danger')
                return redirect(url_for('student.dashboard'))

            if student['exam_status'] != 'ResultPublished':
                flash('Results have not been published yet.', 'warning')
                return redirect(url_for('student.dashboard'))

            cursor.execute(
                """
                SELECT mark_id, subject_code, subject_name,
                       marks_obtained, max_marks, grade, evaluated_by, evaluation_date
                FROM   MARKS
                WHERE  student_id = :sid
                ORDER  BY subject_code
                """,
                {'sid': student_id}
            )
            cols = [c[0].lower() for c in cursor.description]
            marks = [dict(zip(cols, r)) for r in cursor.fetchall()]

            # Compute aggregate
            total_obtained = sum(m['marks_obtained'] for m in marks if m['marks_obtained'])
            total_max      = sum(m['max_marks']      for m in marks if m['max_marks'])
            percentage = round((total_obtained / total_max) * 100, 2) if total_max else 0

        return render_template(
            'student/result.html',
            student=student,
            marks=marks,
            total_obtained=total_obtained,
            total_max=total_max,
            percentage=percentage,
        )

    except Exception as exc:
        flash(f'Error fetching result: {exc}', 'danger')
        return redirect(url_for('student.dashboard'))
