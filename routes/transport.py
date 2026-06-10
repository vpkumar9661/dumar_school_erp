from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import db
from auth.decorators import permission_required

transport_bp = Blueprint('transport', __name__)

@transport_bp.route('/')
@login_required
@permission_required('manage_fees')
def manage():
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM transport_slabs ORDER BY id")
    slabs = cur.fetchall()
    cur.execute("""SELECT s.student_name,s.admission_number,s.class,s.section,
                          s.transport_distance,s.transport_fee
                   FROM students s WHERE s.transport_distance!='None' AND s.status='Active'
                   ORDER BY s.transport_distance,s.class""")
    transport_students = cur.fetchall()
    cur.execute("""SELECT transport_distance,COUNT(*) AS count,SUM(transport_fee) AS total_fee
                   FROM students WHERE transport_distance!='None' AND status='Active'
                   GROUP BY transport_distance""")
    summary = cur.fetchall(); cur.close()
    return render_template('transport/manage.html',
        slabs=slabs, transport_students=transport_students, summary=summary)

@transport_bp.route('/update_slabs', methods=['POST'])
@login_required
@permission_required('manage_fees')
def update_slabs():
    cur = db.connection.cursor()
    for slab in ['0-2','2-5','5-10','10+']:
        fee_key = f"fee_{slab.replace('-','_').replace('+','plus')}"
        fee = float(request.form.get(fee_key, 0))
        cur.execute("UPDATE transport_slabs SET fee=%s WHERE distance_slab=%s", (fee, slab))
    # PostgreSQL UPDATE FROM syntax (no INNER JOIN in UPDATE)
    cur.execute("""UPDATE students SET transport_fee=ts.fee
                   FROM transport_slabs ts
                   WHERE ts.distance_slab=students.transport_distance
                   AND students.transport_distance!='None'""")
    db.connection.commit(); cur.close()
    flash('Transport slabs updated!', 'success')
    return redirect(url_for('transport.manage'))
