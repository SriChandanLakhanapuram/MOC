"""Student exam catalogue, enrollment, payments, refund requests and results."""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_db
from fsm import fsm as exam_fsm

student_bp = Blueprint('student', __name__)


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Student':
            flash('This area is for students.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def _rows(cursor):
    keys = [col[0].lower() for col in cursor.description]
    return [dict(zip(keys, row)) for row in cursor.fetchall()]


def _student_id():
    return session.get('student_id')


@student_bp.route('/dashboard')
@student_required
def dashboard():
    sid = _student_id()
    if not sid:
        flash('Your account is not linked to a student record. Contact the administrator.', 'warning')
        return redirect(url_for('auth.logout'))
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT COUNT(*), SUM(CASE WHEN exam_status='ResultPublished' THEN 1 ELSE 0 END),
                              SUM(CASE WHEN exam_status='FeePaid' THEN 1 ELSE 0 END)
                       FROM exam_enrollments WHERE student_id=:sid""", sid=sid)
        counts = cur.fetchone()
        cur.execute("""SELECT e.exam_name, e.exam_code, e.exam_date, e.course_code,
                            x.exam_status, x.enrollment_id
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     WHERE x.student_id=:sid ORDER BY e.exam_date DESC
                     FETCH FIRST 5 ROWS ONLY""", sid=sid)
        recent = _rows(cur)
    return render_template('student/dashboard.html', counts=counts, recent=recent)


@student_bp.route('/exams')
@student_required
def exams():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT e.exam_id, e.exam_code, e.exam_name, e.course_code,
                            c.course_name, e.exam_date, e.fee
                     FROM exams e JOIN courses c ON c.course_code=e.course_code
                     JOIN students s ON s.course_code=e.course_code
                     WHERE s.student_id=:sid AND e.status='Open' AND e.exam_date>=TRUNC(SYSDATE)
                       AND NOT EXISTS (SELECT 1 FROM exam_enrollments x
                                       WHERE x.exam_id=e.exam_id AND x.student_id=:sid)
                     ORDER BY e.exam_date""", sid=_student_id())
        exams = _rows(cur)
    return render_template('student/exams.html', exams=exams)


@student_bp.route('/exams/<int:exam_id>/enroll', methods=['POST'])
@student_required
def enroll(exam_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT e.course_code, e.status, s.course_code
                     FROM exams e JOIN students s ON s.student_id=:sid
                     WHERE e.exam_id=:eid""", sid=_student_id(), eid=exam_id)
        row = cur.fetchone()
        if not row or row[1] != 'Open' or row[0] != row[2]:
            flash('This exam is unavailable for your course.', 'warning')
            return redirect(url_for('student.exams'))
        cur.execute("""INSERT INTO exam_enrollments (student_id, exam_id, exam_status)
                       VALUES (:sid, :eid, 'Registered')""", sid=_student_id(), eid=exam_id)
        conn.commit()
    flash('Exam added to your registrations. You can pay from My exams.', 'success')
    return redirect(url_for('student.my_exams'))


@student_bp.route('/my-exams')
@student_required
def my_exams():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT x.enrollment_id, x.exam_status, e.exam_id, e.exam_code,
                            e.exam_name, e.course_code, c.course_name, e.exam_date, e.fee,
                            (SELECT COUNT(*) FROM refund_requests r
                             WHERE r.enrollment_id=x.enrollment_id AND r.status='Pending') AS refund_pending
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     JOIN courses c ON c.course_code=e.course_code
                     WHERE x.student_id=:sid ORDER BY e.exam_date DESC""", sid=_student_id())
        exams = _rows(cur)
    return render_template('student/my_exams.html', exams=exams)


