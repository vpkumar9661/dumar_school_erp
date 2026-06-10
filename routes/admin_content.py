"""Admin Content Management — Gallery, Downloads, Enquiries (PostgreSQL)"""
import os, uuid
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, abort)
from flask_login import login_required, current_user
from db import db
from auth.decorators import admin_required
from werkzeug.utils import secure_filename
from utils.storage import upload_to_supabase, delete_from_supabase

admin_content_bp = Blueprint('admin_content', __name__)

def ensure_tables():
    """Ensure gallery/downloads/enquiries tables & notices.is_public exist."""
    try:
        cur = db.connection.cursor()
        cur.execute("ALTER TABLE notices ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT false")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gallery_photos (
                id SERIAL PRIMARY KEY,
                caption VARCHAR(255),
                filename VARCHAR(255) NOT NULL,
                category VARCHAR(30) DEFAULT 'Event',
                uploaded_by INT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public_downloads (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description VARCHAR(500),
                filename VARCHAR(255) NOT NULL,
                category VARCHAR(30) DEFAULT 'Form',
                is_active BOOLEAN DEFAULT true,
                download_count INT DEFAULT 0,
                uploaded_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admission_enquiries (
                id SERIAL PRIMARY KEY,
                student_name VARCHAR(200) NOT NULL,
                father_name VARCHAR(200),
                mobile VARCHAR(15) NOT NULL,
                email VARCHAR(200),
                class_applying VARCHAR(20),
                current_school VARCHAR(200),
                message TEXT,
                status VARCHAR(30) DEFAULT 'New',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.connection.commit(); cur.close()
    except Exception:
        try: db.connection.rollback()
        except: pass

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ('png','jpg','jpeg','gif','webp','pdf','doc','docx','xls','xlsx','ppt','pptx','zip')

GALLERY_CATS   = ['Event','Sports','Classroom','Cultural','Achievement','Other']
DOWNLOAD_CATS  = ['Form','Fee Structure','Calendar','Syllabus','Circular','Other']

# ── GALLERY ──────────────────────────────────────────────────

@admin_content_bp.route('/admin/gallery')
@login_required
def gallery_manage():
    if current_user.role not in ('admin', 'accountant', 'teacher'):
        abort(403)
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM gallery_photos ORDER BY created_at DESC")
    photos = cur.fetchall(); cur.close()
    return render_template('admin_content/gallery.html',
        photos=photos, categories=GALLERY_CATS)

@admin_content_bp.route('/admin/gallery/upload', methods=['POST'])
@login_required
@admin_required
def gallery_upload():
    ensure_tables()
    if 'photo' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('admin_content.gallery_manage'))
    file = request.files['photo']
    if not file or not file.filename:
        flash('No file selected.', 'warning')
        return redirect(url_for('admin_content.gallery_manage'))
    if not allowed_file(file.filename):
        flash('File type not allowed.', 'danger')
        return redirect(url_for('admin_content.gallery_manage'))
    ext = file.filename.rsplit('.', 1)[1].lower()
    fname = f"gallery_{uuid.uuid4().hex}.{ext}"
    if os.environ.get('VERCEL') == '1':
        folder = os.path.join('/tmp', 'uploads', 'gallery')
    else:
        folder = os.path.join(current_app.root_path, 'static', 'uploads', 'gallery')
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, fname))
    
    # Persistent storage via Supabase
    success = upload_to_supabase(os.path.join(folder, fname), 'gallery', fname)
    
    caption  = request.form.get('caption','')
    category = request.form.get('category','Event')
    cur = db.connection.cursor()
    cur.execute("""INSERT INTO gallery_photos (caption,filename,category,uploaded_by)
                   VALUES (%s,%s,%s,%s)""",
                (caption, fname, category, current_user.id))
    db.connection.commit(); cur.close()
    
    # Cleanup local file only if cloud upload succeeded
    if success:
        try: os.remove(os.path.join(folder, fname))
        except: pass
        flash('Photo uploaded successfully to cloud storage!', 'success')
    else:
        flash('Photo saved locally, but cloud backup failed. It may disappear later.', 'warning')
    
    return redirect(url_for('admin_content.gallery_manage'))

@admin_content_bp.route('/admin/gallery/toggle/<int:pid>', methods=['POST'])
@login_required
@admin_required
def gallery_toggle(pid):
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("UPDATE gallery_photos SET is_active = NOT is_active WHERE id=%s", (pid,))
    db.connection.commit(); cur.close()
    flash('Photo status updated.', 'success')
    return redirect(url_for('admin_content.gallery_manage'))

@admin_content_bp.route('/admin/gallery/delete/<int:pid>', methods=['POST'])
@login_required
@admin_required
def gallery_delete(pid):
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("SELECT filename FROM gallery_photos WHERE id=%s", (pid,))
    row = cur.fetchone()
    if row:
        delete_from_supabase('gallery', row['filename'])
        cur.execute("DELETE FROM gallery_photos WHERE id=%s", (pid,))
        db.connection.commit()
    cur.close()
    flash('Photo deleted.', 'success')
    return redirect(url_for('admin_content.gallery_manage'))

# ── DOWNLOADS ────────────────────────────────────────────────

@admin_content_bp.route('/admin/downloads')
@login_required
@admin_required
def downloads_manage():
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM public_downloads ORDER BY created_at DESC")
    downloads = cur.fetchall(); cur.close()
    return render_template('admin_content/downloads.html',
        items=downloads, categories=DOWNLOAD_CATS)

