from flask_login import UserMixin
from db import db

# ── Roles Definition ─────────────────────────────────────────
ROLES = {
    'admin':      {'label': 'Administrator', 'level': 4, 'color': '#00D4FF'},
    'accountant': {'label': 'Accountant',    'level': 3, 'color': '#F5C842'},
    'teacher':    {'label': 'Teacher',       'level': 2, 'color': '#10E87B'},
    'student':    {'label': 'Student',       'level': 1, 'color': '#7C6FEF'},
    'parent':     {'label': 'Parent',        'level': 1, 'color': '#FF8C42'},
}

# ── Permissions ───────────────────────────────────────────────
PERMISSIONS = {
    'admin': [
        'view_dashboard', 'manage_students', 'manage_fees',
        'manage_teachers', 'manage_transport', 'manage_exams',
        'manage_attendance', 'manage_idcard', 'manage_reports',
        'manage_noticeboard', 'manage_users', 'manage_settings',
        'view_portal',
    ],
    'accountant': [
        'view_dashboard', 'manage_fees', 'manage_reports',
        'view_students', 'manage_salary',
    ],
    'teacher': [
        'view_dashboard', 'manage_attendance', 'manage_exams',
        'view_students',
    ],
    'student': ['view_portal'],
    'parent':  ['view_portal'],
}

class User(UserMixin):
    """Flask-Login User class — loads from `users` table."""

    def __init__(self, user_dict):
        self.id          = user_dict['id']
        self.username    = user_dict['username']
        self.email       = user_dict.get('email', '')
        self.role        = user_dict['role']
        self.full_name   = user_dict.get('full_name', '')
        self.is_active_  = bool(user_dict.get('is_active', True))
        self.student_id  = user_dict.get('student_id')    # for student role
        self.teacher_id  = user_dict.get('teacher_id')   # for teacher role

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_

    def has_permission(self, perm):
        return perm in PERMISSIONS.get(self.role, [])

    def has_role(self, *roles):
        return self.role in roles

    @property
    def role_label(self):
        return ROLES.get(self.role, {}).get('label', self.role)

    @property
    def role_color(self):
        return ROLES.get(self.role, {}).get('color', '#888')

    @staticmethod
    def get(user_id):
        """Load user by ID — used by Flask-Login user_loader."""
        try:
            cur = db.connection.cursor()
            cur.execute("SELECT * FROM users WHERE id=%s AND is_active=true", (user_id,))
            row = cur.fetchone()
            cur.close()
            return User(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_by_username(username):
        try:
            cur = db.connection.cursor()
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            row = cur.fetchone()
            cur.close()
            return User(row) if row else None
        except Exception:
            return None
