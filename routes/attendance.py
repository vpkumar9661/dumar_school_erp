from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import db
from auth.decorators import permission_required
from datetime import date, datetime

attendance_bp = Blueprint('attendance', __name__)
CLASSES = ['Nursery','LKG','UKG','1','2','3','4','5','6','7','8','9','10','11','12']

@attendance_bp.route('/students', methods=['GET','POST'])
@login_required
@permission_required('manage_attendance')
def students():
    sel_class = request.args.get('class', CLASSES[0])
    sel_date  = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    cur = db.connection.cursor()
    if request.method == 'POST':
        att_date    = request.form.get('attendance_date')
        cls         = request.form.get('class')
        student_ids = request.form.getlist('student_ids')
        for sid in student_ids:
            status  = request.form.get(f'status_{sid}','Absent')
            remarks = request.form.get(f'remarks_{sid}','')
            cur.execute("""INSERT INTO student_attendance (student_id,attendance_date,status,remarks,marked_by)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (student_id, attendance_date) DO UPDATE SET
                           status=EXCLUDED.status,remarks=EXCLUDED.remarks,marked_by=EXCLUDED.marked_by""",
                        (sid, att_date, status, remarks, current_user.id))
        db.connection.commit()
        flash(f'Attendance saved for Class {cls}!', 'success')
        cur.close()
        return redirect(url_for('attendance.students', **{'class':cls,'date':att_date}))
    cur.execute("""SELECT s.*,a.status AS att_status,a.remarks AS att_remarks
                   FROM students s
                   LEFT JOIN student_attendance a
                       ON a.student_id=s.id AND a.attendance_date=%s
                   WHERE s.class=%s AND s.status='Active'
                   ORDER BY s.roll_number,s.student_name""", (sel_date, sel_class))
    students = cur.fetchall()
    cur.execute("""SELECT status,COUNT(*) AS c FROM student_attendance
                   WHERE attendance_date=%s AND student_id IN
                   (SELECT id FROM students WHERE class=%s AND status='Active')
                   GROUP BY status""", (sel_date, sel_class))
    stats = {r['status']:r['c'] for r in cur.fetchall()}
    cur.close()
    return render_template('attendance/students.html',
        students=students, classes=CLASSES,
        sel_class=sel_class, sel_date=sel_date, stats=stats)

@attendance_bp.route('/teachers', methods=['GET','POST'])
@login_required
@permission_required('manage_attendance')
def teachers():
    sel_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    cur = db.connection.cursor()
    if request.method == 'POST':
        att_date    = request.form.get('attendance_date')
        teacher_ids = request.form.getlist('teacher_ids')
        for tid in teacher_ids:
            status  = request.form.get(f'status_{tid}','Absent')
            remarks = request.form.get(f'remarks_{tid}','')
            cur.execute("""INSERT INTO teacher_attendance (teacher_id,attendance_date,status,remarks)
                           VALUES (%s,%s,%s,%s)
                           ON CONFLICT (teacher_id, attendance_date) DO UPDATE SET
                           status=EXCLUDED.status,remarks=EXCLUDED.remarks""",
                        (tid, att_date, status, remarks))
        db.connection.commit()
        flash(f'Teacher attendance saved!', 'success')
        cur.close()
        return redirect(url_for('attendance.teachers', date=att_date))
    cur.execute("""SELECT t.*,a.status AS att_status,a.remarks AS att_remarks
                   FROM teachers t
                   LEFT JOIN teacher_attendance a
                       ON a.teacher_id=t.id AND a.attendance_date=%s
                   WHERE t.status='Active' ORDER BY t.teacher_name""", (sel_date,))
    teachers = cur.fetchall()
    cur.execute("""SELECT status,COUNT(*) AS c FROM teacher_attendance
                   WHERE attendance_date=%s GROUP BY status""", (sel_date,))
    stats = {r['status']:r['c'] for r in cur.fetchall()}; cur.close()
    return render_template('attendance/teachers.html',
        teachers=teachers, sel_date=sel_date, stats=stats)

@attendance_bp.route('/report')
@login_required
@permission_required('manage_attendance')
def report():
    cls   = request.args.get('class','1')
    month = int(request.args.get('month', date.today().month))
    year  = int(request.args.get('year',  date.today().year))
    cur = db.connection.cursor()
    cur.execute("""SELECT s.id,s.student_name,s.roll_number,
                          COUNT(CASE WHEN a.status='Present' THEN 1 END) AS present_days,
                          COUNT(CASE WHEN a.status='Absent'  THEN 1 END) AS absent_days,
                          COUNT(CASE WHEN a.status='Late'    THEN 1 END) AS late_days,
                          COUNT(a.id) AS total_days
                   FROM students s
                   LEFT JOIN student_attendance a
                       ON a.student_id=s.id
                       AND EXTRACT(MONTH FROM a.attendance_date)=%s
                       AND EXTRACT(YEAR FROM a.attendance_date)=%s
                   WHERE s.class=%s AND s.status='Active'
                   GROUP BY s.id, s.student_name, s.roll_number ORDER BY s.roll_number""", (month, year, cls))
    report_data = cur.fetchall(); cur.close()
    return render_template('attendance/report.html',
        report_data=report_data, classes=CLASSES,
        sel_class=cls, sel_month=month, sel_year=year,
        months=list(range(1,13)), years=range(2020, date.today().year+2))
