import os, sys, time
# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from config import Config
from db import db
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    print("Benchmarking single optimized stats query...")
    now   = datetime.now()
    month = now.strftime('%B')
    year  = now.year
    today = date.today()
    
    conn = db.connection
    cur = conn.cursor()
    
    t0 = time.time()
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM students WHERE status='Active') AS total_students,
            (SELECT COUNT(*) FROM teachers WHERE status='Active') AS total_teachers,
            (SELECT COALESCE(SUM(monthly_fee + transport_fee), 0) FROM students WHERE status='Active') AS fee_expected,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments WHERE month=%s AND year=%s) AS fee_received,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments) AS total_income,
            (SELECT COALESCE(SUM(total_amount), 0) FROM fee_payments WHERE payment_date=%s) AS today_collection,
            (SELECT COUNT(*) FROM fee_payments WHERE payment_date=%s) AS today_count,
            (SELECT COUNT(*) FROM teachers t WHERE status='Active' AND NOT EXISTS (
                SELECT 1 FROM salary_payments sp WHERE sp.teacher_id=t.id AND sp.month=%s AND sp.year=%s
            )) AS pending_salaries
    """, (month, year, today, today, month, year))
    res = cur.fetchone()
    elapsed = time.time() - t0
    
    print(f"Combined Stats Query took {elapsed:.4f} seconds!")
    print(res)
    
    cur.close()
