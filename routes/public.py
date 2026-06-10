"""Public Website — Gallery, Downloads, Admission Enquiry (PostgreSQL)"""
import os
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, jsonify)
from db import db
from datetime import date
import google.generativeai as genai

public_bp = Blueprint('public', __name__)

def ensure_public_tables():
    """Ensure extra tables and columns exist (PostgreSQL-compatible)."""
    try:
        cur = db.connection.cursor()
        cur.execute("ALTER TABLE notices ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT true")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gallery_photos (
                id SERIAL PRIMARY KEY,
                caption VARCHAR(255),
                filename VARCHAR(255) NOT NULL,
                category VARCHAR(30) DEFAULT 'Event',
                uploaded_by INT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE gallery_photos ENABLE ROW LEVEL SECURITY;
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
            );
            ALTER TABLE public_downloads ENABLE ROW LEVEL SECURITY;
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
            );
            ALTER TABLE admission_enquiries ENABLE ROW LEVEL SECURITY;
        """)
        db.connection.commit(); cur.close()
    except Exception:
        try: db.connection.rollback()
        except: pass

def get_setting(key, default=''):
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_value FROM settings WHERE setting_key=%s",(key,))
        row = cur.fetchone(); cur.close()
        return row['setting_value'] if row else default
    except: return default

def get_all_settings():
    """Load every key-value pair from the settings table into a dict."""
    cfg = {}
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_key, setting_value FROM settings")
        for row in cur.fetchall():
            cfg[row['setting_key']] = row['setting_value']
        cur.close()
    except Exception:
        pass
    return cfg

@public_bp.route('/')
def index():
    ensure_public_tables()
    cfg = get_all_settings()
    cur = db.connection.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE status='Active'")
    total_students = cur.fetchone()['c']
    cfg['total_students'] = str(total_students)
    cur.execute("SELECT COUNT(*) AS c FROM teachers WHERE status='Active'")
    total_teachers = cur.fetchone()['c']
    cfg['total_teachers'] = str(total_teachers)
    # Public notices
    cur.execute("""SELECT id, title, content, category, priority, created_at
                   FROM notices WHERE is_public=true
                   AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)
                   ORDER BY array_position(ARRAY['Urgent','Important','Normal'], priority),
                            created_at DESC LIMIT 5""")
    notices = cur.fetchall()
    # All notices for marquee
    cur.execute("""SELECT id, title, category, priority FROM notices
                   WHERE is_public=true
                   AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)
                   ORDER BY array_position(ARRAY['Urgent','Important','Normal'], priority),
                            created_at DESC LIMIT 10""")
    all_notices = cur.fetchall()
    # Gallery
    cur.execute("SELECT * FROM gallery_photos WHERE is_active=true ORDER BY created_at DESC LIMIT 8")
    photos = cur.fetchall()
    # Downloads
    cur.execute("SELECT * FROM public_downloads WHERE is_active=true ORDER BY created_at DESC LIMIT 6")
    downloads = cur.fetchall()
    cur.close()
    return render_template('public/index.html',
        cfg=cfg,
        school_name=cfg.get('school_name','Vivekanand Vidya Mandir Dharampur'),
        school_address=cfg.get('school_address',''),
        school_phone=cfg.get('school_phone',''),
        school_email=cfg.get('school_email',''),
        total_students=total_students, total_teachers=total_teachers,
        notices=notices, all_notices=all_notices,
        gallery=photos, photos=photos, downloads=downloads)

@public_bp.route('/gallery')
def gallery():
    ensure_public_tables()
    cfg = get_all_settings()
    cat = request.args.get('category','')
    cur = db.connection.cursor()
    if cat:
        cur.execute("SELECT * FROM gallery_photos WHERE is_active=true AND category=%s ORDER BY created_at DESC",(cat,))
    else:
        cur.execute("SELECT * FROM gallery_photos WHERE is_active=true ORDER BY created_at DESC")
    photos = cur.fetchall(); cur.close()
    cats = ['Event','Sports','Classroom','Cultural','Achievement','Other']
    return render_template('public/gallery.html',
        photos=photos, categories=cats, sel_category=cat,
        school_name=cfg.get('school_name','Vivekanand Vidya Mandir Dharampur'),
        cfg=cfg)

@public_bp.route('/downloads')
def downloads():
    ensure_public_tables()
    cfg = get_all_settings()
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM public_downloads WHERE is_active=true ORDER BY created_at DESC")
    downloads = cur.fetchall(); cur.close()
    return render_template('public/downloads.html', downloads=downloads,
        school_name=cfg.get('school_name','VVM Dharampur'),
        cfg=cfg)

@public_bp.route('/download_file/<int:did>')
def download_file(did):
    ensure_public_tables()
    cur = db.connection.cursor()
    cur.execute("UPDATE public_downloads SET download_count = download_count + 1 WHERE id=%s",(did,))
    cur.execute("SELECT filename FROM public_downloads WHERE id=%s",(did,))
    row = cur.fetchone()
    db.connection.commit(); cur.close()
    if row:
        from utils.storage import get_public_url
        return redirect(get_public_url('downloads', row['filename']))
    flash('File not found.','danger')
    return redirect(url_for('public.downloads'))

@public_bp.route('/enquiry', methods=['POST'])
def enquiry():
    ensure_public_tables()
    f = request.form
    cur = db.connection.cursor()
    cur.execute("""INSERT INTO admission_enquiries
                   (student_name,father_name,mobile,email,class_applying,current_school,message)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (f.get('student_name',''), f.get('father_name',''),
         f.get('mobile',''), f.get('email',''),
         f.get('class_applying',''), f.get('current_school',''),
         f.get('message','')))
    db.connection.commit(); cur.close()
    flash('Enquiry submitted successfully! We will contact you soon.','success')
    return redirect(url_for('public.index'))

