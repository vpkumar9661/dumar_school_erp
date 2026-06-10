from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_bcrypt import Bcrypt
from db import db
from auth.decorators import permission_required, admin_required
from auth.models import ROLES

users_bp = Blueprint('users', __name__)

def get_bcrypt():
    from app import bcrypt
    return bcrypt

@users_bp.route('/')
@login_required
@admin_required
def list():
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM users ORDER BY role, username")
    users = cur.fetchall()
    
    # Fetch login stats for each user
    cur.execute("""
        SELECT username,
               COUNT(CASE WHEN status='success' THEN 1 END) AS total_logins,
               COUNT(CASE WHEN status='failed' THEN 1 END) AS failed_logins
        FROM login_logs
        GROUP BY username
    """)
    stats = {r['username']: r for r in cur.fetchall()}
    cur.close()
    
    return render_template('users/list.html', users=users, stats=stats)

@users_bp.route('/add', methods=['GET','POST'])
@login_required
@admin_required
def add():
    if request.method == 'POST':
        f = request.form
        bcrypt = get_bcrypt()
        hashed = bcrypt.generate_password_hash(f['password']).decode('utf-8')
        cur = db.connection.cursor()
        cur.execute("""INSERT INTO users (username,password,email,full_name,role,is_active,
                       student_id,teacher_id,created_by)
                       VALUES (%s,%s,%s,%s,%s,true,%s,%s,%s)""",
            (f['username'].lower().strip(), hashed, f.get('email',''),
             f['full_name'], f['role'],
             int(f.get('student_id',0)) if f.get('student_id') else None,
             int(f.get('teacher_id',0)) if f.get('teacher_id') else None,
             current_user.id))
        db.connection.commit(); cur.close()
        flash(f"User '{f['username']}' created!", 'success')
        return redirect(url_for('users.list'))
    cur = db.connection.cursor()
    cur.execute("SELECT id,student_name FROM students WHERE status='Active' ORDER BY student_name")
    students = cur.fetchall()
    cur.execute("SELECT id,teacher_name FROM teachers WHERE status='Active' ORDER BY teacher_name")
    teachers = cur.fetchall(); cur.close()
    return render_template('users/create.html', students=students, teachers=teachers, roles=ROLES)

@users_bp.route('/edit/<int:uid>', methods=['GET','POST'])
@login_required
@admin_required
def edit(uid):
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    if not user:
        flash('User not found.', 'danger'); cur.close()
        return redirect(url_for('users.list'))
    if request.method == 'POST':
        f = request.form
        cur.execute("""UPDATE users SET email=%s,full_name=%s,role=%s,
                       student_id=%s,teacher_id=%s WHERE id=%s""",
            (f.get('email',''), f['full_name'], f['role'],
             int(f.get('student_id',0)) if f.get('student_id') else None,
             int(f.get('teacher_id',0)) if f.get('teacher_id') else None, uid))
        if f.get('new_password'):
            bcrypt = get_bcrypt()
            hashed = bcrypt.generate_password_hash(f['new_password']).decode('utf-8')
            cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, uid))
        db.connection.commit(); cur.close()
        flash('User updated!', 'success')
        return redirect(url_for('users.list'))
    cur.execute("SELECT id,student_name FROM students WHERE status='Active' ORDER BY student_name")
    students = cur.fetchall()
    cur.execute("SELECT id,teacher_name FROM teachers WHERE status='Active' ORDER BY teacher_name")
    teachers = cur.fetchall(); cur.close()
    return render_template('users/edit.html', user=user, students=students, teachers=teachers, roles=ROLES)

@users_bp.route('/toggle/<int:uid>', methods=['POST'])
@login_required
@admin_required
def toggle(uid):
    cur = db.connection.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))
    db.connection.commit(); cur.close()
    flash('User status toggled!', 'success')
    return redirect(url_for('users.list'))

@users_bp.route('/delete/<int:uid>', methods=['POST'])
@login_required
@admin_required
def delete(uid):
    if uid == current_user.id:
        flash("You can't delete yourself!", 'danger')
        return redirect(url_for('users.list'))
    cur = db.connection.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    db.connection.commit(); cur.close()
    flash('User deleted.', 'success')
    return redirect(url_for('users.list'))

@users_bp.route('/audit')
@login_required
@admin_required
def audit_log():
    page = int(request.args.get('page',1))
    per  = 50; offset = (page-1)*per
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM login_logs ORDER BY created_at DESC LIMIT %s OFFSET %s",(per,offset))
    logs = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM login_logs")
    total = cur.fetchone()['c']; cur.close()
    return render_template('users/audit_log.html', logs=logs, page=page, per=per, total=total)
