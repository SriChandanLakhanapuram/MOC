"""Faculty exam work, assigned-only attendance and auditable evaluations."""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_db
from fsm import fsm as exam_fsm

faculty_bp = Blueprint('faculty', __name__)


def faculty_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Faculty':
            flash('This area is for faculty.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def _rows(cur):
    cols = [c[0].lower() for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _assigned(cur, enrollment_id):
    cur.execute("""SELECT x.student_id,x.exam_status,x.exam_id,e.exam_code,e.exam_name,
                        e.course_code,e.exam_date,u.name,s.student_id
                 FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                 JOIN students s ON s.student_id=x.student_id
                 JOIN users u ON u.user_id=s.user_id
                 JOIN exam_faculty a ON a.exam_id=e.exam_id
                 JOIN faculty f ON f.faculty_id=a.faculty_id
                 WHERE x.enrollment_id=:eid AND f.user_id=:actor_id""",
                eid=enrollment_id, actor_id=session['user_id'])
    return cur.fetchone()


@faculty_bp.route('/dashboard')
@faculty_required
def dashboard():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT x.enrollment_id,x.exam_status,e.exam_code,e.exam_name,
                            e.course_code,e.exam_date,s.student_id,u.name
                     FROM exam_enrollments x JOIN exams e ON e.exam_id=x.exam_id
                     JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id
                     JOIN exam_faculty a ON a.exam_id=e.exam_id
                     JOIN faculty f ON f.faculty_id=a.faculty_id
                     WHERE f.user_id=:actor_id AND x.exam_status IN
                           ('HallTicketIssued','ExamTaken','Evaluated','UnderReview')
                     ORDER BY e.exam_date,u.name""", actor_id=session['user_id'])
        tasks = _rows(cur)
    return render_template('faculty/dashboard.html', tasks=tasks)


@faculty_bp.route('/exams')
@faculty_required
def exams():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT e.exam_code,e.exam_name,e.course_code,c.course_name,
                            e.exam_date,e.status,
                            (SELECT COUNT(*) FROM exam_enrollments x WHERE x.exam_id=e.exam_id) AS candidates
                     FROM exams e JOIN courses c ON c.course_code=e.course_code
                     JOIN exam_faculty a ON a.exam_id=e.exam_id
                     JOIN faculty f ON f.faculty_id=a.faculty_id
                     WHERE f.user_id=:actor_id ORDER BY e.exam_date DESC""", actor_id=session['user_id'])
        exams = _rows(cur)
    return render_template('faculty/exams.html', exams=exams)


@faculty_bp.route('/enrollment/<int:enrollment_id>/attendance', methods=['POST'])
@faculty_required
def mark_attendance(enrollment_id):
    return _transition(enrollment_id, 'mark_attendance', 'Student attended the exam.')


@faculty_bp.route('/enrollment/<int:enrollment_id>/absent', methods=['POST'])
@faculty_required
def mark_absent(enrollment_id):
    return _transition(enrollment_id, 'mark_absent', 'Student marked absent.')


def _transition(enrollment_id, event, success):
    try:
        with get_db() as conn:
            cur = conn.cursor()
            row = _assigned(cur, enrollment_id)
            if not row:
                raise PermissionError('This exam is not assigned to your faculty account.')
            exam_fsm.transition(row[0], event, 'Faculty', session['user_id'], conn=conn,
                                enrollment_id=enrollment_id)
            conn.commit()
        flash(success, 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('The exam action could not be saved.', 'danger')
    return redirect(url_for('faculty.dashboard'))


@faculty_bp.route('/enrollment/<int:enrollment_id>/evaluate', methods=['POST'])
@faculty_required
def evaluate(enrollment_id):
    try:
        score = float(request.form.get('marks_obtained', ''))
        maximum = float(request.form.get('max_marks', '100'))
    except ValueError:
        flash('Enter a valid numeric mark and maximum score.', 'warning')
        return redirect(url_for('faculty.dashboard'))
    grade = request.form.get('grade', '').strip().upper()[:5]
    subject_name = request.form.get('subject_name', '').strip()
    if maximum <= 0 or score < 0 or score > maximum or not subject_name:
        flash('Check that the subject is named and the score is within the maximum.', 'warning')
        return redirect(url_for('faculty.dashboard'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            row = _assigned(cur, enrollment_id)
            if not row:
                raise PermissionError('This exam is not assigned to your faculty account.')
            if row[1] != 'ExamTaken':
                raise ValueError('Attendance must be recorded before evaluation.')
            cur.execute('SELECT faculty_id FROM faculty WHERE user_id=:actor_id', actor_id=session['user_id'])
            faculty_id = cur.fetchone()[0]
            exam_fsm.transition(row[0], 'submit_evaluation', 'Faculty', session['user_id'],
                                conn=conn, enrollment_id=enrollment_id)
            cur.execute("""INSERT INTO marks
                         (student_id,enrollment_id,subject_code,subject_name,course_code,
                          marks_obtained,max_marks,grade,entered_by,evaluated_by,evaluation_date)
                         VALUES (:sid,:eid,:code,:name,:course,:score,:maximum,:grade,:fid,:actor_id,SYSDATE)""",
                        sid=row[0], eid=enrollment_id, code=row[5], name=subject_name,
                        course=row[5], score=score, maximum=maximum, grade=grade,
                        fid=faculty_id, actor_id=session['user_id'])
            conn.commit()
        flash('Evaluation saved and ready for Examination Cell review.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Evaluation could not be saved.', 'danger')
    return redirect(url_for('faculty.dashboard'))


@faculty_bp.route('/enrollment/<int:enrollment_id>/flag', methods=['POST'])
@faculty_required
def flag_discrepancy(enrollment_id):
    return _transition(enrollment_id, 'flag_discrepancy', 'Evaluation sent for Examination Cell review.')


@faculty_bp.route('/evaluations')
@faculty_required
def evaluations():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT m.mark_id,m.enrollment_id,m.subject_name,m.subject_code,
                            m.marks_obtained,m.max_marks,m.grade,m.evaluation_date,
                            e.exam_code,e.exam_name,x.exam_status,s.student_id,u.name AS student_name
                     FROM marks m JOIN exam_enrollments x ON x.enrollment_id=m.enrollment_id
                     JOIN exams e ON e.exam_id=x.exam_id JOIN students s ON s.student_id=x.student_id
                     JOIN users u ON u.user_id=s.user_id JOIN exam_faculty a ON a.exam_id=e.exam_id
                     JOIN faculty f ON f.faculty_id=a.faculty_id
                     WHERE f.user_id=:actor_id ORDER BY m.evaluation_date DESC""", actor_id=session['user_id'])
        evaluations = _rows(cur)
        cur.execute("""SELECT h.history_id,h.mark_id,h.old_marks,h.new_marks,h.old_grade,
                            h.new_grade,h.reason,h.changed_at,u.name AS changed_by
                     FROM evaluation_history h JOIN marks m ON m.mark_id=h.mark_id
                     JOIN exam_enrollments x ON x.enrollment_id=m.enrollment_id
                     JOIN exam_faculty a ON a.exam_id=x.exam_id
                     JOIN faculty f ON f.faculty_id=a.faculty_id
                     JOIN users u ON u.user_id=h.changed_by
                     WHERE f.user_id=:actor_id ORDER BY h.changed_at DESC""", actor_id=session['user_id'])
        history_rows = _rows(cur)
    history = {}
    for item in history_rows:
        history.setdefault(item['mark_id'], []).append(item)
    return render_template('faculty/evaluations.html', evaluations=evaluations, history=history)


@faculty_bp.route('/evaluations/<int:mark_id>/update', methods=['POST'])
@faculty_required
def update_evaluation(mark_id):
    reason = request.form.get('reason', '').strip()
    try:
        score = float(request.form.get('marks_obtained', ''))
        maximum = float(request.form.get('max_marks', '100'))
    except ValueError:
        flash('Enter valid numeric marks.', 'warning')
        return redirect(url_for('faculty.evaluations'))
    grade = request.form.get('grade', '').strip().upper()[:5]
    if not reason or maximum <= 0 or score < 0 or score > maximum:
        flash('Provide a reason and a score within the maximum.', 'warning')
        return redirect(url_for('faculty.evaluations'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT m.enrollment_id,m.marks_obtained,m.grade,x.exam_status
                         FROM marks m JOIN exam_enrollments x ON x.enrollment_id=m.enrollment_id
                         JOIN exams e ON e.exam_id=x.exam_id
                         JOIN exam_faculty a ON a.exam_id=e.exam_id
                         JOIN faculty f ON f.faculty_id=a.faculty_id
                         WHERE m.mark_id=:mid AND f.user_id=:actor_id FOR UPDATE""",
                        mid=mark_id, actor_id=session['user_id'])
            row = cur.fetchone()
            if not row:
                raise PermissionError('Evaluation not found in your assigned exams.')
            if row[3] == 'ResultPublished':
                raise ValueError('Published results are locked. Contact Exam Cell for a formal correction.')
            cur.execute("""INSERT INTO evaluation_history
                         (mark_id,changed_by,old_marks,new_marks,old_grade,new_grade,reason)
                         VALUES (:mid,:actor_id,:old_score,:new_score,:old_grade_value,:new_grade_value,:reason)""",
                        mid=mark_id, actor_id=session['user_id'], old_score=row[1], new_score=score,
                        old_grade_value=row[2], new_grade_value=grade, reason=reason[:500])
            cur.execute("""UPDATE marks SET marks_obtained=:score,max_marks=:maximum,
                         grade=:grade,evaluated_by=:actor_id,evaluation_date=SYSDATE WHERE mark_id=:mid""",
                        score=score, maximum=maximum, grade=grade,
                        actor_id=session['user_id'], mid=mark_id)
            cur.execute("""INSERT INTO audit_log
                         (user_id,student_id,enrollment_id,event,old_state,new_state)
                         SELECT :actor_id,x.student_id,x.enrollment_id,'evaluation_corrected',x.exam_status,x.exam_status
                         FROM exam_enrollments x WHERE x.enrollment_id=:eid""",
                        actor_id=session['user_id'], eid=row[0])
            conn.commit()
        flash('Correction saved with its reason and previous mark in the history.', 'success')
    except (ValueError, PermissionError) as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('The correction could not be saved.', 'danger')
    return redirect(url_for('faculty.evaluations'))