@admin_content_bp.route('/admin/downloads/upload', methods=['POST'])
@login_required
@admin_required
def downloads_upload():
    ensure_tables()
    if 'file' not in request.files:
        flash('No file.','warning')
        return redirect(url_for('admin_content.downloads_manage'))
    file = request.files['file']
    if not file or not file.filename:
        flash('No file.','warning')
        return redirect(url_for('admin_content.downloads_manage'))
    if not allowed_file(file.filename):
        flash('Type not allowed.','danger')
        return redirect(url_for('admin_content.downloads_manage'))
    ext = file.filename.rsplit('.',1)[1].lower()
    fname = f"dl_{uuid.uuid4().hex}.{ext}"
    if os.environ.get('VERCEL') == '1':
        folder = os.path.join('/tmp', 'uploads', 'downloads')
    else:
        folder = os.path.join(current_app.root_path, 'static', 'uploads', 'downloads')
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, fname))
    
    # Persistent storage via Supabase
    success = upload_to_supabase(os.path.join(folder, fname), 'downloads', fname)
    
    cur = db.connection.cursor()
    cur.execute("""INSERT INTO public_downloads (title,description,filename,category,uploaded_by)
                   VALUES (%s,%s,%s,%s,%s)""",
        (request.form.get('title',''), request.form.get('description',''),
         fname, request.form.get('category','Form'), current_user.id))
    db.connection.commit(); cur.close()
    
    # Cleanup local file only if cloud upload succeeded
    if success:
        try: os.remove(os.path.join(folder, fname))
        except: pass
        flash('File uploaded successfully to cloud storage!', 'success')
    else:
        flash('File saved locally, but cloud backup failed.', 'warning')
    
    return redirect(url_for('admin_content.downloads_manage'))

@admin_content_bp.route('/admin/downloads/toggle/<int:did>', methods=['POST'])
@login_required
@admin_required
def downloads_toggle(did):
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("UPDATE public_downloads SET is_active = NOT is_active WHERE id=%s", (did,))
    db.connection.commit(); cur.close()
    return redirect(url_for('admin_content.downloads_manage'))

@admin_content_bp.route('/admin/downloads/delete/<int:did>', methods=['POST'])
@login_required
@admin_required
def downloads_delete(did):
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("SELECT filename FROM public_downloads WHERE id=%s", (did,))
    row = cur.fetchone()
    if row:
        delete_from_supabase('downloads', row['filename'])
        cur.execute("DELETE FROM public_downloads WHERE id=%s", (did,))
        db.connection.commit()
    cur.close()
    flash('Download deleted.','success')
    return redirect(url_for('admin_content.downloads_manage'))

# ── ENQUIRIES ────────────────────────────────────────────────

@admin_content_bp.route('/admin/enquiries')
@login_required
@admin_required
def enquiries():
    ensure_tables()
    status_filter = request.args.get('status','')
    cur = db.connection.cursor()
    
    # Fetch counts grouped by status
    cur.execute("SELECT status, COUNT(*) as cnt FROM admission_enquiries GROUP BY status")
    rows = cur.fetchall()
    counts = {'New': 0, 'Contacted': 0, 'Accepted': 0, 'Rejected': 0, 'Admitted': 0, 'Not Interested': 0}
    for r in rows:
        st = r['status']
        if st in counts:
            counts[st] = r['cnt']

    if status_filter:
        cur.execute("SELECT * FROM admission_enquiries WHERE status=%s ORDER BY created_at DESC",(status_filter,))
    else:
        cur.execute("SELECT * FROM admission_enquiries ORDER BY created_at DESC")
    enqs = cur.fetchall(); cur.close()
    return render_template('admin_content/enquiries.html',
        enquiries=enqs, status_filter=status_filter, counts=counts)

@admin_content_bp.route('/admin/enquiries/update/<int:eid>', methods=['POST'])
@login_required
@admin_required
def enquiry_update(eid):
    ensure_tables()
    new_status = request.form.get('status','')
    notes      = request.form.get('notes','')
    cur = db.connection.cursor()
    
    # Fetch enquiry details first to get recipient address & student name
    cur.execute("SELECT * FROM admission_enquiries WHERE id=%s", (eid,))
    enquiry = cur.fetchone()
    
    if enquiry:
        cur.execute("UPDATE admission_enquiries SET status=%s,notes=%s WHERE id=%s",
                    (new_status, notes, eid))
        db.connection.commit()
        
        # Trigger email notification only on Accepted, Rejected, or Admitted
        if new_status in ['Accepted', 'Rejected', 'Admitted']:
            from utils.mail import send_status_email
            send_status_email(enquiry, new_status, notes)
            flash(f"Enquiry updated and notification email sent to {enquiry.get('email')}!", 'success')
        else:
            flash("Enquiry updated successfully.", 'success')
    else:
        flash("Enquiry record not found.", 'danger')
        
    cur.close()
    return redirect(url_for('admin_content.enquiries'))

@admin_content_bp.route('/admin/enquiries/delete/<int:eid>', methods=['POST'])
@login_required
@admin_required
def enquiry_delete(eid):
    ensure_tables()
    cur = db.connection.cursor()
    cur.execute("DELETE FROM admission_enquiries WHERE id=%s",(eid,))
    db.connection.commit(); cur.close()
    flash('Enquiry deleted.','success')
    return redirect(url_for('admin_content.enquiries'))
