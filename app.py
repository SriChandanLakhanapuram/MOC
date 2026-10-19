"""
app.py — University Examination Management System
Main Flask application: blueprints, routes, error handlers.
"""

import os
from flask import Flask, session, redirect, url_for, render_template, jsonify

app = Flask(__name__)
app.secret_key = 'moc_exam_secret_key_2026'  # TODO: change in production

# ---------------------------------------------------------------------------
# Blueprint registration
# ---------------------------------------------------------------------------
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.faculty import faculty_bp
from routes.examcell import examcell_bp

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(admin_bp,   url_prefix='/admin')
app.register_blueprint(faculty_bp, url_prefix='/faculty')
app.register_blueprint(examcell_bp, url_prefix='/examcell')

# FSM singleton
from fsm import fsm as exam_fsm

# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Redirect authenticated users to their role-specific dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    role = session.get('role')
    role_map = {
        'Student':  'student.dashboard',
        'Admin':    'admin.dashboard',
        'Faculty':  'faculty.dashboard',
        'ExamCell': 'examcell.dashboard',
        'HOD':      'examcell.dashboard',
    }
    return redirect(url_for(role_map.get(role, 'auth.login')))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route('/api/fsm')
def api_fsm():
    """Return the FSM state machine as a JSON dict for client-side visualisation."""
    return jsonify(exam_fsm.to_dict())


# ---------------------------------------------------------------------------
# Papers (markdown research/reference papers)
# ---------------------------------------------------------------------------

@app.route('/papers')
def papers():
    """Index page listing all available markdown papers."""
    papers_dir = os.path.join(app.root_path, 'papers')
    if not os.path.isdir(papers_dir):
        os.makedirs(papers_dir, exist_ok=True)
    paper_files = sorted(
        f for f in os.listdir(papers_dir)
        if f.endswith('.md') and f != 'index.md'
    )
    return render_template('papers.html', papers=paper_files)


@app.route('/papers/<path:filename>')
def view_paper(filename):
    """Render a single markdown paper as HTML."""
    import markdown
    papers_dir = os.path.join(app.root_path, 'papers')
    # Basic path traversal guard
    filepath = os.path.realpath(os.path.join(papers_dir, filename))
    if not filepath.startswith(os.path.realpath(papers_dir)):
        return render_template('error.html', code=403, msg='Access Forbidden'), 403
    if not os.path.exists(filepath):
        return render_template('error.html', code=404, msg='Paper not found'), 404
    with open(filepath, 'r', encoding='utf-8') as fh:
        content = fh.read()
    html = markdown.markdown(content, extensions=['tables', 'toc'])
    title = filename.replace('.md', '').replace('_', ' ').title()
    return render_template('paper_view.html', content=html, title=title)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, msg='Access Forbidden'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, msg='Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, msg='Internal Server Error'), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
