import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import db

def run_tests():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    print("=== STARTING STUDENT PORTAL ENDPOINT TESTS ===")

    # 1. Test Login page loads
    print("\n[TEST 1] GET /student-portal/")
    res = client.get('/student-portal/')
    if res.status_code == 200:
        print("  [OK] Login page loaded successfully (200 OK)")
    else:
        print(f"  [FAIL] Failed to load login page: {res.status_code}")

    # 2. Clean up any existing test user if we previously registered ADM0002
    with app.app_context():
        cur = db.connection.cursor()
        cur.execute("DELETE FROM users WHERE username = 'adm0002'")
        db.connection.commit()
        cur.close()

    # 3. Test self-registration API (Valid case)
    print("\n[TEST 2] POST /student-portal/api/register (Valid student ADM0002)")
    reg_data = {
        'admission_number': 'ADM0002',
        'full_name': 'suraj kumar',
        'email': 'suraj.test@vvmdharampur.edu.in',
        'mobile': '7894561023',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }
    res = client.post('/student-portal/api/register', 
                      data=json.dumps(reg_data), 
                      content_type='application/json')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 200, "Registration should succeed for active unregistered student"

    # 4. Test self-registration API (Duplicate case)
    print("\n[TEST 3] POST /student-portal/api/register (Duplicate registration)")
    res = client.post('/student-portal/api/register', 
                      data=json.dumps(reg_data), 
                      content_type='application/json')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 409, "Should prevent duplicate registration"

    # 5. Test login API (Incorrect Password)
    print("\n[TEST 4] POST /student-portal/api/login (Incorrect password)")
    login_data_wrong = {
        'login_id': 'ADM0002',
        'password': 'WrongPassword123'
    }
    res = client.post('/student-portal/api/login', 
                      data=json.dumps(login_data_wrong), 
                      content_type='application/json')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 401, "Should reject incorrect password"

    # 6. Test login API (Correct credentials)
    print("\n[TEST 5] POST /student-portal/api/login (Correct credentials)")
    login_data_correct = {
        'login_id': 'ADM0002',
        'password': 'Password@123'
    }
    res = client.post('/student-portal/api/login', 
                      data=json.dumps(login_data_correct), 
                      content_type='application/json')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 200, "Should authenticate successfully"
    login_res = json.loads(res.get_data(as_text=True))
    assert login_res['status'] == 'success'

    # 7. Test access to dashboard and profile with active session
    print("\n[TEST 6] GET /student-portal/api/profile (Authenticated session)")
    res = client.get('/student-portal/api/profile')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 200, "Profile API should be accessible"

    print("\n[TEST 7] GET /student-portal/api/fees (Authenticated session)")
    res = client.get('/student-portal/api/fees')
    print(f"  Response Code: {res.status_code}")
    print(f"  Response Body: {res.get_data(as_text=True)}")
    assert res.status_code == 200, "Fees API should be accessible"

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_tests()
