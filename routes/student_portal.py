"""
Student Portal — Premium Login, Registration, Dashboard APIs
Replaces the old Student Hub with a full authentication-gated portal.
"""
import os
import secrets
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from flask_login import login_user, logout_user, login_required, current_user
from db import db

import google.generativeai as genai

student_portal_bp = Blueprint('student_portal', __name__)

# ── Helpers ────────────────────────────────────────────────────

def get_bcrypt():
    from app import bcrypt
    return bcrypt

def ensure_portal_tables():
    """Create any extra tables needed for the student portal."""
    try:
        cur = db.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_password_resets (
                id SERIAL PRIMARY KEY,
                student_id INT NOT NULL,
                user_id INT,
                token VARCHAR(128) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE student_password_resets ENABLE ROW LEVEL SECURITY;
        """)
        db.connection.commit()
        cur.close()
    except Exception:
        try:
            db.connection.rollback()
        except:
            pass

def student_api_required(f):
    """Decorator: require student login for API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': 'Please login to continue.'}), 401
        if not current_user.student_id:
            return jsonify({'status': 'error', 'message': 'Student account required.'}), 403
        return f(*args, **kwargs)
    return decorated

def get_student_record(student_id):
    """Fetch full student row by ID."""
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
        row = cur.fetchone()
        cur.close()
        return row
    except:
        return None

def get_all_settings():
    """Load every key-value pair from the settings table."""
    cfg = {}
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_key, setting_value FROM settings")
        for row in cur.fetchall():
            cfg[row['setting_key']] = row['setting_value']
        cur.close()
    except:
        pass
    return cfg


# ══════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ══════════════════════════════════════════════════════════════

@student_portal_bp.route('/')
def portal_login_page():
    """Serve the premium login / register / forgot-password page."""
    ensure_portal_tables()
    if current_user.is_authenticated and current_user.student_id:
        return redirect(url_for('student_portal.dashboard'))
    cfg = get_all_settings()
    return render_template('student_portal/login.html', cfg=cfg)

@student_portal_bp.route('/dashboard')
@login_required
def dashboard():
    """Serve the student dashboard SPA."""
    if not current_user.student_id:
        flash('Only student accounts can access the Student Portal.', 'warning')
        return redirect(url_for('student_portal.portal_login_page'))
    student = get_student_record(current_user.student_id)
    if not student:
        flash('Student record not found. Contact admin.', 'danger')
        return redirect(url_for('student_portal.portal_login_page'))
    cfg = get_all_settings()
    return render_template('student_portal/dashboard.html',
                           student=student, cfg=cfg)


# ══════════════════════════════════════════════════════════════
#  AUTH API ENDPOINTS
# ══════════════════════════════════════════════════════════════

@student_portal_bp.route('/api/login', methods=['POST'])
def api_login():
    """AJAX login — accepts admission number, email, or mobile + password."""
    data = request.get_json() or {}
    login_id = data.get('login_id', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not login_id or not password:
        return jsonify({'status': 'error',
                        'message': 'Login ID and password are required.'}), 400

    try:
        cur = db.connection.cursor()

        # Try to find the user by username (admission number), email, or mobile
        # First check if login_id matches a username directly
        cur.execute("SELECT * FROM users WHERE username=%s AND role='student'", (login_id.lower(),))
        user_row = cur.fetchone()

        if not user_row:
            # Try by email
            cur.execute("SELECT * FROM users WHERE email=%s AND role='student'", (login_id.lower(),))
            user_row = cur.fetchone()

        if not user_row:
            # Try by mobile number via linked student record
            cur.execute("""
                SELECT u.* FROM users u
                JOIN students s ON u.student_id = s.id
                WHERE s.mobile_number = %s AND u.role = 'student'
            """, (login_id,))
            user_row = cur.fetchone()

        if not user_row:
            # Try by admission number via linked student record
            cur.execute("""
                SELECT u.* FROM users u
                JOIN students s ON u.student_id = s.id
                WHERE s.admission_number = %s AND u.role = 'student'
            """, (login_id,))
            user_row = cur.fetchone()

        cur.close()

        if not user_row:
            return jsonify({'status': 'error',
                            'message': 'No student account found with this ID.'}), 401

        bcrypt = get_bcrypt()
        if not bcrypt.check_password_hash(user_row['password'], password):
            # Log failed attempt
            try:
                cur = db.connection.cursor()
                cur.execute("""
                    INSERT INTO login_logs (username, ip_address, user_agent, status)
                    VALUES (%s, %s, %s, 'failed')
                """, (user_row['username'],
                      request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                      str(request.user_agent)[:300]))
                db.connection.commit()
                cur.close()
            except:
                pass
            return jsonify({'status': 'error',
                            'message': 'Incorrect password. Please try again.'}), 401

        if not user_row['is_active']:
            return jsonify({'status': 'error',
                            'message': 'Account is deactivated. Contact admin.'}), 403

        # Success — log in
        from auth.models import User
        user = User(user_row)
        login_user(user, remember=remember)

        # Update last_login
        try:
            cur = db.connection.cursor()
            cur.execute("UPDATE users SET last_login=%s WHERE id=%s",
                        (datetime.now(), user.id))
            cur.execute("""
                INSERT INTO login_logs (username, ip_address, user_agent, status)
                VALUES (%s, %s, %s, 'success')
            """, (user.username,
                  request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                  str(request.user_agent)[:300]))
            db.connection.commit()
            cur.close()
        except:
            pass

        return jsonify({
            'status': 'success',
            'message': f'Welcome back, {user.full_name}!',
            'redirect': url_for('student_portal.dashboard')
        })

    except Exception as e:
        print(f"Student login error: {e}")
        return jsonify({'status': 'error',
                        'message': 'Server error. Please try again.'}), 500


@student_portal_bp.route('/api/register', methods=['POST'])
def api_register():
    """Self-registration: student must exist in students table (admin-created)."""
    data = request.get_json() or {}

    admission_number = data.get('admission_number', '').strip()
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    mobile = data.get('mobile', '').strip()
    dob = data.get('date_of_birth', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Validation
    if not all([admission_number, full_name, email, password, confirm_password]):
        return jsonify({'status': 'error',
                        'message': 'All required fields must be filled.'}), 400

    if password != confirm_password:
        return jsonify({'status': 'error',
                        'message': 'Passwords do not match.'}), 400

    if len(password) < 8:
        return jsonify({'status': 'error',
                        'message': 'Password must be at least 8 characters.'}), 400

    import re
    if not re.search(r'[A-Z]', password):
        return jsonify({'status': 'error',
                        'message': 'Password must include at least one uppercase letter.'}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({'status': 'error',
                        'message': 'Password must include at least one lowercase letter.'}), 400
    if not re.search(r'\d', password):
        return jsonify({'status': 'error',
                        'message': 'Password must include at least one digit.'}), 400

    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'status': 'error',
                        'message': 'Invalid email address format.'}), 400

    try:
        cur = db.connection.cursor()

        # 1. Find student by admission number
        cur.execute("SELECT * FROM students WHERE admission_number=%s AND status='Active'",
                    (admission_number,))
        student = cur.fetchone()
        if not student:
            cur.close()
            return jsonify({'status': 'error',
                            'message': 'No active student found with this admission number. Please contact school admin.'}), 404

        # 2. Check if a user account already exists for this student
        cur.execute("SELECT id FROM users WHERE student_id=%s", (student['id'],))
        existing_user = cur.fetchone()
        if existing_user:
            cur.close()
            return jsonify({'status': 'error',
                            'message': 'An account already exists for this admission number. Please login instead.'}), 409

        # 3. Check if username (admission_number) is taken
        username = admission_number.lower()
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close()
            return jsonify({'status': 'error',
                            'message': 'Username already taken. Contact admin.'}), 409

        # 4. Check email uniqueness
        if email:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                cur.close()
                return jsonify({'status': 'error',
                                'message': 'This email is already registered. Use a different email or login.'}), 409

        # 5. Create user account
        bcrypt = get_bcrypt()
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')

        cur.execute("""
            INSERT INTO users (username, password, email, full_name, role, student_id, is_active)
            VALUES (%s, %s, %s, %s, 'student', %s, true)
            RETURNING id
        """, (username, hashed, email, full_name, student['id']))

        new_user_id = cur.fetchone()['id']

        # 6. Update student record with email/mobile if provided
        updates = []
        params = []
        if mobile and not student.get('mobile_number'):
            updates.append("mobile_number=%s")
            params.append(mobile)
        if updates:
            params.append(student['id'])
            cur.execute(f"UPDATE students SET {', '.join(updates)} WHERE id=%s", tuple(params))

        db.connection.commit()
        cur.close()

        return jsonify({
            'status': 'success',
            'message': 'Registration successful! You can now login with your admission number and password.'
        })

    except Exception as e:
        try:
            db.connection.rollback()
        except:
            pass
        print(f"Registration error: {e}")
        return jsonify({'status': 'error',
                        'message': 'Registration failed. Please try again later.'}), 500


@student_portal_bp.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    """Initiate password reset — generates token."""
    data = request.get_json() or {}
    identifier = data.get('identifier', '').strip()

    if not identifier:
        return jsonify({'status': 'error',
                        'message': 'Please enter your admission number or email.'}), 400

    try:
        cur = db.connection.cursor()

        # Find user by admission number (username) or email
        cur.execute("""
            SELECT u.*, s.admission_number, s.student_name
            FROM users u
            JOIN students s ON u.student_id = s.id
            WHERE (u.username=%s OR u.email=%s) AND u.role='student'
        """, (identifier.lower(), identifier.lower()))
        user_row = cur.fetchone()

        if not user_row:
            cur.close()
            # Don't reveal whether account exists
            return jsonify({
                'status': 'success',
                'message': 'If an account exists with this information, a reset token has been generated. Please contact the school admin with your admission number to get the reset token.'
            })

        # Generate reset token
        token = secrets.token_urlsafe(48)
        expires = datetime.now() + timedelta(hours=1)

        cur.execute("""
            INSERT INTO student_password_resets (student_id, user_id, token, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (user_row['student_id'], user_row['id'], token, expires))
        db.connection.commit()
        cur.close()

        # Try to send email if mail is configured
        try:
            from utils.mail import send_email
            reset_url = request.host_url.rstrip('/') + url_for('student_portal.portal_login_page') + f'?reset_token={token}'
            send_email(
                to=user_row['email'],
                subject='VVM Student Portal — Password Reset',
                body=f"""Dear {user_row['student_name']},

A password reset was requested for your student portal account.

Your reset token is: {token}

Or click this link: {reset_url}

This token expires in 1 hour.

If you did not request this, please ignore this email.

— VVM Dharampur"""
            )
        except Exception as mail_err:
            print(f"Mail send failed (expected if not configured): {mail_err}")

        return jsonify({
            'status': 'success',
            'message': 'A password reset token has been generated. Check your email or contact the school admin with your admission number.',
            'show_reset_form': True
        })

    except Exception as e:
        try:
            db.connection.rollback()
        except:
            pass
        print(f"Forgot password error: {e}")
        return jsonify({'status': 'error',
                        'message': 'Server error. Please try again.'}), 500


@student_portal_bp.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    """Complete password reset with token."""
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not token or not new_password:
        return jsonify({'status': 'error', 'message': 'Token and new password required.'}), 400

    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400

    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters.'}), 400

    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT * FROM student_password_resets
            WHERE token=%s AND used=false AND expires_at > NOW()
        """, (token,))
        reset_row = cur.fetchone()

        if not reset_row:
            cur.close()
            return jsonify({'status': 'error',
                            'message': 'Invalid or expired reset token.'}), 400

        # Update password
        bcrypt = get_bcrypt()
        hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')

        cur.execute("UPDATE users SET password=%s WHERE id=%s",
                    (hashed, reset_row['user_id']))
        cur.execute("UPDATE student_password_resets SET used=true WHERE id=%s",
                    (reset_row['id'],))
        db.connection.commit()
        cur.close()

        return jsonify({
            'status': 'success',
            'message': 'Password reset successful! You can now login with your new password.'
        })

    except Exception as e:
        try:
            db.connection.rollback()
        except:
            pass
        print(f"Reset password error: {e}")
        return jsonify({'status': 'error', 'message': 'Server error.'}), 500


@student_portal_bp.route('/logout')
def portal_logout():
    """Logout student and redirect to portal login."""
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('student_portal.portal_login_page'))


# ══════════════════════════════════════════════════════════════
#  DASHBOARD DATA API ENDPOINTS
# ══════════════════════════════════════════════════════════════

@student_portal_bp.route('/api/profile')
@login_required
@student_api_required
def api_profile():
    """Get student profile data."""
    student = get_student_record(current_user.student_id)
    if not student:
        return jsonify({'status': 'error', 'message': 'Student not found.'}), 404

    return jsonify({
        'status': 'success',
        'student': {
            'id': student['id'],
            'admission_number': student['admission_number'],
            'student_name': student['student_name'],
            'father_name': student['father_name'],
            'mother_name': student['mother_name'],
            'mobile_number': student['mobile_number'],
            'email': current_user.email or '',
            'date_of_birth': str(student['date_of_birth']) if student['date_of_birth'] else '',
            'gender': student['gender'],
            'class': student['class'],
            'section': student['section'],
            'roll_number': student['roll_number'],
            'admission_date': str(student['admission_date']) if student['admission_date'] else '',
            'address': student['address'] or '',
            'aadhar_number': student['aadhar_number'] or '',
            'photo': student['photo'] or 'default_student.jpg',
            'status': student['status'],
        }
    })


@student_portal_bp.route('/api/profile/update', methods=['POST'])
@login_required
@student_api_required
def api_profile_update():
    """Update student contact details."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    mobile = data.get('mobile', '').strip()

    try:
        cur = db.connection.cursor()
        if email:
            cur.execute("UPDATE users SET email=%s WHERE id=%s",
                        (email, current_user.id))
        if mobile:
            cur.execute("UPDATE students SET mobile_number=%s WHERE id=%s",
                        (mobile, current_user.student_id))
        db.connection.commit()
        cur.close()

        return jsonify({'status': 'success', 'message': 'Profile updated successfully.'})
    except Exception as e:
        try:
            db.connection.rollback()
        except:
            pass
        return jsonify({'status': 'error', 'message': 'Update failed.'}), 500


@student_portal_bp.route('/api/change-password', methods=['POST'])
@login_required
@student_api_required
def api_change_password():
    """Change password for logged-in student."""
    data = request.get_json() or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    confirm_pw = data.get('confirm_password', '')

    if not current_pw or not new_pw:
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

    if new_pw != confirm_pw:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400

    if len(new_pw) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters.'}), 400

    try:
        cur = db.connection.cursor()
        cur.execute("SELECT password FROM users WHERE id=%s", (current_user.id,))
        row = cur.fetchone()
        cur.close()

        bcrypt = get_bcrypt()
        if not bcrypt.check_password_hash(row['password'], current_pw):
            return jsonify({'status': 'error', 'message': 'Current password is incorrect.'}), 401

        hashed = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        cur = db.connection.cursor()
        cur.execute("UPDATE users SET password=%s WHERE id=%s",
                    (hashed, current_user.id))
        db.connection.commit()
        cur.close()

        return jsonify({'status': 'success',
                        'message': 'Password changed successfully. Please login again.'})
    except Exception as e:
        try:
            db.connection.rollback()
        except:
            pass
        return jsonify({'status': 'error', 'message': 'Failed to change password.'}), 500


@student_portal_bp.route('/api/fees')
@login_required
@student_api_required
def api_fees():
    """Get fee summary + payment history for the logged-in student."""
    student = get_student_record(current_user.student_id)
    if not student:
        return jsonify({'status': 'error', 'message': 'Student not found.'}), 404

    try:
        cur = db.connection.cursor()

        # Payment history
        cur.execute("""
            SELECT id, receipt_number, month, year, months_paid,
                   monthly_fee, transport_fee, admission_fee, development_fee,
                   exam_fee, other_fee, late_fine, discount, total_amount,
                   payment_date, payment_mode
            FROM fee_payments
            WHERE student_id=%s
            ORDER BY year DESC, created_at DESC
        """, (student['id'],))
        payments = cur.fetchall()

        # Due months calculation
        try:
            from routes.fees import get_due_months
            due_months = get_due_months(student['id'], student['admission_date'])
        except:
            due_months = []

        monthly_fee = float(student['monthly_fee'] or 0)
        transport_fee = float(student['transport_fee'] or 0)
        total_monthly = monthly_fee + transport_fee
        total_paid = sum(float(p['total_amount'] or 0) for p in payments)
        total_due = len(due_months) * total_monthly

        # Format payments for JSON
        payment_list = []
        for p in payments:
            payment_list.append({
                'receipt_number': p['receipt_number'],
                'month': p['month'],
                'year': p['year'],
                'months_paid': p['months_paid'],
                'monthly_fee': float(p['monthly_fee'] or 0),
                'transport_fee': float(p['transport_fee'] or 0),
                'total_amount': float(p['total_amount'] or 0),
                'payment_date': str(p['payment_date']),
                'payment_mode': p['payment_mode'],
            })

        cur.close()

        return jsonify({
            'status': 'success',
            'fee_summary': {
                'monthly_fee': monthly_fee,
                'transport_fee': transport_fee,
                'total_monthly': total_monthly,
                'total_paid': total_paid,
                'total_due': total_due,
                'due_count': len(due_months),
                'due_months': due_months,
            },
            'payments': payment_list,
        })

    except Exception as e:
        print(f"Fee API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load fee data.'}), 500


@student_portal_bp.route('/api/attendance')
@login_required
@student_api_required
def api_attendance():
    """Get attendance data for a given month/year."""
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)

    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT attendance_date, status, remarks
            FROM student_attendance
            WHERE student_id=%s
              AND EXTRACT(MONTH FROM attendance_date)=%s
              AND EXTRACT(YEAR FROM attendance_date)=%s
            ORDER BY attendance_date
        """, (current_user.student_id, month, year))
        records = cur.fetchall()

        # Overall stats
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM student_attendance
            WHERE student_id=%s
            GROUP BY status
        """, (current_user.student_id,))
        stats_rows = cur.fetchall()
        cur.close()

        att_records = [{
            'date': str(r['attendance_date']),
            'day': r['attendance_date'].day,
            'status': r['status'],
            'remarks': r['remarks'] or ''
        } for r in records]

        stats = {r['status']: r['count'] for r in stats_rows}
        total = sum(stats.values())
        present = stats.get('Present', 0)
        percentage = round((present / total * 100), 1) if total > 0 else 0

        return jsonify({
            'status': 'success',
            'month': month,
            'year': year,
            'records': att_records,
            'stats': {
                'present': stats.get('Present', 0),
                'absent': stats.get('Absent', 0),
                'late': stats.get('Late', 0),
                'leave': stats.get('Leave', 0),
                'total': total,
                'percentage': percentage,
            }
        })

    except Exception as e:
        print(f"Attendance API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load attendance.'}), 500


@student_portal_bp.route('/api/performance')
@login_required
@student_api_required
def api_performance():
    """Get exam marks and performance analytics."""
    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT m.marks_obtained, m.grade, m.remarks,
                   e.exam_name, e.subject, e.max_marks, e.exam_date, e.class
            FROM marks m
            JOIN exam_schedules e ON e.id = m.exam_id
            WHERE m.student_id=%s
            ORDER BY e.exam_date DESC
        """, (current_user.student_id,))
        marks_rows = cur.fetchall()
        cur.close()

        marks_list = []
        subject_scores = {}

        for m in marks_rows:
            obtained = float(m['marks_obtained'] or 0)
            max_marks = float(m['max_marks'] or 100)
            percentage = round((obtained / max_marks * 100), 1) if max_marks > 0 else 0

            marks_list.append({
                'exam_name': m['exam_name'],
                'subject': m['subject'],
                'marks_obtained': obtained,
                'max_marks': max_marks,
                'percentage': percentage,
                'grade': m['grade'] or '',
                'exam_date': str(m['exam_date']),
            })

            # Aggregate by subject for analytics
            subj = m['subject']
            if subj not in subject_scores:
                subject_scores[subj] = {'total_obtained': 0, 'total_max': 0, 'count': 0}
            subject_scores[subj]['total_obtained'] += obtained
            subject_scores[subj]['total_max'] += max_marks
            subject_scores[subj]['count'] += 1

        # Calculate averages per subject
        subject_analytics = []
        for subj, data in subject_scores.items():
            avg_pct = round((data['total_obtained'] / data['total_max'] * 100), 1) if data['total_max'] > 0 else 0
            subject_analytics.append({
                'subject': subj,
                'average_percentage': avg_pct,
                'exams_taken': data['count'],
            })
        subject_analytics.sort(key=lambda x: x['average_percentage'], reverse=True)

        # Overall average
        total_obtained = sum(d['total_obtained'] for d in subject_scores.values())
        total_max = sum(d['total_max'] for d in subject_scores.values())
        overall_avg = round((total_obtained / total_max * 100), 1) if total_max > 0 else 0

        return jsonify({
            'status': 'success',
            'marks': marks_list,
            'subject_analytics': subject_analytics,
            'overall_average': overall_avg,
            'total_exams': len(marks_list),
        })

    except Exception as e:
        print(f"Performance API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load performance data.'}), 500


@student_portal_bp.route('/api/notices')
@login_required
@student_api_required
def api_notices():
    """Get notices relevant to the student."""
    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT id, title, content, category, priority, created_at
            FROM notices
            WHERE (target_role='all' OR target_role='student')
              AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)
            ORDER BY array_position(ARRAY['Urgent','Important','Normal'], priority),
                     created_at DESC
            LIMIT 20
        """)
        notices = cur.fetchall()
        cur.close()

        notice_list = [{
            'id': n['id'],
            'title': n['title'],
            'content': n['content'],
            'category': n['category'],
            'priority': n['priority'],
            'created_at': n['created_at'].strftime('%d %b %Y') if n['created_at'] else '',
        } for n in notices]

        return jsonify({'status': 'success', 'notices': notice_list})

    except Exception as e:
        print(f"Notices API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load notices.'}), 500


@student_portal_bp.route('/api/overview')
@login_required
@student_api_required
def api_overview():
    """Dashboard overview — quick stats for the welcome page."""
    student = get_student_record(current_user.student_id)
    if not student:
        return jsonify({'status': 'error', 'message': 'Student not found.'}), 404

    try:
        cur = db.connection.cursor()

        # Attendance stats
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM student_attendance
            WHERE student_id=%s
            GROUP BY status
        """, (student['id'],))
        att_stats = {r['status']: r['count'] for r in cur.fetchall()}
        att_total = sum(att_stats.values())
        att_pct = round((att_stats.get('Present', 0) / att_total * 100), 1) if att_total > 0 else 0

        # Due fees
        try:
            from routes.fees import get_due_months
            due_months = get_due_months(student['id'], student['admission_date'])
        except:
            due_months = []

        monthly_fee = float(student['monthly_fee'] or 0)
        transport_fee = float(student['transport_fee'] or 0)
        total_due = len(due_months) * (monthly_fee + transport_fee)

        # Recent notices
        cur.execute("""
            SELECT id, title, category, priority, created_at
            FROM notices
            WHERE (target_role='all' OR target_role='student')
              AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)
            ORDER BY created_at DESC
            LIMIT 3
        """)
        recent_notices = [{
            'id': n['id'],
            'title': n['title'],
            'category': n['category'],
            'priority': n['priority'],
            'created_at': n['created_at'].strftime('%d %b %Y') if n['created_at'] else '',
        } for n in cur.fetchall()]

        # Total exams
        cur.execute("""
            SELECT COUNT(*) as c FROM marks WHERE student_id=%s
        """, (student['id'],))
        total_exams = cur.fetchone()['c']

        # Overall average
        cur.execute("""
            SELECT AVG(m.marks_obtained * 100.0 / NULLIF(e.max_marks, 0)) as avg_pct
            FROM marks m
            JOIN exam_schedules e ON e.id = m.exam_id
            WHERE m.student_id=%s
        """, (student['id'],))
        avg_row = cur.fetchone()
        overall_avg = round(float(avg_row['avg_pct'] or 0), 1)

        cur.close()

        return jsonify({
            'status': 'success',
            'student_name': student['student_name'],
            'class': student['class'],
            'section': student['section'],
            'roll_number': student['roll_number'],
            'admission_number': student['admission_number'],
            'attendance_percentage': att_pct,
            'total_due': total_due,
            'due_months_count': len(due_months),
            'total_exams': total_exams,
            'overall_average': overall_avg,
            'recent_notices': recent_notices,
        })

    except Exception as e:
        print(f"Overview API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load overview.'}), 500


@student_portal_bp.route('/api/chat', methods=['POST'])
@login_required
@student_api_required
def api_chat():
    """AI Mentor — powered by Gemini, class-aware responses."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'status': 'error', 'message': 'Message is required.'}), 400

    student = get_student_record(current_user.student_id)
    class_level = student['class'] if student else '5'

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({
            'status': 'success',
            'reply': "The AI Mentor is not configured yet. Please contact the school administrator."
        })

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')

        prompt = f"""
        You are a friendly, helpful school AI tutor for Vivekanand Vidya Mandir Dharampur.
        The student asking the question is in Class {class_level} (approximate age: {int(class_level) + 5 if class_level.isdigit() else 10} years old).
        Student's name: {student['student_name'] if student else 'Student'}

        Rules:
        1. Keep the answer VERY simple and easy to understand.
        2. Do not use overly advanced vocabulary or complex college-level concepts.
        3. Explain the concept specifically tailored to a Class {class_level} student's understanding.
        4. Do not provide links or formatting other than bolding important words.
        5. Keep the response concise, maximum 3-4 short paragraphs.
        6. You can help with: homework, doubts, concept explanation, career guidance, exam preparation.
        7. Be encouraging and supportive.

        Student's Question: {message}
        """

        response = model.generate_content(prompt)

        return jsonify({
            'status': 'success',
            'reply': response.text
        })
    except Exception as e:
        print(f"AI Mentor error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'AI Mentor is currently unavailable. Please try again later.'
        })
