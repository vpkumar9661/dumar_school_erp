"""
Teachers & Salary — PostgreSQL/Supabase version
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import db
from datetime import datetime, date

teachers_bp = Blueprint('teachers', __name__)

MONTHS = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']

def _int(v, default=0):
    try:    return int(v)
    except: return default

def _float(v, default=0.0):
    try:    return float(v) if v not in (None, '', 'None') else default
    except: return default

def _can_manage():
    if not hasattr(current_user, 'has_permission'):
        return True
    return current_user.has_permission('manage_teachers') or \
           current_user.role in ('admin', 'accountant')

def _can_salary():
    if not hasattr(current_user, 'has_permission'):
        return True
    return current_user.role in ('admin', 'accountant') or \
           current_user.has_permission('manage_salary') or \
           current_user.has_permission('view_salary')

def ensure_salary_cols():
    """PostgreSQL: ADD COLUMN IF NOT EXISTS — much simpler than MySQL."""
    try:
        cur = db.connection.cursor()
        cur.execute("ALTER TABLE salary_payments ADD COLUMN IF NOT EXISTS deductions DECIMAL(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE salary_payments ADD COLUMN IF NOT EXISTS net_amount DECIMAL(10,2) DEFAULT 0.00")
        cur.execute("UPDATE salary_payments SET net_amount=amount WHERE net_amount=0")
        cur.execute("ALTER TABLE salary_payments ADD COLUMN IF NOT EXISTS paid_by INT DEFAULT NULL")
        cur.execute("ALTER TABLE salary_payments ADD COLUMN IF NOT EXISTS deduction_reason VARCHAR(255) DEFAULT NULL")
        cur.execute("ALTER TABLE salary_payments ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100) DEFAULT NULL")
        db.connection.commit(); cur.close()
    except Exception:
        try: db.connection.rollback()
        except: pass

MONTH_ORDER = """array_position(ARRAY['January','February','March','April','May','June',
          'July','August','September','October','November','December'], month)"""

@teachers_bp.route('/')
@login_required
def teacher_list():
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM teachers ORDER BY teacher_name")
    teachers = cur.fetchall(); cur.close()
    return render_template('teachers/list.html', teachers=teachers, can_manage=_can_manage())

@teachers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        teacher_name = request.form.get('teacher_name', '').strip()
        subject      = request.form.get('subject', '').strip()
        mobile       = request.form.get('mobile_number', '').strip()
        email        = request.form.get('email', '').strip()
        salary       = _float(request.form.get('salary', '0'), 0.0)
        joining_date = request.form.get('joining_date', '').strip() or None
        if not teacher_name:
            flash('Teacher name required!', 'warning')
            return redirect(url_for('teachers.teacher_list'))
        try:
            cur = db.connection.cursor()
            cur.execute(
                "INSERT INTO teachers "
                "(teacher_name,subject,mobile_number,email,salary,joining_date,status) "
                "VALUES (%s,%s,%s,%s,%s,%s,'Active')",
                (teacher_name, subject, mobile, email, salary, joining_date))
            db.connection.commit(); cur.close()
            flash(f"✅ Teacher '{teacher_name}' added!", 'success')
        except Exception as err:
            try: db.connection.rollback()
            except: pass
            flash(f'Error: {err}', 'danger')
        return redirect(url_for('teachers.teacher_list'))
    return render_template('teachers/add.html', today=date.today().strftime('%Y-%m-%d'))

@teachers_bp.route('/edit/<int:tid>', methods=['GET', 'POST'])
@login_required
def edit(tid):
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM teachers WHERE id=%s", (tid,))
    teacher = cur.fetchone(); cur.close()
    if not teacher:
        flash('Teacher not found.', 'danger')
        return redirect(url_for('teachers.teacher_list'))
    if request.method == 'POST':
        f = request.form
        try:
            cur = db.connection.cursor()
            cur.execute(
                "UPDATE teachers SET teacher_name=%s,subject=%s,mobile_number=%s,"
                "email=%s,salary=%s,joining_date=%s,status=%s WHERE id=%s",
                (f.get('teacher_name','').strip(), f.get('subject','').strip(),
                 f.get('mobile_number','').strip(), f.get('email','').strip(),
                 _float(f.get('salary','0'), 0.0),
                 f.get('joining_date','').strip() or None,
                 f.get('status','Active'), tid))
            db.connection.commit(); cur.close()
            flash('✅ Teacher updated!', 'success')
        except Exception as err:
            try: db.connection.rollback()
            except: pass
            flash(f'Error: {err}', 'danger')
        return redirect(url_for('teachers.teacher_list'))
    return render_template('teachers/edit.html', teacher=teacher)

@teachers_bp.route('/delete/<int:tid>', methods=['POST'])
@login_required
def delete(tid):
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT teacher_name FROM teachers WHERE id=%s", (tid,))
        t = cur.fetchone()
        if t:
            cur.execute("DELETE FROM teachers WHERE id=%s", (tid,))
            db.connection.commit()
            flash(f"Teacher '{t['teacher_name']}' deleted.", 'success')
        cur.close()
    except Exception as err:
        flash(f'Error: {err}', 'danger')
    return redirect(url_for('teachers.teacher_list'))

@teachers_bp.route('/salary')
@login_required
def salary():
    if not _can_salary():
        flash('Access restricted.', 'warning')
        return redirect(url_for('dashboard.index'))
    ensure_salary_cols()
    now    = datetime.now()
    month  = request.args.get('month', now.strftime('%B'))
    year   = _int(request.args.get('year', now.year), now.year)
    search = request.args.get('search', '').strip()
    teachers = []; monthly_report = []
    total_teachers = paid_count = pending_count = 0
    total_paid_amt = total_due_amt = 0.0
    try:
        cur = db.connection.cursor()
        q = """
            SELECT t.id, t.teacher_name, t.subject, t.mobile_number, t.salary, t.status,
                   sp.id AS payment_id, sp.amount AS paid_gross,
                   sp.deductions AS paid_deductions, sp.net_amount AS paid_net,
                   sp.payment_date, sp.payment_mode
            FROM teachers t
            LEFT JOIN salary_payments sp ON sp.teacher_id=t.id AND sp.month=%s AND sp.year=%s
            WHERE t.status='Active'
        """
        params = [month, year]
        if search:
            q += " AND t.teacher_name LIKE %s"
            params.append(f"%{search}%")
        q += " ORDER BY t.teacher_name"
        cur.execute(q, params)
        teachers = cur.fetchall()
        total_teachers = len(teachers)
        paid_count     = sum(1 for t in teachers if t['payment_id'])
        pending_count  = total_teachers - paid_count
        total_paid_amt = sum(_float(t['paid_net'] or t['paid_gross'] or 0) for t in teachers if t['payment_id'])
        total_due_amt  = sum(_float(t['salary'] or 0) for t in teachers if not t['payment_id'])
        cur.execute(f"""
            SELECT month, year,
                   SUM(COALESCE(net_amount, amount)) AS total_paid,
                   COUNT(*) AS num_teachers
            FROM salary_payments
            GROUP BY year, month
            ORDER BY year DESC, {MONTH_ORDER}
            LIMIT 6
        """)
        monthly_report = cur.fetchall()
        cur.close()
    except Exception as err:
        flash(f'Error loading salary: {err}', 'danger')
    years_list = [y for y in range(2020, now.year + 2)]
    return render_template('teachers/salary.html',
        teachers=teachers, months=MONTHS, month=month, year=year,
        years=years_list, search=search,
        total_teachers=total_teachers, paid_count=paid_count,
        pending_count=pending_count, total_paid_amt=total_paid_amt,
        total_due_amt=total_due_amt, monthly_report=monthly_report,
        today=date.today().strftime('%Y-%m-%d'), can_manage=_can_salary())

@teachers_bp.route('/pay/<int:tid>')
@login_required
def pay_page(tid):
    if not _can_salary():
        flash('Access denied.', 'danger'); return redirect(url_for('dashboard.index'))
    ensure_salary_cols()
    month = request.args.get('month', datetime.now().strftime('%B'))
    year  = _int(request.args.get('year', datetime.now().year), datetime.now().year)
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM teachers WHERE id=%s AND status='Active'", (tid,))
    teacher = cur.fetchone(); cur.close()
    if not teacher:
        flash('Teacher not found.', 'danger'); return redirect(url_for('teachers.salary'))
    cur = db.connection.cursor()
    cur.execute("SELECT id FROM salary_payments WHERE teacher_id=%s AND month=%s AND year=%s",
                (tid, month, year))
    already = cur.fetchone(); cur.close()
    if already:
        flash(f"{teacher['teacher_name']}'s salary for {month} {year} already processed.", 'warning')
        return redirect(url_for('teachers.salary', month=month, year=year))
    return render_template('teachers/pay.html',
        teacher=teacher, month=month, year=year, today=date.today().strftime('%Y-%m-%d'))

@teachers_bp.route('/process_pay', methods=['POST'])
@login_required
def process_pay():
    if not _can_salary():
        flash('Access denied.', 'danger'); return redirect(url_for('dashboard.index'))
    ensure_salary_cols()
    teacher_id        = _int(request.form.get('teacher_id'), 0)
    month             = request.form.get('month', '').strip()
    year              = _int(request.form.get('year', 0), 0)
    amount            = _float(request.form.get('amount', 0), 0.0)
    deductions        = _float(request.form.get('deductions', 0), 0.0)
    net_amount        = max(0.0, amount - deductions)
    payment_date      = request.form.get('payment_date', '') or date.today().strftime('%Y-%m-%d')
    payment_mode      = request.form.get('payment_mode', 'Cash').strip()
    remarks           = request.form.get('remarks', '').strip()
    deduction_reason  = request.form.get('deduction_reason', '').strip()
    payment_reference = request.form.get('payment_reference', '').strip()
    if teacher_id == 0 or amount <= 0:
        flash('Amount must be greater than 0.', 'danger')
        return redirect(url_for('teachers.salary', month=month, year=year))
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT id FROM salary_payments WHERE teacher_id=%s AND month=%s AND year=%s",
                    (teacher_id, month, year))
        if cur.fetchone():
            flash(f'{month} {year} salary already paid!', 'warning')
            cur.close()
            return redirect(url_for('teachers.salary', month=month, year=year))
        cur.execute("""
            INSERT INTO salary_payments
            (teacher_id, month, year, amount, deductions, net_amount,
             payment_date, payment_mode, remarks, deduction_reason, payment_reference)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (teacher_id, month, year, amount, deductions, net_amount,
              payment_date, payment_mode,
              remarks or None, deduction_reason or None, payment_reference or None))
        new_id = cur.fetchone()['id']
        db.connection.commit()
        cur.execute("SELECT teacher_name FROM teachers WHERE id=%s", (teacher_id,))
        row = cur.fetchone()
        name = row['teacher_name'] if row else 'Teacher'
        cur.close()
        flash(f"✅ {name} — ₹{net_amount:,.0f} paid via {payment_mode}!", 'success')
        return redirect(url_for('teachers.salary_receipt', spid=new_id))
    except Exception as err:
        try: db.connection.rollback()
        except: pass
        flash(f'Payment error: {err}', 'danger')
        return redirect(url_for('teachers.salary', month=month, year=year))

