"""
Fee Management — Multi-month, all fee types, QR code receipts (PostgreSQL)
"""
import json, io, base64
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, make_response, jsonify, current_app, abort)
from flask_login import login_required, current_user
from db import db
from auth.decorators import permission_required
from datetime import datetime, date

fees_bp = Blueprint('fees', __name__)

MONTHS    = ['January','February','March','April','May','June',
             'July','August','September','October','November','December']
MONTH_NUM = {m: i+1 for i,m in enumerate(MONTHS)}
NUM_MONTH = {i+1: m for i,m in enumerate(MONTHS)}

def get_setting(key, default=''):
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT setting_value FROM settings WHERE setting_key=%s",(key,))
        row = cur.fetchone(); cur.close()
        return row['setting_value'] if row else default
    except Exception: return default

def next_receipt_number():
    cur = db.connection.cursor()
    cur.execute("SELECT MAX(CAST(SUBSTRING(receipt_number,4) AS INTEGER)) AS mx FROM fee_payments")
    row = cur.fetchone(); cur.close()
    return f"RCP{((row['mx'] or 0)+1):06d}"

def ensure_extra_columns():
    """PostgreSQL: ADD COLUMN IF NOT EXISTS — no need for SHOW COLUMNS."""
    cols = [
        ('admission_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('development_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('computer_lab_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('science_lab_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('library_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('exam_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('other_fee','DECIMAL(10,2) DEFAULT 0.00'),
        ('other_fee_remark',"VARCHAR(100) DEFAULT ''"),
        ('months_paid',"VARCHAR(500) DEFAULT ''"),
        ('discount',"DECIMAL(10,2) DEFAULT 0.00"),
        ('discount_reason',"VARCHAR(200) DEFAULT ''"),
        ('transaction_id',"VARCHAR(100) DEFAULT ''"),
        ('collected_by','INT DEFAULT NULL'),
    ]
    try:
        cur = db.connection.cursor()
        for col, defn in cols:
            cur.execute(f"ALTER TABLE fee_payments ADD COLUMN IF NOT EXISTS {col} {defn}")
        db.connection.commit(); cur.close()
    except Exception: pass

def get_due_months(student_id, admission_date_val):
    try:
        adm = datetime.strptime(str(admission_date_val), '%Y-%m-%d').date()
    except Exception:
        adm = date.today().replace(day=1)
    today = date.today()
    cur = db.connection.cursor()
    cur.execute("SELECT months_paid FROM fee_payments WHERE student_id=%s", (student_id,))
    paid_set = set()
    for row in cur.fetchall():
        for mp in (row['months_paid'] or '').split(','):
            mp = mp.strip()
            if mp: paid_set.add(mp)
    cur.close()
    due = []
    y, m = adm.year, adm.month
    while (y, m) <= (today.year, today.month):
        key = f"{NUM_MONTH[m]}_{y}"
        if key not in paid_set:
            due.append({'month': NUM_MONTH[m], 'year': y, 'key': key})
        m += 1
        if m > 12: m = 1; y += 1
    return due

def generate_qr(receipt_no, student_name, amount, payment_date):
    try:
        import qrcode
        data = (f"Receipt:{receipt_no}|Student:{student_name}|"
                f"Amount:{amount}|Date:{payment_date}|School:VVM Dharampur")
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(data); qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO(); img.save(buf, format='PNG')
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None

@fees_bp.route('/collect', methods=['GET','POST'])
@login_required
@permission_required('manage_fees')
def collect():
    ensure_extra_columns()
    search       = request.args.get('search','').strip()
    class_filter = request.args.get('class','').strip()
    month_filter = request.args.get('month','').strip()
    year_filter  = request.args.get('year','').strip()
    cur = db.connection.cursor()
    students = []
    has_filter = search or class_filter

    if has_filter:
        query = "SELECT * FROM students WHERE status='Active'"
        params = []
        if search:
            query += " AND (student_name LIKE %s OR admission_number LIKE %s)"
            params += [f"%{search}%", f"%{search}%"]
        if class_filter:
            query += " AND class=%s"
            params.append(class_filter)
        if month_filter and year_filter:
            # Only show students who have NOT paid for the selected month/year
            fee_due_key = f"{month_filter}_{year_filter}"
            query += """ AND NOT EXISTS (
                SELECT 1 FROM fee_payments fp
                WHERE fp.student_id=students.id AND fp.months_paid LIKE %s
            )"""
            params.append(f"%{fee_due_key}%")
        query += " ORDER BY class, section, roll_number"
        cur.execute(query, params)
        students = cur.fetchall()
    cur.close()

    classes = ['Nursery','LKG','UKG'] + [str(i) for i in range(1,13)]

    if request.method == 'POST':
        f = request.form
        student_id   = int(f['student_id'])
        payment_date = f.get('payment_date', date.today().strftime('%Y-%m-%d'))
        payment_mode = f.get('payment_mode','Cash')
        transaction_id = f.get('transaction_id','')
        remarks      = f.get('remarks','')
        selected_months_raw = f.get('selected_months','[]')
        try:    selected_months = json.loads(selected_months_raw)
        except: selected_months = []
        if not selected_months:
            flash('Please select at least one month to collect fees.','warning')
            return redirect(url_for('fees.collect', search=search))
        cur = db.connection.cursor()
        cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
        student = cur.fetchone()
        monthly_fee   = float(student['monthly_fee'])
        transport_fee = float(student['transport_fee'])
        admission_fee    = float(f.get('admission_fee',0) or 0)
        development_fee  = float(f.get('development_fee',0) or 0)
        computer_lab_fee = float(f.get('computer_lab_fee',0) or 0)
        science_lab_fee  = float(f.get('science_lab_fee',0) or 0)
        library_fee      = float(f.get('library_fee',0) or 0)
        exam_fee         = float(f.get('exam_fee',0) or 0)
        other_fee        = float(f.get('other_fee',0) or 0)
        other_fee_remark = f.get('other_fee_remark','')
        late_fine        = float(f.get('late_fine',0) or 0)
        discount         = float(f.get('discount',0) or 0)
        discount_reason  = f.get('discount_reason','')
        n_months        = len(selected_months)
        tuition_total   = monthly_fee * n_months
        transport_total = transport_fee * n_months
        extra_total     = (admission_fee + development_fee + computer_lab_fee +
                          science_lab_fee + library_fee + exam_fee + other_fee)
        grand_total     = tuition_total + transport_total + extra_total + late_fine - discount
        months_paid_str = ','.join(f"{m['month']}_{m['year']}" for m in selected_months)
        already_paid = []
        for m_info in selected_months:
            key = f"{m_info['month']}_{m_info['year']}"
            cur.execute("SELECT id FROM fee_payments WHERE student_id=%s AND months_paid LIKE %s",
                        (student_id, f"%{key}%"))
            if cur.fetchone(): already_paid.append(f"{m_info['month']} {m_info['year']}")
        if already_paid:
            flash(f"Already paid: {', '.join(already_paid)}", 'danger')
            cur.close()
            return redirect(url_for('fees.collect', search=search))
        receipt_no  = next_receipt_number()
        first_m     = selected_months[0]
        cur.execute("""
            INSERT INTO fee_payments
            (student_id, receipt_number, month, year,
             monthly_fee, transport_fee, late_fine, total_amount,
             payment_date, payment_mode, transaction_id, remarks,
             admission_fee, development_fee, computer_lab_fee,
             science_lab_fee, library_fee, exam_fee,
             other_fee, other_fee_remark, months_paid,
             discount, discount_reason, collected_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (student_id, receipt_no,
              first_m['month'], int(first_m['year']),
              tuition_total, transport_total, late_fine, grand_total,
              payment_date, payment_mode, transaction_id, remarks,
              admission_fee, development_fee, computer_lab_fee,
              science_lab_fee, library_fee, exam_fee,
              other_fee, other_fee_remark, months_paid_str,
              discount, discount_reason, current_user.id))
        db.connection.commit(); cur.close()
        flash(f'{n_months} month(s) fee collected successfully. Receipt No: {receipt_no}', 'success')
        return redirect(url_for('fees.receipt', receipt_id=receipt_no))
    return render_template('fees/collect.html',
        students=students, months=MONTHS,
        search=search, today=date.today().strftime('%Y-%m-%d'),
        current_year=datetime.now().year,
        years=list(range(2020, datetime.now().year+2)),
        classes=classes,
        sel_class=class_filter, sel_month=month_filter,
        sel_year=year_filter)

@fees_bp.route('/student_info/<int:sid>')
@login_required
def student_info(sid):
    if current_user.role not in ('admin', 'accountant', 'teacher'):
        if current_user.student_id != sid:
            return jsonify({'error': 'Unauthorized'}), 403
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    student = cur.fetchone(); cur.close()
    if not student: return jsonify({'error':'Not found'}), 404
    due_months = get_due_months(sid, student['admission_date'])
    return jsonify({
        'id': student['id'], 'student_name': student['student_name'],
        'admission_number': student['admission_number'],
        'father_name': student['father_name'],
        'class': student['class'], 'section': student['section'],
        'monthly_fee': float(student['monthly_fee']),
        'transport_fee': float(student['transport_fee']),
        'due_months': due_months, 'due_count': len(due_months),
    })

@fees_bp.route('/receipt/<receipt_id>')
@login_required
def receipt(receipt_id):
    ensure_extra_columns()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT fp.*, s.student_name, s.admission_number, s.father_name,
               s.class, s.section, s.roll_number, s.mobile_number, s.photo
        FROM fee_payments fp JOIN students s ON s.id=fp.student_id
        WHERE fp.receipt_number=%s
    """, (receipt_id,))
    payment = cur.fetchone()
    if not payment:
        flash('Receipt not found.', 'danger'); cur.close()
        return redirect(url_for('fees.history'))
    
    if current_user.role not in ('admin', 'accountant', 'teacher'):
        if current_user.student_id != payment['student_id']:
            cur.close()
            abort(403)
            
    months_list = []
    mp = payment.get('months_paid','') or ''
    for key in mp.split(','):
        key = key.strip()
        if key:
            parts = key.rsplit('_', 1)
            if len(parts) == 2:
                months_list.append({'month':parts[0], 'year':parts[1]})
    if not months_list:
        months_list = [{'month':payment['month'],'year':payment['year']}]
    cur.execute("SELECT * FROM students WHERE id=%s", (payment['student_id'],))
    student = cur.fetchone(); cur.close()
    remaining_due = get_due_months(payment['student_id'], student['admission_date']) if student else []
    qr_data = generate_qr(receipt_id, payment['student_name'],
        payment['total_amount'], str(payment['payment_date']))
    return render_template('fees/receipt.html',
        payment=payment, months_list=months_list, remaining_due=remaining_due,
        qr_code=qr_data, school_name=get_setting('school_name','VVM Dharampur'),
        school_address=get_setting('school_address',''),
        school_phone=get_setting('school_phone',''))

@fees_bp.route('/receipt_pdf/<receipt_id>')
@login_required
def receipt_pdf(receipt_id):
    try:
        from weasyprint import HTML
        ensure_extra_columns()
        cur = db.connection.cursor()
        cur.execute("""
            SELECT fp.*, s.student_name, s.admission_number, s.father_name,
                   s.class, s.section, s.roll_number, s.mobile_number
            FROM fee_payments fp JOIN students s ON s.id=fp.student_id
            WHERE fp.receipt_number=%s
        """, (receipt_id,))
        payment = cur.fetchone()
        if not payment:
            cur.close()
            flash('Receipt not found.', 'danger')
            return redirect(url_for('fees.history'))
        
        if current_user.role not in ('admin', 'accountant', 'teacher'):
            if current_user.student_id != payment['student_id']:
                cur.close()
                abort(403)
                
        cur.close()
        months_list = []
        mp = payment.get('months_paid','') or ''
        for key in mp.split(','):
            key = key.strip()
            if key:
                parts = key.rsplit('_',1)
                if len(parts) == 2:
                    months_list.append({'month':parts[0],'year':parts[1]})
        if not months_list:
            months_list = [{'month':payment['month'],'year':payment['year']}]
        qr_data = generate_qr(receipt_id, payment['student_name'],
                               payment['total_amount'], str(payment['payment_date']))
        html_str = render_template('fees/receipt.html',
            payment=payment, months_list=months_list, remaining_due=[],
            qr_code=qr_data, school_name=get_setting('school_name'),
            school_address=get_setting('school_address'),
            school_phone=get_setting('school_phone'), pdf_mode=True)
        pdf = HTML(string=html_str, base_url=current_app.root_path).write_pdf()
        resp = make_response(pdf)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'attachment; filename=Receipt_{receipt_id}.pdf'
        return resp
    except ImportError:
        flash('WeasyPrint not installed.', 'warning')
        return redirect(url_for('fees.receipt', receipt_id=receipt_id))

@fees_bp.route('/history')
@login_required
@permission_required('manage_fees')
def history():
    ensure_extra_columns()
    page     = int(request.args.get('page',1))
    per_page = 30
    offset   = (page-1)*per_page
    cls      = request.args.get('class','')
    month    = request.args.get('month','')
    year     = request.args.get('year','')
    search   = request.args.get('search','').strip()
    cur = db.connection.cursor()
    base = """SELECT fp.*,s.student_name,s.admission_number,s.class,s.section
              FROM fee_payments fp JOIN students s ON s.id=fp.student_id WHERE 1=1"""
    params = []
    if cls:    base += " AND s.class=%s";   params.append(cls)
    if month:  base += " AND fp.month=%s";  params.append(month)
    if year:   base += " AND fp.year=%s";   params.append(year)
    if search:
        base += " AND (s.student_name LIKE %s OR fp.receipt_number LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    cur.execute(base + " ORDER BY fp.created_at DESC LIMIT %s OFFSET %s",
                params + [per_page, offset])
    payments = cur.fetchall()
    cur.execute(base.replace(
        "fp.*,s.student_name,s.admission_number,s.class,s.section","COUNT(*) AS cnt"), params)
    total = cur.fetchone()['cnt']
    cur.close()
    classes = ['Nursery','LKG','UKG'] + [str(i) for i in range(1,13)]
    return render_template('fees/history.html',
        payments=payments, total=total, page=page, per_page=per_page,
        months=MONTHS, years=list(range(2020, datetime.now().year+2)),
        classes=classes, sel_class=cls, sel_month=month,
        sel_year=year, search=search)

@fees_bp.route('/pending')
@login_required
@permission_required('manage_fees')
def pending():
    now   = datetime.now()
    month = request.args.get('month', now.strftime('%B'))
    year  = int(request.args.get('year', now.year))
    cls   = request.args.get('class','')
    key   = f"{month}_{year}"
    cur = db.connection.cursor()
    q = """SELECT s.* FROM students s WHERE s.status='Active'
           AND NOT EXISTS (
               SELECT 1 FROM fee_payments fp
               WHERE fp.student_id=s.id AND fp.months_paid LIKE %s
           )"""
    params = [f"%{key}%"]
    if cls: q += " AND s.class=%s"; params.append(cls)
    q += " ORDER BY s.class, s.section, s.roll_number"
    cur.execute(q, params)
    pending_students = cur.fetchall(); cur.close()
    classes = ['Nursery','LKG','UKG'] + [str(i) for i in range(1,13)]
    return render_template('fees/pending.html',
        students=pending_students, months=MONTHS,
        years=range(2020, now.year+2), classes=classes,
        sel_month=month, sel_year=year, sel_class=cls)
