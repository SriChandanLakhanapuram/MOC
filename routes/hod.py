"""Department-scoped course catalog and teaching assignment tools for HODs."""
import re
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_db

hod_bp = Blueprint('hod', __name__)


def hod_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'HOD':
            flash('This workspace is for Heads of Department.', 'danger')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


def _rows(cur):
    names = [column[0].lower() for column in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def _departments(cur):
    cur.execute('SELECT department FROM hod_departments WHERE user_id=:actor_id ORDER BY department',
                actor_id=session['user_id'])
    return [row[0] for row in cur.fetchall()]


def _owns_course(cur, course_code):
    cur.execute("""SELECT 1 FROM courses c JOIN hod_departments h ON h.department=c.department
                 WHERE c.course_code=:course_code AND h.user_id=:actor_id""",
                course_code=course_code, actor_id=session['user_id'])
    return bool(cur.fetchone())


@hod_bp.route('/dashboard')
@hod_required
def dashboard():
    with get_db() as conn:
        cur = conn.cursor()
        departments = _departments(cur)
        if not departments:
            courses = faculty_count = assignment_count = 0
            recent = []
        else:
            cur.execute("""SELECT COUNT(*) FROM courses c JOIN hod_departments h ON h.department=c.department
                         WHERE h.user_id=:actor_id""", actor_id=session['user_id'])
            courses = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(DISTINCT f.faculty_id) FROM faculty f
                         JOIN hod_departments h ON h.department=f.department
                         WHERE h.user_id=:actor_id""", actor_id=session['user_id'])
            faculty_count = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(*) FROM course_faculty a
                         JOIN courses c ON c.course_code=a.course_code
                         JOIN hod_departments h ON h.department=c.department
                         WHERE h.user_id=:actor_id AND a.active='Y'""", actor_id=session['user_id'])
            assignment_count = cur.fetchone()[0]
            cur.execute("""SELECT c.course_code,c.course_name,a.academic_year,a.term,a.assignment_role,
                                f.faculty_id,u.name AS faculty_name,a.assigned_at
                         FROM course_faculty a JOIN courses c ON c.course_code=a.course_code
                         JOIN hod_departments h ON h.department=c.department
                         JOIN faculty f ON f.faculty_id=a.faculty_id JOIN users u ON u.user_id=f.user_id
                         WHERE h.user_id=:actor_id AND a.active='Y'
                         ORDER BY a.assigned_at DESC FETCH FIRST 8 ROWS ONLY""",
                        actor_id=session['user_id'])
            recent = _rows(cur)
    return render_template('hod/dashboard.html', departments=departments, courses=courses,
                           faculty_count=faculty_count, assignment_count=assignment_count, recent=recent)


@hod_bp.route('/courses')
@hod_required
def courses():
    with get_db() as conn:
        cur = conn.cursor()
        departments = _departments(cur)
        cur.execute("""SELECT c.course_code,c.course_name,c.department,c.credits,
                            (SELECT COUNT(*) FROM course_faculty a
                             WHERE a.course_code=c.course_code AND a.active='Y') AS instructors,
                            (SELECT COUNT(*) FROM students s WHERE s.course_code=c.course_code) AS students
                     FROM courses c JOIN hod_departments h ON h.department=c.department
                     WHERE h.user_id=:actor_id ORDER BY c.course_name""", actor_id=session['user_id'])
        courses = _rows(cur)
    return render_template('hod/courses.html', courses=courses, departments=departments)


