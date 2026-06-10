"""
Dashboard — Role-based views (PostgreSQL/Supabase)
"""
from flask import Blueprint, render_template, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from db import db
from datetime import datetime, date, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


def get_setting(key, default=''):
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_value FROM settings WHERE setting_key=%s", (key,))
        row = cur.fetchone(); cur.close()
        return row['setting_value'] if row else default
    except Exception:
        return default


@dashboard_bp.route('/dashboard')
@login_required
def index():
    if current_user.role in ('student', 'parent'):
        return redirect(url_for('portal.index'))

    now   = datetime.now()
    month = now.strftime('%B')
    year  = now.year
    today = date.today()
    cur   = db.connection.cursor()

    # ── Combined Core Stats (Single DB network round-trip instead of 8 separate ones) ──
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM students WHERE status='Active') AS total_students,
            (SELECT COUNT(*) FROM teachers WHERE status='Active') AS total_teachers,
            (SELECT COALESCE(SUM(monthly_fee + transport_fee), 0) FROM students WHERE status='Active') AS fee_expected,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments WHERE month=%s AND year=%s) AS fee_received,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments) AS total_income,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments WHERE payment_date=%s) AS today_collection,
            (SELECT COUNT(*) FROM fee_payments WHERE payment_date=%s) AS today_count,
            (SELECT COUNT(*) FROM teachers t WHERE status='Active' AND NOT EXISTS (
                SELECT 1 FROM salary_payments sp WHERE sp.teacher_id=t.id AND sp.month=%s AND sp.year=%s
            )) AS pending_salaries
    """, (month, year, today, today, month, year))
    stats = cur.fetchone()

    total_students = stats['total_students']
    total_teachers = stats['total_teachers']
    fee_expected   = float(stats['fee_expected'])
    fee_received   = float(stats['fee_received'])
    fee_pending    = max(fee_expected - fee_received, 0)
    total_income   = float(stats['total_income'])
    today_collection = float(stats['today_collection'])
    today_count      = stats['today_count']
    pending_salaries = stats['pending_salaries']

    # ── Last 6 months chart ───────────────────────────────────
    cur.execute("""
        SELECT month, year, SUM(total_amount) AS amount
        FROM fee_payments
        GROUP BY year, month
        ORDER BY year DESC,
            array_position(ARRAY['January','February','March','April','May','June',
                  'July','August','September','October','November','December'], month) DESC
        LIMIT 6
    """)
    monthly_rows  = list(reversed(cur.fetchall()))
    chart_labels  = [f"{r['month'][:3]} {str(r['year'])[2:]}" for r in monthly_rows]
    chart_amounts = [float(r['amount']) for r in monthly_rows]
    avg_fee       = fee_expected
    chart_expected= [avg_fee] * len(chart_labels)
    chart_pending = [max(avg_fee - amt, 0) for amt in chart_amounts]

    # ── Class-wise ────────────────────────────────────────────
    cur.execute("""
        SELECT class, COUNT(*) AS cnt FROM students
        WHERE status='Active' GROUP BY class ORDER BY class
    """)
    class_rows   = cur.fetchall()
    class_labels = [r['class'] for r in class_rows]
    class_counts = [r['cnt']   for r in class_rows]

    # ── Attendance today ──────────────────────────────────────
    cur.execute("""
        SELECT status, COUNT(*) AS c FROM student_attendance
        WHERE attendance_date=%s GROUP BY status
    """, (today,))
    att = {r['status']: r['c'] for r in cur.fetchall()}

    # ── Recent Transactions ───────────────────────────────────
    cur.execute("""
        SELECT fp.receipt_number, fp.payment_date, fp.total_amount,
               fp.month, fp.year, fp.months_paid, fp.payment_mode,
               s.student_name, s.class, s.section, s.admission_number
        FROM fee_payments fp
        JOIN students s ON s.id = fp.student_id
        ORDER BY fp.created_at DESC LIMIT 8
    """)
    recent_txn = cur.fetchall()

    # ── Recent Activity ───────────────────────────────────────
    cur.execute("""
        SELECT 'fee' AS type, fp.created_at AS ts,
               CONCAT('Fee collected from ', s.student_name) AS desc_text,
               CONCAT('₹', ROUND(fp.total_amount,0)) AS meta
        FROM fee_payments fp JOIN students s ON s.id=fp.student_id
        ORDER BY fp.created_at DESC LIMIT 4
    """)
    fee_activity = cur.fetchall()

    cur.execute("""
        SELECT 'student' AS type, s.created_at AS ts,
               CONCAT('New admission: ', s.student_name) AS desc_text,
               CONCAT('Class ', s.class, '-', s.section) AS meta
        FROM students s ORDER BY s.created_at DESC LIMIT 3
    """)
    student_activity = cur.fetchall()

    # ── Fee Defaulters ────────────────────────────────────────
    cur.execute("""
        SELECT s.student_name, s.admission_number, s.class, s.section,
               s.monthly_fee, s.transport_fee
        FROM students s WHERE s.status='Active'
        AND (
            SELECT COUNT(DISTINCT CONCAT(fp.month,'_',fp.year))
            FROM fee_payments fp WHERE fp.student_id = s.id
        ) < (
            (DATE_PART('year', CURRENT_DATE) - DATE_PART('year', s.admission_date)) * 12
            + (DATE_PART('month', CURRENT_DATE) - DATE_PART('month', s.admission_date)) + 1
        ) - 1
        LIMIT 5
    """)
    fee_defaulters = cur.fetchall()

    # ── Latest Notices ────────────────────────────────────────
    cur.execute("""
        SELECT * FROM notices
        WHERE (expires_at IS NULL OR expires_at >= %s)
        ORDER BY array_position(ARRAY['Urgent','Important','Normal'], priority), created_at DESC
        LIMIT 3
    """, (today,))
    latest_notices = cur.fetchall()

    # ── Weekly trend ──────────────────────────────────────────
    cur.execute("""
        SELECT payment_date AS day, SUM(total_amount) AS amt
        FROM fee_payments
        WHERE payment_date >= %s
        GROUP BY payment_date ORDER BY day
    """, (today - timedelta(days=6),))
    week_rows   = {str(r['day']): float(r['amt']) for r in cur.fetchall()}
    week_labels = [(today - timedelta(days=i)).strftime('%a') for i in range(6,-1,-1)]
    week_data   = [week_rows.get(str(today - timedelta(days=i)), 0) for i in range(6,-1,-1)]

    cur.close()

    collection_pct = round((fee_received / fee_expected * 100) if fee_expected > 0 else 0, 1)

    return render_template('dashboard.html',
        role=current_user.role,
        school_name=get_setting('school_name', 'VVM Dharampur'),
        total_students=total_students,
        total_teachers=total_teachers,
        fee_expected=fee_expected,
        fee_received=fee_received,
        fee_pending=fee_pending,
        total_income=total_income,
        today_collection=today_collection,
        today_count=today_count,
        collection_pct=collection_pct,
        chart_labels=chart_labels,
        chart_amounts=chart_amounts,
        chart_expected=chart_expected,
        chart_pending=chart_pending,
        class_labels=class_labels,
        class_counts=class_counts,
        att_present=att.get('Present', 0),
        att_absent=att.get('Absent', 0),
        att_late=att.get('Late', 0),
        pending_salaries=pending_salaries,
        recent_txn=recent_txn,
        fee_activity=fee_activity,
        student_activity=student_activity,
        fee_defaulters=fee_defaulters,
        latest_notices=latest_notices,
        week_labels=week_labels,
        week_data=week_data,
        current_month=month,
        current_year=year,
    )


@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    now = datetime.now()
    cur = db.connection.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE status='Active'")
    students = cur.fetchone()['c']
    cur.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS r FROM fee_payments
        WHERE month=%s AND year=%s
    """, (now.strftime('%B'), now.year))
    received = float(cur.fetchone()['r'])
    cur.execute("""
        SELECT COALESCE(SUM(monthly_fee+transport_fee),0) AS e
        FROM students WHERE status='Active'
    """)
    expected = float(cur.fetchone()['e'])
    cur.close()
    return jsonify({
        'students':       students,
        'fee_received':   received,
        'fee_pending':    max(expected - received, 0),
        'collection_pct': round(received / expected * 100 if expected > 0 else 0, 1)
    })


@dashboard_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('dashboard.index'))
    abort(403)

@dashboard_bp.route('/staff')
@login_required
def staff_dashboard():
    if current_user.role in ('admin', 'accountant', 'teacher'):
        return redirect(url_for('dashboard.index'))
    abort(403)

@dashboard_bp.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role == 'teacher':
        return redirect(url_for('dashboard.index'))
    abort(403)

@dashboard_bp.route('/accountant')
@login_required
def accountant_dashboard():
    if current_user.role == 'accountant':
        return redirect(url_for('dashboard.index'))
    abort(403)
