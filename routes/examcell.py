"""Exam Cell exam catalogue, assignments, refunds and result release."""
import json
import random
import string
from datetime import date
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_db
from fsm import fsm as exam_fsm

examcell_bp = Blueprint('examcell', __name__)


def examcell_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'ExamCell':
            flash('This area is for the Examination Cell.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def examcell_editor(view):
    @wraps(view)
    @examcell_required
    def wrapped(*args, **kwargs):
        if session.get('role') != 'ExamCell':
            flash('HOD accounts have read-only access.', 'warning')
            return redirect(url_for('examcell.dashboard'))
        return view(*args, **kwargs)
    return wrapped


def _rows(cur):
    cols = [c[0].lower() for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _transition(conn, enrollment_id, event):
    cur = conn.cursor()
    cur.execute("SELECT student_id FROM exam_enrollments WHERE enrollment_id=:eid",
                eid=enrollment_id)
    row = cur.fetchone()
    if not row:
        raise ValueError('Exam registration not found.')
    return exam_fsm.transition(row[0], event, 'ExamCell', session['user_id'],
                               conn=conn, enrollment_id=enrollment_id)


@examcell_bp.route('/dashboard')
@examcell_required
def dashboard():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM exams WHERE status='Open'""")
        open_exams = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM refund_requests WHERE status='Pending'")
        pending_refunds = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM exam_enrollments WHERE exam_status IN ('FeePaid','Evaluated','UnderReview')")
        review_queue = cur.fetchone()[0]
        cur.execute("""SELECT x.enrollment_id,e.exam_name,e.exam_code,e.exam_date,
                            x.exam_status,s.student_id,u.name
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id
                     WHERE x.exam_status IN ('FeePaid','Evaluated','UnderReview')
                     ORDER BY e.exam_date,u.name FETCH FIRST 8 ROWS ONLY""")
        queue = _rows(cur)
    return render_template('examcell/dashboard.html', open_exams=open_exams,
                           pending_refunds=pending_refunds, review_queue=review_queue, queue=queue)


@examcell_bp.route('/exams')
@examcell_required
def exams():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT e.exam_id,e.exam_code,e.exam_name,e.course_code,c.course_name,
                            e.exam_date,e.fee,e.status,u.name AS creator,
                            (SELECT COUNT(*) FROM exam_enrollments x WHERE x.exam_id=e.exam_id) AS candidates
                     FROM exams e JOIN courses c ON c.course_code=e.course_code
                     JOIN users u ON u.user_id=e.created_by ORDER BY e.exam_date DESC""")
        exams = _rows(cur)
        cur.execute("SELECT course_code,course_name,department FROM courses ORDER BY course_name")
        courses = _rows(cur)
        cur.execute("""SELECT f.faculty_id,u.name,f.department,u.email,
                            (SELECT LISTAGG(a.course_code, ',') WITHIN GROUP (ORDER BY a.course_code)
                             FROM course_faculty a WHERE a.faculty_id=f.faculty_id AND a.active='Y') AS course_codes
                     FROM faculty f JOIN users u ON u.user_id=f.user_id
                     ORDER BY f.department,u.name""")
        faculty = _rows(cur)
    return render_template('examcell/exams.html', exams=exams, courses=courses,
                           faculty=faculty, today=date.today().isoformat(),
                           can_edit=session.get('role') == 'ExamCell')


@examcell_bp.route('/exams/create', methods=['POST'])
@examcell_editor
def create_exam():
    code = request.form.get('exam_code', '').strip().upper()
    name = request.form.get('exam_name', '').strip()
    course_code = request.form.get('course_code', '').strip().upper()
    exam_date = request.form.get('exam_date', '').strip()
    # Faculty IDs are VARCHAR2 values (for example, FAC001), not numeric user IDs.
    faculty_ids = list(dict.fromkeys(value.strip() for value in request.form.getlist('faculty_ids') if value.strip()))
    try:
        fee = float(request.form.get('fee', ''))
        parsed_date = date.fromisoformat(exam_date)
        if not code or not name or not course_code or not faculty_ids or fee < 0 or parsed_date < date.today():
            raise ValueError
    except (TypeError, ValueError):
        flash('Enter an exam code, name, course, future date, fee, and at least one assigned faculty member.', 'warning')
        return redirect(url_for('examcell.exams'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM courses WHERE course_code=:code", code=course_code)
            if not cur.fetchone():
                raise ValueError('Choose a valid course.')
            if faculty_ids:
                binds = ','.join(f':fid{i}' for i in range(len(faculty_ids)))
                params = {f'fid{i}': fid for i, fid in enumerate(faculty_ids)}
                params['course_code'] = course_code
                cur.execute(f"""SELECT faculty_id FROM course_faculty
                             WHERE course_code=:course_code AND active='Y' AND faculty_id IN ({binds})""", params)
                valid_faculty = {r[0] for r in cur.fetchall()}
                if valid_faculty != set(faculty_ids):
                    raise ValueError('Assign selected faculty to this course in the HOD workspace before assigning them to its exam.')
            cur.execute("""INSERT INTO exams
                         (exam_code,exam_name,course_code,exam_date,fee,status,created_by)
                         VALUES (:code,:name,:course,TO_DATE(:exam_date,'YYYY-MM-DD'),:fee,'Open',:actor_id)""",
                        code=code, name=name, course=course_code, exam_date=exam_date,
                        fee=fee, actor_id=session['user_id'])
            cur.execute("SELECT exam_id FROM exams WHERE exam_code=:code", code=code)
            exam_id = cur.fetchone()[0]
            for faculty_id in faculty_ids:
                cur.execute("""INSERT INTO exam_faculty (exam_id,faculty_id,assigned_by)
                             VALUES (:eid,:fid,:actor_id)""",
                            eid=exam_id, fid=faculty_id, actor_id=session['user_id'])
            conn.commit()
        flash(f'{code} is open for eligible students to enroll.', 'success')
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Exam could not be created. Check that its code is unique and try again.', 'danger')
    return redirect(url_for('examcell.exams'))


@examcell_bp.route('/exams/<int:exam_id>/status', methods=['POST'])
@examcell_editor
def update_exam_status(exam_id):
    status = request.form.get('status', '')
    if status not in ('Open', 'Closed'):
        flash('Unsupported exam status.', 'warning')
        return redirect(url_for('examcell.exams'))
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE exams SET status=:status WHERE exam_id=:eid", status=status, eid=exam_id)
        conn.commit()
    flash('Exam enrollment is now ' + status.lower() + '.', 'success')
    return redirect(url_for('examcell.exams'))


@examcell_bp.route('/refunds')
@examcell_required
def refunds():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT r.refund_id,r.enrollment_id,r.reason,r.status,r.requested_at,
                            r.review_note,e.exam_code,e.exam_name,e.fee,s.student_id,u.name AS student_name,
                            x.exam_status
                     FROM refund_requests r JOIN exam_enrollments x ON x.enrollment_id=r.enrollment_id
                     JOIN exams e ON e.exam_id=x.exam_id JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id ORDER BY
                     CASE r.status WHEN 'Pending' THEN 0 ELSE 1 END,r.requested_at DESC""")
        requests = _rows(cur)
    return render_template('examcell/refunds.html', requests=requests,
                           can_review=session.get('role') == 'ExamCell')


@examcell_bp.route('/refunds/<int:refund_id>/review', methods=['POST'])
@examcell_editor
def review_refund(refund_id):
    decision = request.form.get('decision')
    note = request.form.get('review_note', '').strip()
    if decision not in ('Approved', 'Rejected'):
        flash('Choose approve or reject.', 'warning')
        return redirect(url_for('examcell.refunds'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT enrollment_id,status FROM refund_requests
                         WHERE refund_id=:rid FOR UPDATE""", rid=refund_id)
            row = cur.fetchone()
            if not row or row[1] != 'Pending':
                raise ValueError('This request has already been reviewed.')
            if decision == 'Approved':
                _transition(conn, row[0], 'request_refund')
                cur.execute("UPDATE fee_payments SET status='Refunded' WHERE enrollment_id=:eid AND status='Success'",
                            eid=row[0])
            cur.execute("""UPDATE refund_requests SET status=:status,reviewed_by=:actor_id,
                         reviewed_at=SYSTIMESTAMP,review_note=:note WHERE refund_id=:rid""",
                        status=decision, actor_id=session['user_id'], note=note[:500] or None, rid=refund_id)
            conn.commit()
        flash('Refund request ' + decision.lower() + '.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('The refund decision could not be saved.', 'danger')
    return redirect(url_for('examcell.refunds'))


@examcell_bp.route('/hall-tickets')
@examcell_required
def hall_tickets():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT x.enrollment_id,x.exam_status,e.exam_code,e.exam_name,e.exam_date,
                            e.course_code,s.student_id,u.name AS student_name
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     JOIN students s ON s.student_id=x.student_id JOIN users u ON u.user_id=s.user_id
                     WHERE x.exam_status='FeePaid' ORDER BY e.exam_date,u.name""")
        queue = _rows(cur)
        cur.execute("""SELECT h.ticket_id,h.seat_number,h.exam_center,h.exam_date,e.exam_code,
                            e.exam_name,s.student_id,u.name AS student_name
                     FROM hall_tickets h JOIN exam_enrollments x ON x.enrollment_id=h.enrollment_id
                     JOIN exams e ON e.exam_id=x.exam_id JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id ORDER BY h.exam_date DESC""")
        issued = _rows(cur)
    return render_template('examcell/hall_tickets.html', queue=queue, issued=issued,
                           can_issue=session.get('role') == 'ExamCell')


@examcell_bp.route('/enrollment/<int:enrollment_id>/hall-ticket', methods=['POST'])
@examcell_editor
def issue_hall_ticket(enrollment_id):
    center = request.form.get('exam_center', '').strip() or 'Main Examination Hall'
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT x.student_id,x.exam_status,e.exam_date
                         FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                         WHERE x.enrollment_id=:eid FOR UPDATE""", eid=enrollment_id)
            row = cur.fetchone()
            if not row:
                raise ValueError('Exam registration not found.')
            _transition(conn, enrollment_id, 'generate_hall_ticket')
            cur.execute("""INSERT INTO hall_tickets
                         (student_id,enrollment_id,issued_by,issue_date,exam_date,exam_center,seat_number,qr_code)
                         VALUES (:sid,:eid,:actor_id,SYSDATE,:exam_date,:center,:seat,:qr)""",
                        sid=row[0], eid=enrollment_id, actor_id=session['user_id'], exam_date=row[2],
                        center=center[:100], seat=f'{random.choice(string.ascii_uppercase[:10])}-{random.randint(1,30)}',
                        qr='QR-' + ''.join(random.choices(string.ascii_uppercase+string.digits,k=12)))
            conn.commit()
        flash('Hall ticket issued.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Hall ticket could not be issued.', 'danger')
    return redirect(url_for('examcell.hall_tickets'))


@examcell_bp.route('/evaluations')
@examcell_required
def evaluations():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT x.enrollment_id,x.exam_status,e.exam_code,e.exam_name,
                            e.course_code,e.exam_date,s.student_id,u.name AS student_name,
                            m.marks_obtained,m.max_marks,m.grade
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     JOIN students s ON s.student_id=x.student_id JOIN users u ON u.user_id=s.user_id
                     LEFT JOIN marks m ON m.enrollment_id=x.enrollment_id
                     WHERE x.exam_status IN ('Evaluated','UnderReview')
                     ORDER BY e.exam_date,u.name""")
        queue = _rows(cur)
    return render_template('examcell/evaluations.html', queue=queue,
                           can_review=session.get('role') == 'ExamCell')


@examcell_bp.route('/enrollment/<int:enrollment_id>/<action>', methods=['POST'])
@examcell_editor
def evaluation_action(enrollment_id, action):
    events = {'publish': 'publish_result', 'confirm': 'confirm_evaluation', 'revert': 'revert_evaluation'}
    if action not in events:
        flash('Unknown evaluation action.', 'warning')
        return redirect(url_for('examcell.evaluations'))
    try:
        with get_db() as conn:
            _transition(conn, enrollment_id, events[action])
            conn.commit()
        flash({'publish': 'Result published.', 'confirm': 'Evaluation confirmed.',
               'revert': 'Evaluation returned to faculty.'}[action], 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('The evaluation action could not be saved.', 'danger')
    return redirect(url_for('examcell.evaluations'))


@examcell_bp.route('/reports')
@examcell_required
def reports():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT exam_status,COUNT(*) FROM exam_enrollments GROUP BY exam_status ORDER BY exam_status")
        state_counts = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM exams")
        exam_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM refund_requests WHERE status='Pending'")
        pending_refunds = cur.fetchone()[0]
    chart_data = json.dumps({'states': {'labels': list(state_counts), 'data': list(state_counts.values())}})
    return render_template('examcell/reports.html', state_counts=state_counts,
                           chart_data=chart_data, exam_count=exam_count,
                           pending_refunds=pending_refunds)
