"""
Vivekanand Vidya Mandir Dharampur — School ERP v2.0
Production-Ready | Secure | Role-Based Access Control
"""
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, send_from_directory
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from db import db
from utils.storage import get_public_url

# ── App Init ────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# ── Extensions ──────────────────────────────────────────────
db.init_app(app)
bcrypt = Bcrypt(app)

# Rate Limiter — prevent brute force
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=['200 per day', '50 per hour'],
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view       = 'auth.login'
login_manager.login_message    = 'Please login to access this page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    from auth.models import User
    return User.get(user_id)

# Upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── Global Template Context ──────────────────────────────────
@app.context_processor
def inject_globals():
    from utils.storage import _get_creds
    url, key = _get_creds()
    return {
        'now':         datetime.now,
        'school_name': app.config.get('SCHOOL_NAME', 'VVM Dharampur'),
        'get_url':     get_public_url,
        'supabase_ready': bool(url and key)
    }

# ── Security Headers ─────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options']  = 'nosniff'
    response.headers['X-Frame-Options']         = 'SAMEORIGIN'
    response.headers['X-XSS-Protection']        = '1; mode=block'
    response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
    return response

# ── Register Blueprints ──────────────────────────────────────
from routes.auth_routes      import auth_bp
from routes.dashboard        import dashboard_bp
from routes.students         import students_bp
from routes.fees             import fees_bp
from routes.teachers         import teachers_bp
from routes.transport        import transport_bp
from routes.exams            import exams_bp
from routes.attendance       import attendance_bp
from routes.idcard           import idcard_bp
from routes.reports          import reports_bp
from routes.noticeboard      import noticeboard_bp
from routes.users            import users_bp
from routes.settings_routes  import settings_bp
from routes.portal           import portal_bp
from routes.public            import public_bp
from routes.admin_content     import admin_content_bp
from routes.student_portal    import student_portal_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(students_bp,   url_prefix='/students')
app.register_blueprint(fees_bp,       url_prefix='/fees')
app.register_blueprint(teachers_bp,   url_prefix='/teachers')
app.register_blueprint(transport_bp,  url_prefix='/transport')
app.register_blueprint(exams_bp,      url_prefix='/exams')
app.register_blueprint(attendance_bp, url_prefix='/attendance')
app.register_blueprint(idcard_bp,     url_prefix='/idcard')
app.register_blueprint(reports_bp,    url_prefix='/reports')
app.register_blueprint(noticeboard_bp,url_prefix='/noticeboard')
app.register_blueprint(users_bp,      url_prefix='/users')
app.register_blueprint(settings_bp,   url_prefix='/settings')
app.register_blueprint(portal_bp,     url_prefix='/portal')
app.register_blueprint(public_bp)           # Public school website — handles '/'
app.register_blueprint(admin_content_bp)    # Gallery / Downloads / Enquiries
app.register_blueprint(student_portal_bp, url_prefix='/student-portal')  # Premium Student Portal

# ── Root redirect ────────────────────────────────────────────
@app.route('/erp')
def erp_index():
    if current_user.is_authenticated:
        if current_user.role in ('student', 'parent'):
            return redirect(url_for('portal.index'))
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))
# Note: '/' is handled by routes/public.py (public school website)

# Serve favicon.ico directly from static/images to avoid 404 errors
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                               'school_logo.png', mimetype='image/png')


# ── Error Handlers ───────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('errors/429.html'), 429

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
