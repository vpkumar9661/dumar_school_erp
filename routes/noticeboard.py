from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import db
from datetime import date

noticeboard_bp = Blueprint('noticeboard', __name__)

CATEGORIES = ['General','Academic','Admission','Exam','Event','Holiday']
PRIORITIES = ['Normal','Important','Urgent']

def ensure_is_public():
    try:
        cur = db.connection.cursor()
        cur.execute("ALTER TABLE notices ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT true")
        db.connection.commit(); cur.close()
    except Exception:
        try: db.connection.rollback()
        except: pass

@noticeboard_bp.route('/')
@login_required
def index():
    ensure_is_public()
    cat = request.args.get('category','')
    cur = db.connection.cursor()
    q = "SELECT n.* FROM notices n WHERE (n.expires_at IS NULL OR n.expires_at >= %s)"
    p = [date.today()]
    if current_user.role not in ('admin','teacher','accountant'):
        q += " AND (n.target_role='all' OR n.target_role=%s)"
        p.append(current_user.role)
    if cat: q += " AND n.category=%s"; p.append(cat)
    q += " ORDER BY array_position(ARRAY['Urgent','Important','Normal'], n.priority), n.created_at DESC"
    cur.execute(q, p); notices = cur.fetchall(); cur.close()
    return render_template('noticeboard/index.html',
        notices=notices, sel_category=cat, categories=CATEGORIES, priorities=PRIORITIES, today=date.today())

@noticeboard_bp.route('/add', methods=['POST'])
@login_required
def add():
    if current_user.role not in ('admin','teacher'):
        flash('Only admin/teacher can add notices.', 'warning')
        return redirect(url_for('noticeboard.index'))
    ensure_is_public()
    f = request.form
    is_public_val = True if f.get('is_public') else False
    cur = db.connection.cursor()
    cur.execute("""INSERT INTO notices (title,content,category,priority,target_role,created_by,expires_at,is_public)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (f['title'], f['content'], f.get('category','General'),
         f.get('priority','Normal'), f.get('target_role','all'),
         current_user.id, f.get('expires_at') or None, is_public_val))
    db.connection.commit(); cur.close()
    flash('Notice published!', 'success')
    return redirect(url_for('noticeboard.index'))

@noticeboard_bp.route('/toggle_public/<int:nid>', methods=['POST'])
@login_required
def toggle_public(nid):
    if current_user.role not in ('admin','teacher'):
        flash('Only admin/teacher can toggle notice visibility.', 'warning')
        return redirect(url_for('noticeboard.index'))
    ensure_is_public()
    cur = db.connection.cursor()
    cur.execute("UPDATE notices SET is_public = NOT is_public WHERE id=%s", (nid,))
    db.connection.commit(); cur.close()
    flash('Notice public status updated!', 'success')
    return redirect(url_for('noticeboard.index'))

@noticeboard_bp.route('/edit/<int:nid>', methods=['GET','POST'])
@login_required
def edit(nid):
    if current_user.role not in ('admin','teacher'):
        flash('Only admin/teacher can edit notices.', 'warning')
        return redirect(url_for('noticeboard.index'))
    ensure_is_public()
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM notices WHERE id=%s", (nid,))
    notice = cur.fetchone()
    if not notice:
        flash('Notice not found.', 'danger'); cur.close()
        return redirect(url_for('noticeboard.index'))
    if request.method == 'POST':
        f = request.form
        is_public_val = True if f.get('is_public') else False
        cur.execute("""UPDATE notices SET title=%s,content=%s,category=%s,
                       priority=%s,target_role=%s,expires_at=%s,is_public=%s WHERE id=%s""",
            (f['title'], f['content'], f.get('category','General'),
             f.get('priority','Normal'), f.get('target_role','all'),
             f.get('expires_at') or None, is_public_val, nid))
        db.connection.commit(); cur.close()
        flash('Notice updated!', 'success')
        return redirect(url_for('noticeboard.index'))
    cur.close()
    return render_template('noticeboard/edit.html', notice=notice)

@noticeboard_bp.route('/delete/<int:nid>', methods=['POST'])
@login_required
def delete(nid):
    if current_user.role not in ('admin','teacher'):
        flash('Only admin/teacher can delete notices.', 'warning')
        return redirect(url_for('noticeboard.index'))
    cur = db.connection.cursor()
    cur.execute("DELETE FROM notices WHERE id=%s", (nid,))
    db.connection.commit(); cur.close()
    flash('Notice deleted.', 'success')
    return redirect(url_for('noticeboard.index'))
