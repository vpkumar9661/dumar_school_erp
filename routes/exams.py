from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import db
from auth.decorators import permission_required
from datetime import date

exams_bp = Blueprint('exams', __name__)
CLASSES = ['Nursery','LKG','UKG','1','2','3','4','5','6','7','8','9','10','11','12']

@exams_bp.route('/')
@login_required
def schedule():
    cls = request.args.get('class','')
    cur = db.connection.cursor()
    if cls:
        cur.execute("SELECT * FROM exam_schedules WHERE class=%s ORDER BY exam_date,start_time", (cls,))
    else:
        cur.execute("SELECT * FROM exam_schedules ORDER BY exam_date,start_time")
    exams = cur.fetchall(); cur.close()
    return render_template('exams/schedule.html',
        exams=exams, classes=CLASSES, sel_class=cls,
        today=date.today().strftime('%Y-%m-%d'))

@exams_bp.route('/add', methods=['POST'])
@login_required
@permission_required('manage_exams')
def add():
    f = request.form
    cur = db.connection.cursor()
    cur.execute("""INSERT INTO exam_schedules
                   (exam_name,class,subject,exam_date,start_time,end_time,max_marks,room_number)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (f['exam_name'],f['class'],f['subject'],f['exam_date'],
                 f.get('start_time') or None, f.get('end_time') or None,
                 int(f.get('max_marks',100)), f.get('room_number','')))
    db.connection.commit(); cur.close()
    flash('Exam schedule added!', 'success')
    return redirect(url_for('exams.schedule'))

@exams_bp.route('/edit/<int:eid>', methods=['GET','POST'])
@login_required
@permission_required('manage_exams')
def edit(eid):
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM exam_schedules WHERE id=%s", (eid,))
    exam = cur.fetchone()
    if request.method == 'POST':
        f = request.form
        cur.execute("""UPDATE exam_schedules SET exam_name=%s,class=%s,subject=%s,
                       exam_date=%s,start_time=%s,end_time=%s,max_marks=%s,room_number=%s
                       WHERE id=%s""",
                    (f['exam_name'],f['class'],f['subject'],f['exam_date'],
                     f.get('start_time') or None, f.get('end_time') or None,
                     int(f.get('max_marks',100)), f.get('room_number',''), eid))
        db.connection.commit(); cur.close()
        flash('Exam updated!', 'success')
        return redirect(url_for('exams.schedule'))
    cur.close()
    return render_template('exams/edit.html', exam=exam, classes=CLASSES)

@exams_bp.route('/delete/<int:eid>', methods=['POST'])
@login_required
@permission_required('manage_exams')
def delete(eid):
    cur = db.connection.cursor()
    cur.execute("DELETE FROM exam_schedules WHERE id=%s", (eid,))
    db.connection.commit(); cur.close()
    flash('Exam deleted.', 'success')
    return redirect(url_for('exams.schedule'))

@exams_bp.route('/marks/<int:eid>', methods=['GET','POST'])
@login_required
@permission_required('manage_exams')
def marks_entry(eid):
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM exam_schedules WHERE id=%s", (eid,))
    exam = cur.fetchone()
    if not exam: flash('Exam not found.','danger'); cur.close(); return redirect(url_for('exams.schedule'))
    cur.execute("""SELECT s.*, m.marks_obtained, m.grade
                   FROM students s
                   LEFT JOIN marks m ON m.student_id=s.id AND m.exam_id=%s
                   WHERE s.class=%s AND s.status='Active'
                   ORDER BY s.roll_number""", (eid, exam['class']))
    students = cur.fetchall()
    if request.method == 'POST':
        for s in students:
            mo = request.form.get(f"marks_{s['id']}")
            if mo is not None:
                mo = float(mo)
                max_m = float(exam['max_marks'])
                pct = (mo/max_m*100) if max_m > 0 else 0
                grade = ('A+' if pct>=90 else 'A' if pct>=80 else 'B+' if pct>=70
                         else 'B' if pct>=60 else 'C' if pct>=50 else 'D' if pct>=40 else 'F')
                cur.execute("""INSERT INTO marks (student_id,exam_id,marks_obtained,grade,entered_by)
                               VALUES (%s,%s,%s,%s,%s)
                               ON CONFLICT (student_id, exam_id) DO UPDATE SET
                               marks_obtained=EXCLUDED.marks_obtained,
                               grade=EXCLUDED.grade,
                               entered_by=EXCLUDED.entered_by""",
                            (s['id'], eid, mo, grade, current_user.id))
        db.connection.commit()
        flash('Marks saved!', 'success')
        return redirect(url_for('exams.marks_entry', eid=eid))
    cur.close()
    return render_template('exams/marks_entry.html', exam=exam, students=students)
