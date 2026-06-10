-- ============================================================
-- VVM Dharampur School ERP v2.0 — PostgreSQL Schema (Supabase)
-- STEPS:
--   1. Paste this in Supabase → SQL Editor → Run
--   2. Then run: python setup_passwords.py
--   3. Then run: python run.py
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    is_active BOOLEAN DEFAULT true,
    student_id INT DEFAULT NULL,
    teacher_id INT DEFAULT NULL,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS login_logs (
    id SERIAL PRIMARY KEY,
    user_id INT,
    username VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent VARCHAR(300),
    status VARCHAR(20) DEFAULT 'failed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    admission_number VARCHAR(20) UNIQUE NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    photo VARCHAR(255) DEFAULT 'default_student.jpg',
    father_name VARCHAR(100) NOT NULL,
    mother_name VARCHAR(100) NOT NULL,
    aadhar_number VARCHAR(12),
    mobile_number VARCHAR(10) NOT NULL,
    address TEXT,
    date_of_birth DATE,
    gender VARCHAR(10) NOT NULL,
    class VARCHAR(10) NOT NULL,
    section VARCHAR(5) NOT NULL,
    roll_number INT,
    admission_date DATE NOT NULL,
    transport_distance VARCHAR(10) DEFAULT 'None',
    transport_fee DECIMAL(10,2) DEFAULT 0.00,
    monthly_fee DECIMAL(10,2) DEFAULT 500.00,
    status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fee_payments (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    receipt_number VARCHAR(20) UNIQUE NOT NULL,
    month VARCHAR(20) NOT NULL,
    year INT NOT NULL,
    months_paid VARCHAR(500) DEFAULT '',
    monthly_fee DECIMAL(10,2) DEFAULT 0.00,
    transport_fee DECIMAL(10,2) DEFAULT 0.00,
    admission_fee DECIMAL(10,2) DEFAULT 0.00,
    development_fee DECIMAL(10,2) DEFAULT 0.00,
    computer_lab_fee DECIMAL(10,2) DEFAULT 0.00,
    science_lab_fee DECIMAL(10,2) DEFAULT 0.00,
    library_fee DECIMAL(10,2) DEFAULT 0.00,
    exam_fee DECIMAL(10,2) DEFAULT 0.00,
    other_fee DECIMAL(10,2) DEFAULT 0.00,
    other_fee_remark VARCHAR(100) DEFAULT '',
    late_fine DECIMAL(10,2) DEFAULT 0.00,
    discount DECIMAL(10,2) DEFAULT 0.00,
    discount_reason VARCHAR(200) DEFAULT '',
    total_amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_mode VARCHAR(20) DEFAULT 'Cash',
    transaction_id VARCHAR(100) DEFAULT '',
    remarks TEXT,
    collected_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    teacher_name VARCHAR(100) NOT NULL,
    subject VARCHAR(100),
    mobile_number VARCHAR(10),
    email VARCHAR(100),
    salary DECIMAL(10,2) DEFAULT 0.00,
    joining_date DATE,
    status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salary_payments (
    id SERIAL PRIMARY KEY,
    teacher_id INT NOT NULL,
    month VARCHAR(20) NOT NULL,
    year INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    deductions DECIMAL(10,2) DEFAULT 0.00,
    net_amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_mode VARCHAR(30) DEFAULT 'Cash',
    remarks TEXT,
    deduction_reason VARCHAR(255) DEFAULT NULL,
    payment_reference VARCHAR(100) DEFAULT NULL,
    paid_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transport_slabs (
    id SERIAL PRIMARY KEY,
    distance_slab VARCHAR(20) UNIQUE NOT NULL,
    fee DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_schedules (
    id SERIAL PRIMARY KEY,
    exam_name VARCHAR(100) NOT NULL,
    class VARCHAR(10) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    exam_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    max_marks INT DEFAULT 100,
    room_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marks (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    exam_id INT NOT NULL,
    marks_obtained DECIMAL(5,2) DEFAULT 0.00,
    grade VARCHAR(5),
    remarks VARCHAR(200),
    entered_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (exam_id) REFERENCES exam_schedules(id) ON DELETE CASCADE,
    UNIQUE (student_id, exam_id)
);

CREATE TABLE IF NOT EXISTS student_attendance (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Present',
    remarks VARCHAR(200),
    marked_by INT DEFAULT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE (student_id, attendance_date)
);

CREATE TABLE IF NOT EXISTS teacher_attendance (
    id SERIAL PRIMARY KEY,
    teacher_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Present',
    remarks VARCHAR(200),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    UNIQUE (teacher_id, attendance_date)
);

CREATE TABLE IF NOT EXISTS notices (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(20) DEFAULT 'General',
    priority VARCHAR(20) DEFAULT 'Normal',
    target_role VARCHAR(20) DEFAULT 'all',
    created_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATE,
    is_public BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    type VARCHAR(20) DEFAULT 'system',
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fee_structure (
    id SERIAL PRIMARY KEY,
    class VARCHAR(10) NOT NULL,
    session VARCHAR(10) NOT NULL DEFAULT '2024-25',
    monthly_fee DECIMAL(10,2) DEFAULT 0.00,
    admission_fee DECIMAL(10,2) DEFAULT 0.00,
    development_fee DECIMAL(10,2) DEFAULT 0.00,
    exam_fee DECIMAL(10,2) DEFAULT 0.00,
    UNIQUE (class, session)
);

CREATE TABLE IF NOT EXISTS gallery_photos (
    id SERIAL PRIMARY KEY,
    caption VARCHAR(255),
    filename VARCHAR(255) NOT NULL,
    category VARCHAR(30) DEFAULT 'Event',
    uploaded_by INT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public_downloads (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    filename VARCHAR(255) NOT NULL,
    category VARCHAR(30) DEFAULT 'Form',
    is_active BOOLEAN DEFAULT true,
    download_count INT DEFAULT 0,
    uploaded_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admission_enquiries (
    id SERIAL PRIMARY KEY,
    student_name VARCHAR(200) NOT NULL,
    father_name VARCHAR(200),
    mobile VARCHAR(15) NOT NULL,
    email VARCHAR(200),
    class_applying VARCHAR(20),
    current_school VARCHAR(200),
    message TEXT,
    status VARCHAR(30) DEFAULT 'New',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── DEFAULT DATA ─────────────────────────────────────────────
INSERT INTO transport_slabs (distance_slab, fee) VALUES
('0-2',300.00),('2-5',500.00),('5-10',800.00),('10+',1200.00)
ON CONFLICT DO NOTHING;

INSERT INTO settings (setting_key, setting_value) VALUES
('school_name','Vivekanand Vidya Mandir Dharampur'),
('school_address','Dharampur, Himachal Pradesh - 176218'),
('school_phone','9999999999'),
('school_email','info@vvmdharampur.edu.in'),
('late_fine_per_day','5'),
('late_fine_after_days','10'),
('current_session','2024-25'),
('monthly_fee_default','500')
ON CONFLICT DO NOTHING;

INSERT INTO teachers (teacher_name,subject,mobile_number,email,salary,joining_date) VALUES
('Ramesh Kumar','Mathematics','9876543210','ramesh@vvm.edu.in',25000.00,'2020-06-01'),
('Sunita Sharma','Science','9876543211','sunita@vvm.edu.in',22000.00,'2021-04-01'),
('Priya Singh','English','9876543212','priya@vvm.edu.in',20000.00,'2022-07-01')
ON CONFLICT DO NOTHING;

INSERT INTO notices (title,content,category,priority,target_role) VALUES
('Welcome to VVM ERP v2.0','School ERP v2.0 installed with Login + RBAC security. Login with your credentials.','General','Important','all')
ON CONFLICT DO NOTHING;

INSERT INTO fee_structure (class,session,monthly_fee,admission_fee,development_fee,exam_fee) VALUES
('Nursery','2024-25',400,1000,500,200),('LKG','2024-25',450,1000,500,200),
('UKG','2024-25',450,1000,500,200),('1','2024-25',500,1500,600,300),
('2','2024-25',500,1500,600,300),('3','2024-25',550,1500,600,300),
('4','2024-25',550,1500,600,300),('5','2024-25',600,2000,700,400),
('6','2024-25',650,2000,700,400),('7','2024-25',650,2000,700,400),
('8','2024-25',700,2000,700,400),('9','2024-25',750,2500,800,500),
('10','2024-25',750,2500,800,500),('11','2024-25',800,3000,900,600),
('12','2024-25',800,3000,900,600)
ON CONFLICT DO NOTHING;

SELECT 'Schema created! Now run: python setup_passwords.py' AS next_step;

-- ── ENABLE ROW LEVEL SECURITY (RLS) FOR ALL TABLES ───────────
-- This secures all tables from client-side REST API access via the public schema.
-- Since the Flask backend accesses the database using direct connection (postgres role),
-- it will bypass RLS automatically, while keeping the client-side API completely secure.
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS login_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS students ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fee_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS teachers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS salary_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS transport_slabs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS exam_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS student_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS teacher_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fee_structure ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS gallery_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public_downloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS admission_enquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS student_password_resets ENABLE ROW LEVEL SECURITY;
