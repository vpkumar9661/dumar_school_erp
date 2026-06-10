# 🏫 VVM Dharampur School ERP v2.0 — Setup Guide

## ⚡ Quick Start (5 Steps)

---

## Step 1 — Install Python Libraries

```bash
cd school_erp_v2
pip install -r requirements.txt
```

**If WeasyPrint (PDF) fails on Windows:**
```bash
# Install GTK runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
# Then run:
pip install weasyprint
```

---

## Step 2 — Create Environment File

```bash
# Copy the environment template
copy .env.example .env        # Windows
cp .env.example .env          # Mac/Linux
```

`.env` file and set your MySQL password:
```
MYSQL_PASSWORD=your_xampp_password
SECRET_KEY=koi_bhi_long_random_string_yahan_likho
```

---

## Step 3 — Database Setup

**Start MySQL in XAMPP**, then run:

```
phpMyAdmin → localhost/phpmyadmin → SQL tab
Paste the full content of database/schema.sql → Click Go
```

✅ "Step 1 Done! Now run: python setup_passwords.py" dikhega

---

## Step 4 — Configure Passwords

```bash
python setup_passwords.py
```

This script automatically creates login credentials:

```
┌─────────────┬─────────────────┬──────────────┐
│ Username    │ Password        │ Role         │
├─────────────┼─────────────────┼──────────────┤
│ admin       │ Admin@123       │ Administrator│
│ accountant  │ Account@123     │ Accountant   │
│ teacher1    │ Teacher@123     │ Teacher      │
└─────────────┴─────────────────┴──────────────┘
```

---

## Step 5 — Start the Server

```bash
python run.py
```

Open in your browser: **http://localhost:5000**

---

## 🔐 Login System

### Default Logins

| Role | Username | Password | Kya Access |
|------|----------|----------|------------|
| **Admin** | `admin` | `Admin@123` | Full access |
| **Accountant** | `accountant` | `Account@123` | Fee management |
| **Teacher** | `teacher1` | `Teacher@123` | Attendance, Marks |

### Student Login Banana

1. Admin → User Management → Add User
2. Role: Student
3. Link to Student: Select the student's name
4. Set Username and Password
5. Student portal: http://localhost:5000/portal/

---

## 🏗️ Project Structure

```
school_erp_v2/
├── app.py                  ← Main Flask app (security headers, blueprints)
├── config.py               ← All settings (reads from .env)
├── db.py                   ← MySQL shared instance
├── run.py                  ← Start server
├── setup_passwords.py      ← Run ONCE to set passwords
├── .env.example            ← Copy to .env
│
├── auth/
│   ├── models.py           ← User class (Flask-Login)
│   └── decorators.py       ← @role_required, @permission_required
│
├── routes/
│   ├── auth_routes.py      ← Login, Logout, Change Password
│   ├── dashboard.py        ← Role-based dashboard
│   ├── students.py         ← Student CRUD
│   ├── fees.py             ← Fee collection, receipts, QR code
│   ├── teachers.py         ← Teacher + salary
│   ├── transport.py        ← Transport slabs
│   ├── exams.py            ← Exam schedule + marks entry
│   ├── attendance.py       ← Student + teacher attendance
│   ├── idcard.py           ← ID card generator
│   ├── reports.py          ← Excel/PDF reports
│   ├── noticeboard.py      ← Notices
│   ├── users.py            ← User management (Admin only)
│   ├── settings_routes.py  ← School settings + fee structure
│   └── portal.py           ← Student/Parent portal
│
├── templates/
│   ├── base.html           ← Role-aware sidebar
│   ├── dashboard.html      ← Main dashboard
│   ├── auth/               ← Login, Change Password, Profile
│   ├── users/              ← User list, create, edit, audit log
│   ├── portal/             ← Student portal pages
│   ├── students/           ← Student CRUD pages
│   ├── fees/               ← Fee collect, receipt, history
│   ├── settings/           ← School settings
│   └── errors/             ← 403, 404, 429, 500
│
├── static/
│   ├── css/style.css       ← Premium dark theme
│   └── js/main.js          ← Cursor glow, sidebar toggle
│
└── database/
    ├── schema.sql          ← Run this first
    └── migrate_fees.sql    ← If updating from v1
```

---

## 🛡️ Security Features

| Feature | Details |
|---------|---------|
| **bcrypt** | Password hashing (rounds=12) |
| **Rate Limiting** | 5 login attempts per minute per IP |
| **RBAC** | 5 roles with granular permissions |
| **Session Protection** | Flask-Login 'strong' mode |
| **Security Headers** | X-Frame, XSS, CSP headers |
| **Audit Log** | Every login attempt recorded |
| **Input Sanitization** | HTML escape on all inputs |
| **CSRF Protection** | Flask-WTF CSRF tokens |

---

## 👥 Role Permissions

| Permission | Admin | Accountant | Teacher | Student | Parent |
|-----------|:-----:|:----------:|:-------:|:-------:|:------:|
| Dashboard | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage Students | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Students | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage Fees | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage Teachers | ✅ | ❌ | ❌ | ❌ | ❌ |
| Attendance | ✅ | ❌ | ✅ | ❌ | ❌ |
| Marks Entry | ✅ | ❌ | ✅ | ❌ | ❌ |
| Reports | ✅ | ✅ | ❌ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ | ❌ |
| Settings | ✅ | ❌ | ❌ | ❌ | ❌ |
| Portal (View) | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 🚀 Production Deployment Tips

```python
# config.py mein:
DEBUG = False
SESSION_COOKIE_SECURE = True   # HTTPS required
WTF_CSRF_ENABLED = True

# .env mein:
SECRET_KEY=very_long_random_key_minimum_32_chars
FLASK_ENV=production
```

---

## ❓ Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| MySQL connection error | Start MySQL in XAMPP and verify your .env settings |
| `ImportError: qrcode` | `pip install qrcode[pil]` |
| `ImportError: weasyprint` | Install GTK runtime on Windows (see Step 1) |
| Cannot log in | Re-run `python setup_passwords.py` to reset credentials |
| Permission denied | Verify user role in User Management |

---

*VVM Dharampur School ERP v2.0 — Built with Flask + MySQL*
