import os, base64, requests
from flask import Blueprint, render_template, request, make_response, current_app, flash, redirect, url_for
from flask_login import login_required
from db import db
from auth.decorators import permission_required
from utils.storage import get_public_url

idcard_bp = Blueprint('idcard', __name__)
CLASSES = ['Nursery','LKG','UKG','1','2','3','4','5','6','7','8','9','10','11','12']

def get_setting(key, default=''):
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_value FROM settings WHERE setting_key=%s",(key,))
        row = cur.fetchone(); cur.close()
        return row['setting_value'] if row else default
    except: return default

def photo_to_b64(photo_name, folder):
    from flask import current_app
    if not photo_name:
        photo_name = 'default_student.jpg'
    
    # 1. If it's the default student photo, read it locally from static/images
    if photo_name == 'default_student.jpg':
        path = os.path.join(current_app.static_folder, 'images', 'default_student.jpg')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
        return None
        
    # 2. Try fetching custom student photo from Supabase Storage (since files uploaded on admission are stored cloud-side)
    url = get_public_url('students', photo_name)
    if url.startswith('http'):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                ext = photo_name.rsplit('.', 1)[-1].lower()
                mime = 'png' if ext == 'png' else 'jpeg'
                return f"data:image/{mime};base64,{base64.b64encode(resp.content).decode()}"
        except Exception:
            pass
            
    # 3. Fallback: check if the file exists locally in uploads
    path = os.path.join(folder, photo_name)
    if os.path.exists(path):
        ext = photo_name.rsplit('.', 1)[-1].lower()
        mime = 'png' if ext == 'png' else 'jpeg'
        with open(path, 'rb') as f:
            return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
            
    # 4. Final fallback: read local default student photo from static/images
    default_path = os.path.join(current_app.static_folder, 'images', 'default_student.jpg')
    if os.path.exists(default_path):
        with open(default_path, 'rb') as f:
            return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
            
    return None

def logo_to_b64(app):
    path = os.path.join(app.static_folder, 'images', 'school_logo.png')
    if os.path.exists(path):
        with open(path,'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return None

@idcard_bp.route('/')
@login_required
@permission_required('manage_idcard')
def generate():
    cls = request.args.get('class','')
    ids = request.args.get('ids','')
    cur = db.connection.cursor()
    if ids:
        id_list = [int(x.strip()) for x in ids.split(',') if x.strip().isdigit()]
        if id_list:
            cur.execute("SELECT * FROM students WHERE id = ANY(%s) AND status='Active' ORDER BY class,section,roll_number", (id_list,))
        else:
            cur.execute("SELECT * FROM students WHERE status='Active' ORDER BY class,section,roll_number")
    elif cls:
        cur.execute("SELECT * FROM students WHERE class=%s AND status='Active' ORDER BY section,roll_number", (cls,))
    else:
        cur.execute("SELECT * FROM students WHERE status='Active' ORDER BY class,section,roll_number")
    students = cur.fetchall(); cur.close()
    folder = current_app.config['UPLOAD_FOLDER']
    for s in students: s['photo_b64'] = photo_to_b64(s['photo'], folder)
    return render_template('idcard/generate.html',
        students=students, classes=CLASSES, sel_class=cls,
        school_name=get_setting('school_name','VVM Dharampur'),
        school_phone=get_setting('school_phone',''),
        school_address=get_setting('school_address',''),
        school_email=get_setting('school_email',''),
        current_session=get_setting('current_session','2024-25'),
        school_logo_b64=logo_to_b64(current_app))

@idcard_bp.route('/pdf')
@login_required
@permission_required('manage_idcard')
def pdf():
    try:
        from weasyprint import HTML
        cls = request.args.get('class','')
        ids = request.args.get('ids','')
        cur = db.connection.cursor()
        if ids:
            id_list = [int(x.strip()) for x in ids.split(',') if x.strip().isdigit()]
            if id_list:
                cur.execute("SELECT * FROM students WHERE id = ANY(%s) AND status='Active' ORDER BY class,section,roll_number", (id_list,))
            else:
                cur.execute("SELECT * FROM students WHERE status='Active' ORDER BY class,section,roll_number")
        elif cls:
            cur.execute("SELECT * FROM students WHERE class=%s AND status='Active' ORDER BY section,roll_number",(cls,))
        else:
            cur.execute("SELECT * FROM students WHERE status='Active' ORDER BY class,section,roll_number")
        students = cur.fetchall(); cur.close()
        folder = current_app.config['UPLOAD_FOLDER']
        for s in students: s['photo_b64'] = photo_to_b64(s['photo'], folder)
        html_str = render_template('idcard/generate.html',
            students=students, classes=CLASSES, sel_class=cls,
            school_name=get_setting('school_name','VVM Dharampur'),
            school_phone=get_setting('school_phone',''),
            school_address=get_setting('school_address',''),
            school_email=get_setting('school_email',''),
            current_session=get_setting('current_session','2024-25'), pdf_mode=True,
            school_logo_b64=logo_to_b64(current_app))
        pdf_bytes = HTML(string=html_str, base_url=current_app.root_path).write_pdf()
        resp = make_response(pdf_bytes)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'attachment; filename=IDCards_{cls or "All"}.pdf'
        return resp
    except ImportError:
        flash('WeasyPrint not installed.','warning')
        return redirect(url_for('idcard.generate'))
