"""Student / Parent Portal — view-only access (PostgreSQL)"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from db import db
from datetime import datetime, date

portal_bp = Blueprint('portal', __name__)
MONTHS = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']

def _get_student():
    """Return the student row linked to current_user, or None."""
    sid = current_user.student_id
    if not sid: return None
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    row = cur.fetchone(); cur.close()
    return row

@portal_bp.route('/')
@login_required
def index():
    student = _get_student()
    if not student:
        return render_template('portal/no_student.html')
    cur = db.connection.cursor()
    
    # Recent Payments
    cur.execute("""SELECT * FROM fee_payments WHERE student_id=%s
                   ORDER BY created_at DESC LIMIT 5""", (student['id'],))
    recent_fees = cur.fetchall()
    
    # Total Paid Fee
    cur.execute("SELECT SUM(total_amount) AS total_paid FROM fee_payments WHERE student_id=%s", (student['id'],))
    fee_data = cur.fetchone()
    
    # Attendance Summary
    cur.execute("""SELECT status,COUNT(*) AS c FROM student_attendance
                   WHERE student_id=%s GROUP BY status""", (student['id'],))
    att_summary = {r['status']: r['c'] for r in cur.fetchall()}
    
    # Upcoming Exams
    cur.execute("""SELECT subject, exam_date, start_time, max_marks
                   FROM exam_schedules WHERE class=%s AND exam_date >= %s
                   ORDER BY exam_date ASC""", (student['class'], date.today()))
    exams = cur.fetchall()
    
    # Notices
    cur.execute("""SELECT * FROM notices
                   WHERE (target_role='all' OR target_role=%s)
                   AND (expires_at IS NULL OR expires_at >= %s)
                   ORDER BY array_position(ARRAY['Urgent','Important','Normal'], priority), created_at DESC
                   LIMIT 5""", (current_user.role, date.today()))
    notices = cur.fetchall(); cur.close()
    
    return render_template('portal/index.html',
        student=student, recent_fees=recent_fees, fee_data=fee_data,
        att_summary=att_summary, exams=exams, notices=notices)

@portal_bp.route('/fees')
@login_required
def fees():
    student = _get_student()
    if not student: return render_template('portal/no_student.html')
    cur = db.connection.cursor()
    cur.execute("""SELECT * FROM fee_payments WHERE student_id=%s
                   ORDER BY year DESC, created_at DESC""", (student['id'],))
    payments = cur.fetchall()
    now = datetime.now()
    cur.execute("""SELECT id FROM fee_payments
                   WHERE student_id=%s AND EXTRACT(MONTH FROM payment_date)=%s AND EXTRACT(YEAR FROM payment_date)=%s""",
                (student['id'], now.month, now.year))
    current_paid = bool(cur.fetchone()); cur.close()
    return render_template('portal/fees.html',
        student=student, payments=payments, current_paid=current_paid)

@portal_bp.route('/attendance')
@login_required
def attendance():
    student = _get_student()
    if not student: return render_template('portal/no_student.html')
    import calendar
    now = datetime.now()
    month = int(request.args.get('month', now.month))
    year  = int(request.args.get('year',  now.year))
    cur = db.connection.cursor()
    cur.execute("""SELECT attendance_date, status FROM student_attendance
                   WHERE student_id=%s AND EXTRACT(MONTH FROM attendance_date)=%s AND EXTRACT(YEAR FROM attendance_date)=%s
                   ORDER BY attendance_date""", (student['id'], month, year))
    records = cur.fetchall(); cur.close()
    return render_template('portal/attendance.html',
        student=student, records=records, sel_month=month, sel_year=year,
        months=list(range(1,13)), years=range(2020, now.year+2))

@portal_bp.route('/results')
@login_required
def results():
    student = _get_student()
    if not student: return render_template('portal/no_student.html')
    cur = db.connection.cursor()
    cur.execute("""SELECT m.*, e.exam_name, e.subject, e.max_marks, e.exam_date
                   FROM marks m JOIN exam_schedules e ON e.id=m.exam_id
                   WHERE m.student_id=%s ORDER BY e.exam_date DESC""", (student['id'],))
    marks_list = cur.fetchall(); cur.close()
    
    # Calculate overall performance percentage
    total_obtained = sum(float(m['marks_obtained']) for m in marks_list)
    total_max = sum(float(m['max_marks']) for m in marks_list)
    overall_pct = round((total_obtained / total_max) * 100, 1) if total_max > 0 else 0
    
    return render_template('portal/results.html',
        student=student, results=marks_list, overall_pct=overall_pct)

