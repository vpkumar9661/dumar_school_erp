import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import Database

db = Database()
with app.app_context():
    cur = db.connection.cursor()
    cur.execute("SELECT id, student_name, email, status, notes FROM admission_enquiries")
    rows = cur.fetchall()
    print("Database Rows:")
    for r in rows:
        print(f"ID: {r['id']}, Student: {r['student_name']}, Email: {r['email']}, Status: {r['status']}, Notes: {r['notes']}")
    cur.close()
