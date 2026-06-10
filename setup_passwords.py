"""
VVM ERP v2.0 — Password Setup Script (Supabase/PostgreSQL)
Run ONCE after schema_postgres.sql to set correct bcrypt passwords.
Usage: python setup_passwords.py
"""
from flask import Flask
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
import psycopg2
import psycopg2.extras

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'setup_temp'

bcrypt = Bcrypt(app)

DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL:
    print("  [ERROR] DATABASE_URL not found in .env file!")
    print("  Add: DATABASE_URL=postgresql://postgres.xxxxx:password@host:6543/postgres")
    exit(1)

DEFAULT_USERS = [
    # (username, plain_password, full_name, email, role)
    ('admin',      'Admin@123',   'School Administrator', 'admin@vvmdharampur.edu.in', 'admin'),
    ('accountant', 'Account@123', 'Fee Accountant',       'accounts@vvmdharampur.edu.in', 'accountant'),
    ('teacher1',   'Teacher@123', 'Ramesh Kumar',         'ramesh@vvm.edu.in', 'teacher'),
]

with app.app_context():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()

    for username, password, full_name, email, role in DEFAULT_USERS:
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if user exists
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        existing = cur.fetchone()

        if existing:
            cur.execute("UPDATE users SET password=%s WHERE username=%s", (hashed, username))
            print(f"  [OK] Updated password for: {username} ({role})")
        else:
            cur.execute("""
                INSERT INTO users (username, password, email, full_name, role, is_active)
                VALUES (%s, %s, %s, %s, %s, true)
            """, (username, hashed, email, full_name, role))
            print(f"  [OK] Created user: {username} ({role})")

    # Link teacher1 to Ramesh Kumar (teacher_id=1)
    cur.execute("UPDATE users SET teacher_id=1 WHERE username='teacher1'")

    conn.commit()
    cur.close()
    conn.close()

    print()
    print("=" * 50)
    print("  Password setup complete!")
    print()
    print("  Default Login Credentials:")
    print("  +------------+-----------------+--------------+")
    print("  | Username   | Password        | Role         |")
    print("  +------------+-----------------+--------------+")
    print("  | admin      | Admin@123       | Administrator|")
    print("  | accountant | Account@123     | Accountant   |")
    print("  | teacher1   | Teacher@123     | Teacher      |")
    print("  +------------+-----------------+--------------+")
    print()
    print("  WARNING: Remember to change all default passwords before deploying to production!")
    print("=" * 50)

if __name__ == '__main__':
    print("VVM ERP -- Password Setup (Supabase)")
    print("-" * 30)
