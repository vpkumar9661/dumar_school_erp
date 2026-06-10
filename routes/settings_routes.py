from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import db
from auth.decorators import admin_required

settings_bp = Blueprint('settings', __name__)
CLASSES = ['Nursery','LKG','UKG','1','2','3','4','5','6','7','8','9','10','11','12']

@settings_bp.route('/', methods=['GET','POST'])
@login_required
@admin_required
def index():
    cur = db.connection.cursor()
    if request.method == 'POST':
        for key in ['school_name','school_address','school_phone','school_email',
                     'late_fine_per_day','late_fine_after_days','current_session','monthly_fee_default']:
            val = request.form.get(key,'')
            cur.execute("""INSERT INTO settings (setting_key,setting_value) VALUES (%s,%s)
                           ON CONFLICT (setting_key) DO UPDATE SET setting_value=EXCLUDED.setting_value""",
                        (key, val))
        db.connection.commit()
        flash('Settings saved!', 'success')
    cur.execute("SELECT * FROM settings")
    settings = {r['setting_key']:r['setting_value'] for r in cur.fetchall()}
    cur.execute("""SELECT * FROM fee_structure
                   ORDER BY array_position(ARRAY['Nursery','LKG','UKG','1','2','3','4','5',
                   '6','7','8','9','10','11','12'], class), session""")
    fee_structure = cur.fetchall(); cur.close()
    return render_template('settings/index.html',
        settings=settings, fee_structure=fee_structure, classes=CLASSES)

@settings_bp.route('/fee_structure', methods=['POST'])
@login_required
@admin_required
def update_fee_structure():
    f = request.form
    classes = f.getlist('fs_class')
    cur = db.connection.cursor()
    for i, cls in enumerate(classes):
        session_val = f.getlist('fs_session')[i]
        monthly     = float(f.getlist('fs_monthly')[i] or 0)
        admission   = float(f.getlist('fs_admission')[i] or 0)
        development = float(f.getlist('fs_development')[i] or 0)
        exam        = float(f.getlist('fs_exam')[i] or 0)
        cur.execute("""INSERT INTO fee_structure (class,session,monthly_fee,admission_fee,development_fee,exam_fee)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (class, session) DO UPDATE SET
                       monthly_fee=EXCLUDED.monthly_fee,admission_fee=EXCLUDED.admission_fee,
                       development_fee=EXCLUDED.development_fee,exam_fee=EXCLUDED.exam_fee""",
                    (cls, session_val, monthly, admission, development, exam))
    db.connection.commit(); cur.close()
    flash('Fee structure updated!', 'success')
    return redirect(url_for('settings.index'))