@hod_bp.route('/courses/create', methods=['POST'])
@hod_required
def create_course():
    code = request.form.get('course_code', '').strip().upper()
    name = request.form.get('course_name', '').strip()
    department = request.form.get('department', '').strip()
    credits = request.form.get('credits', type=int)
    if not re.fullmatch(r'[A-Z0-9-]{2,10}', code) or not name or not credits or credits < 1 or credits > 12:
        flash('Enter a course code, name, and a credit value from 1 to 12.', 'warning')
        return redirect(url_for('hod.courses'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            if department not in _departments(cur):
                raise ValueError('Choose a department assigned to your HOD account.')
            cur.execute("""INSERT INTO courses(course_code,course_name,department,credits)
                         VALUES(:course_code,:course_name,:department,:credits)""",
                        course_code=code, course_name=name, department=department, credits=credits)
            conn.commit()
        flash(f'{code} was added to the {department} course catalog.', 'success')
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('Course code already exists or the course could not be saved.', 'danger')
    return redirect(url_for('hod.courses'))


@hod_bp.route('/courses/<course_code>/update', methods=['POST'])
@hod_required
def update_course(course_code):
    name = request.form.get('course_name', '').strip()
    credits = request.form.get('credits', type=int)
    if not name or not credits or credits < 1 or credits > 12:
        flash('Enter a course name and a credit value from 1 to 12.', 'warning')
        return redirect(url_for('hod.courses'))
    with get_db() as conn:
        cur = conn.cursor()
        if not _owns_course(cur, course_code):
            flash('That course is outside your department.', 'danger')
        else:
            cur.execute('UPDATE courses SET course_name=:course_name,credits=:credits WHERE course_code=:course_code',
                        course_name=name, credits=credits, course_code=course_code)
            conn.commit()
            flash('Course details updated. Course codes and department ownership stay fixed after creation.', 'success')
    return redirect(url_for('hod.courses'))


@hod_bp.route('/faculty')
@hod_required
def faculty_assignments():
    with get_db() as conn:
        cur = conn.cursor()
        departments = _departments(cur)
        cur.execute("""SELECT f.faculty_id,u.name,u.email,f.department,
                            (SELECT COUNT(*) FROM course_faculty a WHERE a.faculty_id=f.faculty_id AND a.active='Y') AS active_courses
                     FROM faculty f JOIN users u ON u.user_id=f.user_id
                     ORDER BY f.department,u.name""")
        faculty = _rows(cur)
        cur.execute("""SELECT a.assignment_id,a.course_code,c.course_name,a.faculty_id,u.name AS faculty_name,
                            f.department AS home_department,a.academic_year,a.term,a.assignment_role,
                            a.active,a.assigned_at,a.ended_at
                     FROM course_faculty a JOIN courses c ON c.course_code=a.course_code
                     JOIN hod_departments h ON h.department=c.department
                     JOIN faculty f ON f.faculty_id=a.faculty_id JOIN users u ON u.user_id=f.user_id
                     WHERE h.user_id=:actor_id ORDER BY a.active DESC,a.academic_year DESC,a.term,c.course_name,u.name""",
                    actor_id=session['user_id'])
        assignments = _rows(cur)
        cur.execute("""SELECT c.course_code,c.course_name FROM courses c JOIN hod_departments h ON h.department=c.department
                     WHERE h.user_id=:actor_id ORDER BY c.course_name""", actor_id=session['user_id'])
        courses = _rows(cur)
    current_year = str(__import__('datetime').date.today().year)
    return render_template('hod/faculty.html', faculty=faculty, assignments=assignments,
                           courses=courses, departments=departments,
                           academic_year=f'{current_year}-{str(int(current_year)+1)[-2:]}')


@hod_bp.route('/faculty/assign', methods=['POST'])
@hod_required
def assign_faculty():
    course_code = request.form.get('course_code', '').strip().upper()
    faculty_id = request.form.get('faculty_id', '').strip().upper()
    academic_year = request.form.get('academic_year', '').strip()
    term = request.form.get('term', '').strip()
    role = request.form.get('assignment_role', 'Instructor').strip()
    if (not re.fullmatch(r'\d{4}-\d{2}', academic_year) or
            term not in {'Term 1', 'Term 2', 'Full year'} or
            role not in {'Lead', 'Co-instructor', 'Lab instructor'}):
        flash('Check the academic year, term, and teaching role.', 'warning')
        return redirect(url_for('hod.faculty_assignments'))
    try:
        with get_db() as conn:
            cur = conn.cursor()
            if not _owns_course(cur, course_code):
                raise ValueError('Choose a course in your department.')
            cur.execute('SELECT 1 FROM faculty WHERE faculty_id=:faculty_id', faculty_id=faculty_id)
            if not cur.fetchone():
                raise ValueError('Choose an existing faculty account.')
            if role == 'Lead':
                cur.execute("""SELECT u.name FROM course_faculty a
                             JOIN faculty f ON f.faculty_id=a.faculty_id JOIN users u ON u.user_id=f.user_id
                             WHERE a.course_code=:course_code AND a.academic_year=:academic_year
                               AND a.term=:term AND a.assignment_role='Lead' AND a.active='Y'""",
                            course_code=course_code, academic_year=academic_year, term=term)
                current_lead = cur.fetchone()
                if current_lead:
                    raise ValueError(f"{current_lead[0]} is already the Lead for this course and term. End that assignment before replacing it.")
            cur.execute("""INSERT INTO course_faculty
                         (course_code,faculty_id,academic_year,term,assignment_role,assigned_by)
                         VALUES(:course_code,:faculty_id,:academic_year,:term,:assignment_role,:actor_id)""",
                        course_code=course_code, faculty_id=faculty_id, academic_year=academic_year,
                        term=term, assignment_role=role, actor_id=session['user_id'])
            conn.commit()
        flash('Faculty assignment added. Past assignments are retained when they are ended.', 'success')
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception:
        flash('An active assignment already exists for this instructor, course, year, and term.', 'danger')
    return redirect(url_for('hod.faculty_assignments'))


@hod_bp.route('/faculty/assignments/<int:assignment_id>/end', methods=['POST'])
@hod_required
def end_assignment(assignment_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""UPDATE course_faculty a SET active='N',ended_by=:actor_id,ended_at=SYSTIMESTAMP
                     WHERE a.assignment_id=:assignment_id AND a.active='Y'
                       AND EXISTS (SELECT 1 FROM courses c JOIN hod_departments h ON h.department=c.department
                                   WHERE c.course_code=a.course_code AND h.user_id=:actor_id)""",
                    actor_id=session['user_id'], assignment_id=assignment_id)
        if cur.rowcount:
            conn.commit()
            flash('Assignment ended and preserved in the history.', 'success')
        else:
            flash('Active assignment not found in your department.', 'warning')
    return redirect(url_for('hod.faculty_assignments'))
