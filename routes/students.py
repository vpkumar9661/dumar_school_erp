import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from db import db
from auth.decorators import permission_required
from datetime import datetime, date
from utils.storage import upload_to_supabase, delete_from_supabase

students_bp = Blueprint('students', __name__)
CLASSES   = ['Nursery','LKG','UKG','1','2','3','4','5','6','7','8','9','10','11','12']
SECTIONS  = ['A','B','C','D','E']
TRANSPORT = ['None','0-2','2-5','5-10','10+']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_transport_fee(slab):
    if not slab or slab == 'None': return 0.0
    cur = db.connection.cursor()
    cur.execute("SELECT fee FROM transport_slabs WHERE distance_slab=%s", (slab,))
    row = cur.fetchone(); cur.close()
    return float(row['fee']) if row else 0.0

def next_admission_number():
    cur = db.connection.cursor()
    cur.execute("SELECT MAX(CAST(SUBSTRING(admission_number,4) AS INTEGER)) AS mx FROM students")
    row = cur.fetchone(); cur.close()
    return f"ADM{((row['mx'] or 0)+1):04d}"

@students_bp.route('/')
@login_required
def list():
    if not (current_user.has_permission('manage_students') or current_user.has_permission('view_students')):
        flash('Permission denied.', 'danger'); return redirect(url_for('dashboard.index'))
    search = request.args.get('search','').strip()
    cls    = request.args.get('class','').strip()
    sec    = request.args.get('section','').strip()
    status = request.args.get('status','Active').strip()
    q = "SELECT * FROM students WHERE 1=1"; p = []
    if search:
        q += " AND (student_name LIKE %s OR admission_number LIKE %s OR mobile_number LIKE %s)"
        like = f"%{search}%"; p += [like, like, like]
    if cls:    q += " AND class=%s";   p.append(cls)
    if sec:    q += " AND section=%s"; p.append(sec)
    if status: q += " AND status=%s";  p.append(status)
    q += " ORDER BY class, section, roll_number"
    cur = db.connection.cursor()
    cur.execute(q, p); students = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE status='Active'")
    total_active = cur.fetchone()['c']
    cur.close()
    return render_template('students/list.html',
        students=students, classes=CLASSES, sections=SECTIONS,
        search=search, sel_class=cls, sel_section=sec,
        sel_status=status, total_active=total_active)