@public_bp.route('/notice/<int:nid>')
def notice_detail(nid):
    ensure_public_tables()
    cfg = get_all_settings()
    cur = db.connection.cursor()
    cur.execute("""SELECT * FROM notices WHERE id=%s
                   AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)""", (nid,))
    notice = cur.fetchone(); cur.close()
    if not notice:
        flash('Notice not found.','danger')
        return redirect(url_for('public.index'))
    return render_template('public/notice_detail.html',
        notice=notice,
        school_name=cfg.get('school_name','VVM Dharampur'),
        cfg=cfg)

@public_bp.route('/student-hub')
def student_hub():
    """Redirect to the new Student Portal (replaces old Student Hub)."""
    return redirect(url_for('student_portal.portal_login_page'))

@public_bp.route('/api/student-hub/dues')
def api_student_hub_dues():
    """Returns the dues and student info for the currently logged in student/parent."""
    from flask_login import current_user
    if not current_user.is_authenticated:
        return jsonify({'status': 'error', 'message': 'Please login to access your fee details.'}), 401
    
    if not current_user.student_id:
        return jsonify({'status': 'error', 'message': 'Only student or parent accounts can view due fees.'}), 403
        
    try:
        from routes.fees import get_due_months
        cur = db.connection.cursor()
        cur.execute("SELECT * FROM students WHERE id=%s", (current_user.student_id,))
        student = cur.fetchone()
        cur.close()
        
        if not student:
            return jsonify({'status': 'error', 'message': 'No student profile linked to this account.'}), 404
            
        due_months = get_due_months(student['id'], student['admission_date'])
        
        monthly_fee = float(student['monthly_fee'] or 0.0)
        transport_fee = float(student['transport_fee'] or 0.0)
        total_monthly_amount = monthly_fee + transport_fee
        total_due_amount = len(due_months) * total_monthly_amount
        
        return jsonify({
            'status': 'success',
            'student_name': student['student_name'],
            'admission_number': student['admission_number'],
            'class': student['class'],
            'section': student['section'],
            'monthly_fee': monthly_fee,
            'transport_fee': transport_fee,
            'total_monthly_amount': total_monthly_amount,
            'due_months': due_months,
            'due_count': len(due_months),
            'total_due_amount': total_due_amount
        })
    except Exception as e:
        print(f"Error fetching student dues: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error while retrieving details.'}), 500

@public_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles requests from the AI Chatbot in the Student Hub."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'})
        
    user_message = data.get('message', '')
    class_level = data.get('class_level', '5')
    
    # Get Gemini API key from environment
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({
            'status': 'success',
            'reply': "System Administrator hasn't configured the AI API key yet. Please contact the school."
        })
        
    try:
        genai.configure(api_key=api_key)
        # Using the recommended model
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Strict system prompt to ensure simple, age-appropriate answers
        prompt = f"""
        You are a friendly, helpful school AI tutor for Vivekanand Vidya Mandir Dharampur.
        The student asking the question is in Class {class_level} (approximate age: {int(class_level) + 5} years old).
        
        Rules:
        1. Keep the answer VERY simple and easy to understand.
        2. Do not use overly advanced vocabulary or complex college-level concepts.
        3. Explain the concept specifically tailored to a Class {class_level} student's understanding.
        4. Do not provide links or formatting other than bolding important words.
        5. Keep the response concise, maximum 3-4 short paragraphs.
        
        Student's Question: {user_message}
        """
        
        response = model.generate_content(prompt)
        
        return jsonify({
            'status': 'success',
            'reply': response.text
        })
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'AI service is currently unavailable.'
        })

