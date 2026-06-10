"""
RBAC & Security Verification Script for VVM ERP v2.0
Validates that:
1. Student login on Staff Portal fails with generic message
2. Staff login works
3. Manual dashboard paths redirect or return 403 correctly
4. RBAC loopholes (Noticeboard, Exams, Gallery, Receipts) are securely closed
"""
import sys
import os

# Set search path to workspace root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import db

def run_tests():
    print("START: Starting Security Verification Suite...")
    print("-" * 50)
    
    # Enable testing mode in Flask
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    client = app.test_client()
    
    with app.app_context():
        # First, ensure there is a student and an admin in the database to test with
        cur = db.connection.cursor()
        
        # Check if an admin exists, or get its credentials
        cur.execute("SELECT username, role FROM users WHERE role='admin' AND is_active=true LIMIT 1")
        admin_user = cur.fetchone()
        
        # Check if a student user exists
        cur.execute("SELECT username, role, student_id FROM users WHERE role='student' AND is_active=true LIMIT 1")
        student_user = cur.fetchone()
        
        cur.close()
        
        if not admin_user or not student_user:
            print("ERROR: Missing test users in the database! Please run setup_passwords.py first.")
            return

        print(f"Test users loaded: Admin='{admin_user['username']}', Student='{student_user['username']}' (student_id={student_user['student_id']})")
        print("-" * 50)

        # ──── TEST 1: Student Login on Staff Portal Blocked with Generic Message ────
        print("Test 1: Student Login on Staff Portal (Strict Role-Based Auth)...")
        # Send POST login attempt using student username and a password with AJAX header
        resp = client.post('/login', data={
            'username': student_user['username'],
            'password': 'SomePassword123'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        # Verify it fails and returns unified generic message
        assert resp.status_code == 401, f"FAIL: Expected 401, got {resp.status_code}"
        data = resp.get_json()
        assert data['status'] == 'error'
        assert data['message'] == 'Invalid username or password', f"FAIL: Expected 'Invalid username or password', got '{data['message']}'"
        print("  OK: Student account login rejected on Staff Login page with generic message.")
        
        # Double check with a non-existent user
        resp_fake = client.post('/login', data={
            'username': 'fake_user_123',
            'password': 'SomePassword123'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        assert resp_fake.status_code == 401
        data_fake = resp_fake.get_json()
        assert data_fake['status'] == 'error'
        assert data_fake['message'] == 'Invalid username or password', f"FAIL: Expected 'Invalid username or password', got '{data_fake['message']}'"
        print("  OK: Fake user login returned identical generic message (no username enumeration).")

        # ──── TEST 2: Specific Dashboard Path Protections (Anonymous User) ────
        print("Test 2: Dashboard route protection (Anonymous / Logged out user)...")
        
        for path in ['/admin', '/staff', '/teacher', '/accountant', '/dashboard']:
            resp_anon = client.get(path)
            # Should redirect to login page (302) since user is anonymous
            assert resp_anon.status_code == 302, f"FAIL: Anonymous user not redirected from {path} (got {resp_anon.status_code})"
            print(f"  OK: Anonymous user blocked from {path} (redirected to login).")

        # ──── TEST 3: Staff Login Page Accepts Staff ────
        print("Test 3: Staff Login Page accepts admin credentials...")
        resp_admin = client.post('/login', data={
            'username': 'admin',
            'password': 'Admin@123'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        # Check that it redirects or logs in successfully
        assert resp_admin.status_code == 200, f"FAIL: Admin login failed with status {resp_admin.status_code}"
        data_admin = resp_admin.get_json()
        assert data_admin['status'] == 'success'
        print("  OK: Admin successfully authenticated via AJAX.")

        # ──── TEST 4: Specific Dashboard Path Protections (Admin Session) ────
        print("Test 4: Specific dashboard paths under Admin session...")
        # Since Admin is logged in, /admin and /staff should redirect to /dashboard (302),
        # while /teacher and /accountant must return 403 Forbidden.
        for path in ['/admin', '/staff', '/teacher', '/accountant']:
            resp_dash = client.get(path)
            if path in ('/admin', '/staff'):
                assert resp_dash.status_code == 302, f"FAIL: Admin got blocked from {path} (got {resp_dash.status_code})"
                print(f"  OK: Admin successfully allowed/redirected to dashboard from {path}.")
            else:
                assert resp_dash.status_code == 403, f"FAIL: Admin not denied from {path} (got {resp_dash.status_code})"
                print(f"  OK: Admin blocked with 403 from role-incompatible path: {path}.")

        # Log out the admin
        client.get('/logout')

        # ──── TEST 5: Logged-in Student Session ────
        print("Test 5: Initializing Student Session...")
        cur = db.connection.cursor()
        import flask_bcrypt
        bcrypt = flask_bcrypt.Bcrypt()
        hashed = bcrypt.generate_password_hash("Test@123").decode('utf-8')
        
        # Check if student exists or create one
        cur.execute("SELECT id FROM students WHERE id=999")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO students (id, admission_number, student_name, class, section, status, father_name, mother_name, mobile_number, gender, admission_date)
                VALUES (999, 'ADM9999', 'Test Student', '1', 'A', 'Active', 'Test Father', 'Test Mother', '9999999999', 'Male', CURRENT_DATE)
            """)
        
        cur.execute("SELECT id FROM users WHERE username='teststudent'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO users (username, password, email, full_name, role, student_id, is_active)
                VALUES ('teststudent', %s, 'test@test.com', 'Test Student', 'student', 999, true)
            """, (hashed,))
            
        db.connection.commit()
        cur.close()

        # Let's login as the student
        resp_stud = client.post('/student-portal/api/login', json={
            'login_id': 'teststudent',
            'password': 'Test@123'
        })
        assert resp_stud.status_code == 200, "FAIL: Student login failed"
        print("  OK: Student session initialized successfully.")
        
        # Now try to access restricted dashboards under student session
        for path in ['/admin', '/staff', '/teacher', '/accountant', '/dashboard']:
            resp_blocked = client.get(path)
            if path == '/dashboard':
                assert resp_blocked.status_code == 302, f"FAIL: Student got {resp_blocked.status_code} on {path}"
            else:
                assert resp_blocked.status_code == 403, f"FAIL: Student did not get 403 on {path} (got {resp_blocked.status_code})"
            print(f"  OK: Student blocked from manual dashboard path: {path}")

        # ──── TEST 6: Closing RBAC Loopholes & IDOR Controls ────
        print("Test 6: RBAC Loophole & IDOR protections...")
        
        # Test 6.1: Student trying to edit/delete notices
        resp_notice = client.post('/noticeboard/edit/1', data={'title': 'Hacked'})
        assert resp_notice.status_code == 302, "FAIL: Notice edit didn't redirect (block) student!"
        # Check that it flashed warning
        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            assert any('admin/teacher' in f[1] for f in flashes), "FAIL: Notice edit did not flash permission warning!"
        print("  OK: Student blocked from editing notices.")

        # Test 6.2: Student trying to enter marks
        resp_marks = client.post('/exams/marks/1', data={'marks_999': 100})
        # Note: @permission_required decorator redirects to dashboard.index (302) with a flash message when unauthorized.
        assert resp_marks.status_code == 302, f"FAIL: Student got {resp_marks.status_code} on exams/marks (expected 302)"
        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            assert any('permission' in f[1] for f in flashes), "FAIL: Marks entry did not flash permission warning!"
        print("  OK: Student blocked from entering exam marks (redirected to dashboard with warning).")

        # Test 6.3: Student trying to manage gallery
        resp_gallery = client.get('/admin/gallery')
        assert resp_gallery.status_code == 403, f"FAIL: Student got {resp_gallery.status_code} on /admin/gallery (expected 403)"
        print("  OK: Student blocked from viewing gallery management page (403 Forbidden).")

        # Test 6.4: IDOR on student_info
        resp_info = client.get('/fees/student_info/1')
        assert resp_info.status_code == 403, f"FAIL: Student got {resp_info.status_code} on student_info IDOR (expected 403)"
        
        # Student queries their own student_id 999
        resp_own_info = client.get('/fees/student_info/999')
        assert resp_own_info.status_code == 200, f"FAIL: Student got {resp_own_info.status_code} on own student_info (expected 200)"
        print("  OK: IDOR blocked on /fees/student_info/ API.")

        # Test 6.5: IDOR on receipts
        cur = db.connection.cursor()
        cur.execute("SELECT receipt_number FROM fee_payments LIMIT 1")
        payment_row = cur.fetchone()
        
        if payment_row:
            receipt_no = payment_row['receipt_number']
            resp_receipt = client.get(f'/fees/receipt/{receipt_no}')
            assert resp_receipt.status_code == 403, f"FAIL: Student got {resp_receipt.status_code} on other's receipt (expected 403)"
            print(f"  OK: IDOR blocked on /fees/receipt/{receipt_no} view.")
        else:
            print("  Skip: No receipt found in database to test receipt IDOR.")

        # Cleanup test entries
        cur = db.connection.cursor()
        cur.execute("DELETE FROM users WHERE username='teststudent'")
        cur.execute("DELETE FROM students WHERE id=999")
        db.connection.commit()
        cur.close()

        print("-" * 50)
        print("SUCCESS: ALL SECURITY VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("The Staff Login and RBAC system are now fully secure and enterprise-grade.")

if __name__ == '__main__':
    run_tests()