@student_bp.route('/pay_fee', methods=['POST'])
@student_required
def pay_fee():
    enrollment_id = request.form.get('enrollment_id', type=int)
    sid = _student_id()
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT x.exam_status, e.fee, x.exam_id
                         FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                         WHERE x.enrollment_id=:eid AND x.student_id=:sid FOR UPDATE""",
                        eid=enrollment_id, sid=sid)
            row = cur.fetchone()
            if not row:
                raise ValueError('Registration not found.')
            exam_fsm.transition(sid, 'pay_fee', 'Student', session['user_id'], conn=conn,
                                enrollment_id=enrollment_id)
            cur.execute("""INSERT INTO fee_payments
                         (student_id, enrollment_id, amount, payment_date, status, transaction_id)
                         VALUES (:sid,:eid,:amount,SYSDATE,'Success',:txn)""",
                        sid=sid, eid=enrollment_id, amount=row[1], txn=f'EF-{enrollment_id}-{session["user_id"]}')
            conn.commit()
        flash('Payment recorded. Your seat is now eligible for a hall ticket.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Payment could not be completed. Please retry or contact the examination cell.', 'danger')
    return redirect(url_for('student.my_exams'))


@student_bp.route('/cancel', methods=['POST'])
@student_required
def cancel():
    enrollment_id = request.form.get('enrollment_id', type=int)
    sid = _student_id()
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM exam_enrollments WHERE enrollment_id=:eid AND student_id=:sid",
                        eid=enrollment_id, sid=sid)
            if not cur.fetchone():
                raise ValueError('Registration not found.')
            exam_fsm.transition(sid, 'cancel_registration', 'Student', session['user_id'],
                                conn=conn, enrollment_id=enrollment_id)
            conn.commit()
        flash('Registration cancelled.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Registration could not be cancelled.', 'danger')
    return redirect(url_for('student.my_exams'))


@student_bp.route('/refunds')
@student_required
def refunds():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT r.refund_id, r.reason, r.status, r.requested_at, r.review_note,
                            e.exam_code, e.exam_name, e.fee, x.exam_status
                     FROM refund_requests r JOIN exam_enrollments x ON x.enrollment_id=r.enrollment_id
                     JOIN exams e ON e.exam_id=x.exam_id WHERE x.student_id=:sid
                     ORDER BY r.requested_at DESC""", sid=_student_id())
        requests = _rows(cur)
    return render_template('student/refunds.html', requests=requests)


@student_bp.route('/refunds/<int:enrollment_id>', methods=['POST'])
@student_required
def request_refund(enrollment_id):
    sid = _student_id()
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Add a short reason so the Exam Cell can review your request.', 'warning')
        return redirect(url_for('student.my_exams'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT exam_status FROM exam_enrollments
                         WHERE enrollment_id=:eid AND student_id=:sid FOR UPDATE""",
                        eid=enrollment_id, sid=sid)
            row = cur.fetchone()
            if not row or row[0] != 'FeePaid':
                raise ValueError('Refunds can be requested only for paid exams that have not started.')
            cur.execute("SELECT 1 FROM fee_payments WHERE enrollment_id=:eid AND status='Success'",
                        eid=enrollment_id)
            if not cur.fetchone():
                raise ValueError('No successful payment was found for this exam.')
            cur.execute("SELECT 1 FROM refund_requests WHERE enrollment_id=:eid AND status='Pending'",
                        eid=enrollment_id)
            if cur.fetchone():
                raise ValueError('A refund request is already waiting for review.')
            cur.execute("""INSERT INTO refund_requests (enrollment_id,requested_by,reason)
                         VALUES (:eid,:actor_id,:reason)""",
                        eid=enrollment_id, actor_id=session['user_id'], reason=reason[:500])
            cur.execute("""INSERT INTO audit_log
                         (user_id,student_id,enrollment_id,event,old_state,new_state)
                         VALUES (:actor_id,:sid,:eid,'refund_requested','FeePaid','FeePaid')""",
                        actor_id=session['user_id'], sid=sid, eid=enrollment_id)
            conn.commit()
        flash('Refund request sent to the Examination Cell for review.', 'success')
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Refund request could not be saved. Please try again.', 'danger')
    return redirect(url_for('student.refunds'))


@student_bp.route('/hall-tickets')
@student_required
def hall_tickets():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT h.ticket_id,h.exam_date,h.exam_center,h.seat_number,h.qr_code,
                            e.exam_code,e.exam_name,e.course_code,u.name,s.student_id
                     FROM hall_tickets h JOIN exam_enrollments x ON x.enrollment_id=h.enrollment_id
                     JOIN exams e ON e.exam_id=x.exam_id JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id
                     WHERE x.student_id=:sid ORDER BY h.exam_date DESC""", sid=_student_id())
        tickets = _rows(cur)
    return render_template('student/hall_tickets.html', tickets=tickets)


@student_bp.route('/results')
@student_required
def results():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT x.enrollment_id,e.exam_code,e.exam_name,e.course_code,e.exam_date,
                            m.mark_id,m.subject_code,m.subject_name,m.marks_obtained,m.max_marks,m.grade
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     LEFT JOIN marks m ON m.enrollment_id=x.enrollment_id
                     WHERE x.student_id=:sid AND x.exam_status='ResultPublished'
                     ORDER BY e.exam_date DESC,m.subject_code""", sid=_student_id())
        rows = _rows(cur)
    results = {}
    for row in rows:
        result = results.setdefault(row['enrollment_id'], {
            'exam_code': row['exam_code'], 'exam_name': row['exam_name'],
            'course_code': row['course_code'], 'exam_date': row['exam_date'], 'marks': []})
        if row['mark_id'] is not None:
            result['marks'].append(row)
    return render_template('student/results.html', results=list(results.values()))
