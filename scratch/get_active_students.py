import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import db

with app.app_context():
    try:
        cur = db.connection.cursor()
        cur.execute("SELECT id, admission_number, student_name, class, roll_number, mobile_number, photo, status FROM students WHERE status='Active' LIMIT 5")
        rows = cur.fetchall()
        print("Active Students:")
        for r in rows:
            print(dict(r))
        cur.close()
    except Exception as e:
        print(f"Error querying students: {e}")
