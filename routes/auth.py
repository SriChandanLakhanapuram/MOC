"""
routes/auth.py — Authentication Blueprint
Handles login (GET/POST) and logout for the University Examination System.

Password verification uses SHA-256 so that:
    stored hash == SHA-256(plaintext_password)

Session keys set on successful login:
    user_id  — Oracle USERS.user_id
    name     — USERS.name
    email    — USERS.email
    role     — USERS.role  (Admin | Student | Faculty | ExamCell | HOD)
    student_id — STUDENTS.student_id  (only if role == 'Student')
"""

import hashlib
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash
)
from db import get_db

auth_bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(plaintext: str) -> str:
    """Return the SHA-256 hex digest of *plaintext*."""
    return hashlib.sha256(plaintext.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    GET  — Render the login form.
    POST — Validate credentials against Oracle USERS table; on success
           populate the session and redirect to the home index.
    """
    # Already authenticated → go home
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'warning')
            return render_template('login.html')

        password_hash = _sha256(password)

        try:
            with get_db() as conn:
                cursor = conn.cursor()

                # Fetch the user row
                cursor.execute(
                    """
                    SELECT user_id, name, email, password_hash, role
                    FROM   USERS
                    WHERE  LOWER(email) = :email
                    """,
                    {'email': email}
                )
                row = cursor.fetchone()

                if row is None:
                    flash('Invalid email or password.', 'danger')
                    return render_template('login.html')

                db_user_id, db_name, db_email, db_hash, db_role = row

                if db_hash != password_hash:
                    flash('Invalid email or password.', 'danger')
                    return render_template('login.html')

                # ── Populate session ──────────────────────────────────────
                session.clear()
                session['user_id'] = db_user_id
                session['name']    = db_name
                session['email']   = db_email
                session['role']    = db_role

                # For students, also store student_id
                if db_role == 'Student':
                    cursor.execute(
                        """
                        SELECT student_id
                        FROM   STUDENTS
                        WHERE  user_id = :uid
                        """,
                        {'uid': db_user_id}
                    )
                    s_row = cursor.fetchone()
                    if s_row:
                        session['student_id'] = s_row[0]
                    else:
                        # Account exists but no STUDENTS record yet
                        session['student_id'] = None

                flash(f'Welcome back, {db_name}!', 'success')
                return redirect(url_for('index'))

        except Exception as exc:
            flash(f'Database error: {exc}', 'danger')
            return render_template('login.html')

    # GET
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Clear the session and redirect to the login page."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
