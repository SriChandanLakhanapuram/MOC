"""
routes/admin.py — Admin Blueprint  (url_prefix='/admin')
All routes require session role == 'Admin'.

Capabilities:
    GET  /dashboard              — list all students with FSM states + summary counts
    POST /student/<id>/refund    — FSM event 'request_refund'
    POST /student/<id>/cancel    — FSM event 'cancel_registration'
    GET  /audit                  — full AUDIT_LOG table
    GET  /users                  — list all USERS
    POST /users/add              — insert new user into USERS
"""

from functools import wraps

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash
)
from db import get_db
from fsm import fsm as exam_fsm
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)


# ---------------------------------------------------------------------------
# Access guard
# ---------------------------------------------------------------------------

def admin_required(f):
    """Ensure only Admin role can access the decorated view."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Admin':
            flash('Access denied: Admins only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    List all students with their current FSM state.
    Also display a summary count per state.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # All students with user details
            cursor.execute(
                """
                SELECT s.student_id, u.name, u.email,
                       s.course_code, s.exam_status
                FROM   STUDENTS s
                JOIN   USERS    u ON u.user_id = s.user_id
                ORDER  BY u.name
                """
            )
            cols = [c[0].lower() for c in cursor.description]
            students = [dict(zip(cols, r)) for r in cursor.fetchall()]

            # Summary counts grouped by exam_status
            cursor.execute(
                """
                SELECT exam_status, COUNT(*) AS cnt
                FROM   STUDENTS
                GROUP  BY exam_status
                ORDER  BY exam_status
                """
            )
            state_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return render_template(
            'admin/dashboard.html',
            students=students,
            state_counts=state_counts,
        )

    except Exception as exc:
        flash(f'Error loading dashboard: {exc}', 'danger')
        return redirect(url_for('index'))


# ---------------------------------------------------------------------------

@admin_bp.route('/student/<student_id>/refund', methods=['POST'])
@admin_required
def refund(student_id: int):
    """Trigger 'request_refund' FSM event for the specified student."""
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
                return redirect(url_for('admin.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='request_refund',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Refund requested for student {student_id}.', 'success')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot request refund: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('admin.dashboard'))


# ---------------------------------------------------------------------------

@admin_bp.route('/student/<student_id>/cancel', methods=['POST'])
@admin_required
def cancel_student(student_id: int):
    """Trigger 'cancel_registration' FSM event for the specified student."""
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
                return redirect(url_for('admin.dashboard'))

            exam_fsm.transition(
                student_id=student_id,
                current_state=row[0],
                event='cancel_registration',
                role=session['role'],
                user_id=session['user_id'],
                conn=conn,
            )
            conn.commit()
            flash(f'Registration cancelled for student {student_id}.', 'info')

    except (ValueError, PermissionError) as exc:
        flash(f'Cannot cancel registration: {exc}', 'danger')
    except Exception as exc:
        flash(f'Unexpected error: {exc}', 'danger')

    return redirect(url_for('admin.dashboard'))


# ---------------------------------------------------------------------------

@admin_bp.route('/audit')
@admin_required
def audit():
    """Display the full AUDIT_LOG table, newest entries first."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.log_id, a.student_id, a.event, a.old_state, a.new_state,
                       a.log_time AS timestamp, u.name AS performed_by_name,
                       u.role AS performed_by_role, s.name AS student_name
                FROM   AUDIT_LOG a
                LEFT JOIN USERS u ON u.user_id = a.user_id
                LEFT JOIN STUDENTS st ON st.student_id = a.student_id
                LEFT JOIN USERS s ON s.user_id = st.user_id
                ORDER  BY a.log_time DESC
                FETCH  FIRST 500 ROWS ONLY
                """
            )
            cols = [c[0].lower() for c in cursor.description]
            logs = [dict(zip(cols, r)) for r in cursor.fetchall()]

        return render_template('admin/audit.html', logs=logs)

    except Exception as exc:
        flash(f'Error loading audit log: {exc}', 'danger')
        return redirect(url_for('admin.dashboard'))


# ---------------------------------------------------------------------------

@admin_bp.route('/users')
@admin_required
def users():
    """List all users in the USERS table."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, name, email, role
                FROM   USERS
                ORDER  BY name
                """
            )
            cols = [c[0].lower() for c in cursor.description]
            user_list = [dict(zip(cols, r)) for r in cursor.fetchall()]

        return render_template('admin/users.html', users=user_list)

    except Exception as exc:
        flash(f'Error loading users: {exc}', 'danger')
        return redirect(url_for('admin.dashboard'))


# ---------------------------------------------------------------------------

@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """
    Insert a new user into the USERS table.
    Password is stored as a salted Werkzeug password hash.
    Form fields expected: name, email, password, role
    """
    name     = request.form.get('name', '').strip()
    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', '').strip()

    valid_roles = {'Admin', 'Student', 'Faculty', 'ExamCell', 'HOD'}

    if not all([name, email, password, role]):
        flash('All fields (name, email, password, role) are required.', 'warning')
        return redirect(url_for('admin.users'))

    if role not in valid_roles:
        flash(f'Invalid role. Must be one of: {", ".join(sorted(valid_roles))}.', 'warning')
        return redirect(url_for('admin.users'))

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check duplicate email
            cursor.execute(
                "SELECT 1 FROM USERS WHERE LOWER(email) = :email",
                {'email': email}
            )
            if cursor.fetchone():
                flash(f'A user with email "{email}" already exists.', 'warning')
                return redirect(url_for('admin.users'))

            cursor.execute(
                """
                INSERT INTO USERS (name, email, password_hash, role)
                VALUES (:name, :email, :pwd, :role)
                """,
                {'name': name, 'email': email, 'pwd': password_hash, 'role': role}
            )
            cursor.execute('SELECT user_id FROM USERS WHERE LOWER(email) = :email', {'email': email})
            new_user_id = cursor.fetchone()[0]
            if role == 'Student':
                cursor.execute('SELECT course_code FROM COURSES ORDER BY course_code FETCH FIRST 1 ROWS ONLY')
                course = cursor.fetchone()
                if not course:
                    raise ValueError('Add at least one course before creating a student account.')
                cursor.execute(
                    "INSERT INTO STUDENTS (student_id, user_id, course_code, exam_status) VALUES (:sid, :user_id_param, :course, 'Registered')",
                    {'sid': f'S{new_user_id:06d}', 'user_id_param': new_user_id, 'course': course[0]},
                )
            elif role == 'Faculty':
                cursor.execute(
                    'INSERT INTO FACULTY (faculty_id, user_id, department) VALUES (:fid, :user_id_param, :dept)',
                    {'fid': f'F{new_user_id:06d}', 'user_id_param': new_user_id, 'dept': 'General'},
                )
            conn.commit()
            flash(f'User "{name}" ({role}) created successfully.', 'success')

    except Exception as exc:
        flash(f'Error creating user: {exc}', 'danger')

    return redirect(url_for('admin.users'))
