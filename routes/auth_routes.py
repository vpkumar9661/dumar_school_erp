"""
Authentication Routes — Login, Logout, Register
Security: Rate limited, bcrypt, session management, audit logging
"""
import re
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, session, jsonify)
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

from db import db
from auth.models import User, ROLES

auth_bp = Blueprint('auth', __name__)

# ── Helpers ────────────────────────────────────────────────
def get_bcrypt():
    from app import bcrypt
    return bcrypt

def get_limiter():
    from app import limiter
    return limiter

def log_login_attempt(username, status, request):
    """Write login attempt to audit log."""
    try:
        cur = db.connection.cursor()
        cur.execute("""
            INSERT INTO login_logs (username, ip_address, user_agent, status)
            VALUES (%s, %s, %s, %s)
        """, (username,
              request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
              request.user_agent.string[:300],
              status))
        db.connection.commit()
        cur.close()
    except Exception:
        pass

def validate_password(pw):
    """Password must be 8+ chars with uppercase, lowercase, digit."""
    if len(pw) < 8:
        return False, 'Password minimum 8 characters hona chahiye.'
    if not re.search(r'[A-Z]', pw):
        return False, 'Password mein ek Capital letter hona chahiye.'
    if not re.search(r'[a-z]', pw):
        return False, 'Password mein ek small letter hona chahiye.'
    if not re.search(r'\d', pw):
        return False, 'Password mein ek number hona chahiye.'
    return True, ''

# ── LOGIN ───────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Rate limit: 5 attempts per minute per IP
    from app import limiter
    limiter.limit('5 per minute')(lambda: None)()

    if current_user.is_authenticated:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        if is_ajax:
            return jsonify({
                'status': 'success',
                'message': f'Welcome back, {current_user.full_name}!',
                'role': current_user.role,
                'full_name': current_user.full_name,
                'redirect': url_for('portal.index') if current_user.role in ('student', 'parent') else url_for('dashboard.index')
            })
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            if is_ajax:
                return jsonify({'status': 'error', 'message': 'Username or password both required.'}), 400
            flash('Username or password both required.', 'danger')
            return render_template('auth/login.html')

        # Fetch user
        cur = db.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user_row = cur.fetchone()
        cur.close()

        bcrypt = get_bcrypt()

        if user_row and bcrypt.check_password_hash(user_row['password'], password):
            if not user_row['is_active']:
                log_login_attempt(username, 'locked', request)
                if is_ajax:
                    return jsonify({'status': 'error', 'message': 'Account deactivated. Contact Admin.'}), 403
                flash('Aapka account deactivated hai. Admin se contact karo.', 'danger')
                return render_template('auth/login.html')

            # Strict Role Check - Block unauthorized roles (students, parents, etc.) from Staff Portal
            if user_row['role'] not in ('admin', 'accountant', 'teacher'):
                log_login_attempt(username, 'unauthorized_role', request)
                if is_ajax:
                    return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401
                flash('Invalid username or password', 'danger')
                return render_template('auth/login.html')

            # Update last_login
            cur = db.connection.cursor()
            cur.execute("UPDATE users SET last_login=%s WHERE id=%s",
                        (datetime.now(), user_row['id']))
            db.connection.commit()
            cur.close()

            user = User(user_row)
            login_user(user, remember=remember)
            log_login_attempt(username, 'success', request)

            # Role-based redirect
            next_page = request.args.get('next')
            if next_page:
                redirect_url = next_page
            else:
                redirect_url = url_for('dashboard.index')

            if is_ajax:
                return jsonify({
                    'status': 'success',
                    'message': f'Welcome back, {user.full_name}!',
                    'role': user.role,
                    'full_name': user.full_name,
                    'redirect': redirect_url
                })
            
            flash(f'Welcome back, {user.full_name}! 👋', 'success')
            return redirect(redirect_url)

        else:
            log_login_attempt(username, 'failed', request)
            if is_ajax:
                return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')

# ── LOGOUT ──────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    name = current_user.full_name
    logout_user()
    flash(f'You are logged out from, {name}. Take care! 👋', 'info')
    return redirect(url_for('public.index'))

# ── CHANGE PASSWORD ──────────────────────────────────────────
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw  = request.form.get('current_password', '')
        new_pw      = request.form.get('new_password', '')
        confirm_pw  = request.form.get('confirm_password', '')

        bcrypt = get_bcrypt()

        # Verify current password
        cur = db.connection.cursor()
        cur.execute("SELECT password FROM users WHERE id=%s", (current_user.id,))
        row = cur.fetchone()
        cur.close()

        if not bcrypt.check_password_hash(row['password'], current_pw):
            flash('Current password Wrong!', 'danger')
            return render_template('auth/change_password.html')

        if new_pw != confirm_pw:
            flash('New password or confirm password not match!', 'danger')
            return render_template('auth/change_password.html')

        valid, msg = validate_password(new_pw)
        if not valid:
            flash(msg, 'danger')
            return render_template('auth/change_password.html')

        hashed = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        cur = db.connection.cursor()
        cur.execute("UPDATE users SET password=%s WHERE id=%s",
                    (hashed, current_user.id))
        db.connection.commit()
        cur.close()

        flash('Password successfully changed! login Again.', 'success')
        logout_user()
        return redirect(url_for('public.index'))

    return render_template('auth/change_password.html')

# ── PROFILE ──────────────────────────────────────────────────
@auth_bp.route('/profile')
@login_required
def profile():
    cur = db.connection.cursor()
    cur.execute("""
        SELECT * FROM login_logs WHERE username=%s
        ORDER BY created_at DESC LIMIT 10
    """, (current_user.username,))
    login_history = cur.fetchall()
    cur.close()
    return render_template('auth/profile.html', login_history=login_history)
