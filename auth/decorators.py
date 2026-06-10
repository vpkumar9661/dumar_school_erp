"""
RBAC Decorators — Role-Based Access Control
Usage:
    @login_required
    @role_required('admin', 'accountant')
    @permission_required('manage_fees')
"""
from functools import wraps
from flask import redirect, url_for, flash, abort, request, jsonify
from flask_login import current_user, login_required as flask_login_required

# Re-export login_required for convenience
login_required = flask_login_required

def role_required(*roles):
    """Allow only specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def permission_required(permission):
    """Allow only users with specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if not current_user.has_permission(permission):
                flash('You do not have permission to perform this action.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def admin_required(f):
    """Shortcut — Admin only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('Administrator access is required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated

def api_login_required(f):
    """For AJAX/API endpoints — returns JSON error instead of redirect."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized', 'message': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated

def sanitize_input(text, max_len=500):
    """Basic input sanitization."""
    if not text:
        return ''
    import html
    return html.escape(str(text).strip())[:max_len]