@teachers_bp.route('/salary/receipt/<int:spid>')
@login_required
def salary_receipt(spid):
    ensure_salary_cols()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT sp.*, t.teacher_name, t.subject, t.mobile_number
        FROM salary_payments sp JOIN teachers t ON t.id = sp.teacher_id
        WHERE sp.id = %s
    """, (spid,))
    record = cur.fetchone(); cur.close()
    if not record:
        flash('Receipt not found.', 'danger'); return redirect(url_for('teachers.salary'))
    return render_template('teachers/salary_receipt.html', record=record)

@teachers_bp.route('/pay_salary', methods=['POST'])
@login_required
def pay_salary():
    if not _can_salary():
        flash('Access denied.', 'danger'); return redirect(url_for('dashboard.index'))
    ensure_salary_cols()
    teacher_id   = _int(request.form.get('teacher_id'), 0)
    month        = request.form.get('month', '').strip()
    year         = _int(request.form.get('year', 0), 0)
    amount       = _float(request.form.get('amount', 0), 0.0)
    deductions   = _float(request.form.get('deductions', 0), 0.0)
    net_amount   = max(0.0, amount - deductions)
    payment_date = request.form.get('payment_date', '') or date.today().strftime('%Y-%m-%d')
    payment_mode = request.form.get('payment_mode', 'Cash').strip()
    remarks      = request.form.get('remarks', '').strip()
    if teacher_id == 0 or amount <= 0:
        flash('Invalid data.', 'danger')
        return redirect(url_for('teachers.salary', month=month, year=year))
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT id FROM salary_payments WHERE teacher_id=%s AND month=%s AND year=%s",
                    (teacher_id, month, year))
        if cur.fetchone():
            flash(f'{month} {year} salary already paid!', 'warning')
        else:
            cur.execute(
                "INSERT INTO salary_payments "
                "(teacher_id,month,year,amount,deductions,net_amount,payment_date,payment_mode,remarks) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (teacher_id, month, year, amount, deductions, net_amount,
                 payment_date, payment_mode, remarks))
            db.connection.commit()
            cur.execute("SELECT teacher_name FROM teachers WHERE id=%s", (teacher_id,))
            row = cur.fetchone()
            flash(f"✅ {row['teacher_name'] if row else 'Teacher'} — ₹{net_amount:,.0f} paid!", 'success')
        cur.close()
    except Exception as err:
        try: db.connection.rollback()
        except: pass
        flash(f'Payment error: {err}', 'danger')
    return redirect(url_for('teachers.salary', month=month, year=year))

@teachers_bp.route('/salary/bulk_pay_page')
@login_required
def bulk_pay_page():
    if not _can_salary():
        flash('Access denied.', 'danger'); return redirect(url_for('dashboard.index'))
    month = request.args.get('month', datetime.now().strftime('%B'))
    year  = _int(request.args.get('year', datetime.now().year), datetime.now().year)
    return redirect(url_for('teachers.salary', month=month, year=year))

@teachers_bp.route('/salary/bulk_pay', methods=['POST'])
@login_required
def bulk_pay_salary():
    if not _can_salary():
        flash('Access denied.', 'danger'); return redirect(url_for('dashboard.index'))
    ensure_salary_cols()
    month        = request.form.get('month', '')
    year         = _int(request.form.get('year', 0), 0)
    payment_date = request.form.get('payment_date', '') or date.today().strftime('%Y-%m-%d')
    payment_mode = request.form.get('payment_mode', 'Cash')
    count = 0
    try:
        cur = db.connection.cursor()
        cur.execute("""
            SELECT t.id, t.salary FROM teachers t WHERE t.status='Active'
            AND NOT EXISTS (SELECT 1 FROM salary_payments sp
                WHERE sp.teacher_id=t.id AND sp.month=%s AND sp.year=%s)
        """, (month, year))
        for t in cur.fetchall():
            sal = _float(t['salary'], 0.0)
            if sal > 0:
                cur.execute(
                    "INSERT INTO salary_payments "
                    "(teacher_id,month,year,amount,deductions,net_amount,payment_date,payment_mode) "
                    "VALUES (%s,%s,%s,%s,0,%s,%s,%s)",
                    (t['id'], month, year, sal, sal, payment_date, payment_mode))
                count += 1
        db.connection.commit(); cur.close()
        flash(f'✅ {count} teacher(s) salary processed for {month} {year}.', 'success')
    except Exception as err:
        try: db.connection.rollback()
        except: pass
        flash(f'Error: {err}', 'danger')
    return redirect(url_for('teachers.salary', month=month, year=year))

@teachers_bp.route('/salary/delete/<int:spid>', methods=['POST'])
@login_required
def delete_salary(spid):
    try:
        cur = db.connection.cursor()
        cur.execute("DELETE FROM salary_payments WHERE id=%s", (spid,))
        db.connection.commit(); cur.close()
        flash('Record deleted.', 'success')
    except Exception as err:
        flash(f'Error: {err}', 'danger')
    return redirect(url_for('teachers.salary'))

@teachers_bp.route('/salary/history/<int:tid>')
@login_required
def salary_history(tid):
    ensure_salary_cols()
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM teachers WHERE id=%s", (tid,))
    teacher = cur.fetchone()
    cur.execute(f"""
        SELECT * FROM salary_payments WHERE teacher_id=%s
        ORDER BY year DESC, {MONTH_ORDER}
    """, (tid,))
    history    = cur.fetchall()
    total_paid = sum(_float(r.get('net_amount') or r.get('amount') or 0) for r in history)
    cur.close()
    return render_template('teachers/salary_history.html',
        teacher=teacher, history=history, total_paid=total_paid)