@students_bp.route('/add', methods=['GET','POST'])
@login_required
@permission_required('manage_students')
def add():
    if request.method == 'POST':
        f = request.form
        photo_name = 'default_student.jpg'
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.',1)[1].lower()
                photo_name = f"{uuid.uuid4().hex}.{ext}"
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_name)
                file.save(path)
                
                # Cloud backup
                success = upload_to_supabase(path, 'students', photo_name)
                if success:
                    try: os.remove(path)
                    except: pass
        transport_slab = f.get('transport_distance','None')
        transport_fee  = get_transport_fee(transport_slab)
        adm_no = f.get('admission_number') or next_admission_number()
        cur = db.connection.cursor()
        cur.execute("""
            INSERT INTO students
            (admission_number,student_name,photo,father_name,mother_name,
             aadhar_number,mobile_number,address,date_of_birth,gender,
             class,section,roll_number,admission_date,
             transport_distance,transport_fee,monthly_fee,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (adm_no, f['student_name'], photo_name,
              f['father_name'], f['mother_name'], f.get('aadhar_number',''),
              f['mobile_number'], f.get('address',''),
              f.get('date_of_birth') or None, f['gender'],
              f['class'], f['section'], f.get('roll_number') or None,
              f['admission_date'], transport_slab, transport_fee,
              f.get('monthly_fee',500), f.get('status','Active')))
        db.connection.commit(); cur.close()
        flash(f"Student '{f['student_name']}' added! Adm No: {adm_no}", 'success')
        return redirect(url_for('students.list'))
    return render_template('students/add.html',
        classes=CLASSES, sections=SECTIONS, transport_options=TRANSPORT,
        suggested_adm=next_admission_number(),
        today=datetime.now().strftime('%Y-%m-%d'))

@students_bp.route('/view/<int:sid>')
@login_required
def view(sid):
    if not (current_user.has_permission('manage_students') or current_user.has_permission('view_students')):
        flash('Permission denied.', 'danger'); return redirect(url_for('dashboard.index'))
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    student = cur.fetchone()
    if not student:
        flash('Student not found.', 'danger'); return redirect(url_for('students.list'))
    cur.execute("SELECT * FROM fee_payments WHERE student_id=%s ORDER BY created_at DESC LIMIT 12", (sid,))
    fee_history = cur.fetchall()
    cur.execute("SELECT status, COUNT(*) AS c FROM student_attendance WHERE student_id=%s GROUP BY status", (sid,))
    att = {r['status']: r['c'] for r in cur.fetchall()}
    cur.execute("SELECT m.*, e.exam_name, e.subject, e.max_marks FROM marks m JOIN exam_schedules e ON e.id=m.exam_id WHERE m.student_id=%s ORDER BY e.exam_date DESC LIMIT 10", (sid,))
    marks_list = cur.fetchall()
    from routes.fees import get_due_months
    due_months = get_due_months(sid, student['admission_date'])
    cur.close()
    return render_template('students/view.html',
        student=student, fee_history=fee_history,
        att=att, marks_list=marks_list, due_months=due_months)

@students_bp.route('/edit/<int:sid>', methods=['GET','POST'])
@login_required
@permission_required('manage_students')
def edit(sid):
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    student = cur.fetchone()
    if not student:
        flash('Student not found.', 'danger'); return redirect(url_for('students.list'))
    if request.method == 'POST':
        f = request.form
        photo_name = student['photo']
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                photo_name = f"{uuid.uuid4().hex}.{ext}"
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_name)
                file.save(path)
                
                # Cloud backup
                success = upload_to_supabase(path, 'students', photo_name)
                if success:
                    try: os.remove(path)
                    except: pass
        transport_slab = f.get('transport_distance','None')
        transport_fee  = get_transport_fee(transport_slab)
        cur.execute("""
            UPDATE students SET student_name=%s,photo=%s,father_name=%s,
            mother_name=%s,aadhar_number=%s,mobile_number=%s,address=%s,
            date_of_birth=%s,gender=%s,class=%s,section=%s,roll_number=%s,
            admission_date=%s,transport_distance=%s,transport_fee=%s,
            monthly_fee=%s,status=%s WHERE id=%s
        """, (f['student_name'], photo_name, f['father_name'], f['mother_name'],
              f.get('aadhar_number',''), f['mobile_number'], f.get('address',''),
              f.get('date_of_birth') or None, f['gender'], f['class'], f['section'],
              f.get('roll_number') or None, f['admission_date'],
              transport_slab, transport_fee, f.get('monthly_fee',500),
              f.get('status','Active'), sid))
        db.connection.commit(); cur.close()
        flash('Student updated!', 'success')
        return redirect(url_for('students.view', sid=sid))
    cur.close()
    return render_template('students/edit.html', student=student,
        classes=CLASSES, sections=SECTIONS, transport_options=TRANSPORT)

@students_bp.route('/delete/<int:sid>', methods=['POST'])
@login_required
@permission_required('manage_students')
def delete(sid):
    cur = db.connection.cursor()
    cur.execute("SELECT photo, student_name FROM students WHERE id=%s", (sid,))
    student = cur.fetchone()
    if student:
        if student['photo'] != 'default_student.jpg':
            delete_from_supabase('students', student['photo'])
        cur.execute("DELETE FROM students WHERE id=%s", (sid,))
        db.connection.commit()
        flash(f"Student '{student['student_name']}' deleted.", 'success')
    cur.close()
    return redirect(url_for('students.list'))
