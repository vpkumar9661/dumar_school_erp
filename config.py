import os
from dotenv import load_dotenv

load_dotenv()   # Load .env file

class Config:
    # ── Security ────────────────────────────────────────────
    SECRET_KEY             = os.getenv('SECRET_KEY', 'dev_secret_change_in_production')
    WTF_CSRF_ENABLED       = True
    SESSION_COOKIE_HTTPONLY= True
    SESSION_COOKIE_SAMESITE= 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour session timeout

    # ── Supabase PostgreSQL ──────────────────────────────────
    DATABASE_URL = os.getenv('DATABASE_URL', '')

    # ── Supabase Storage ─────────────────────────────────────
    SUPABASE_URL      = os.getenv('SUPABASE_URL', '')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

    # ── File Upload ──────────────────────────────────────────
    BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
    # Render & Vercel use ephemeral filesystems — write to /tmp
    if os.environ.get('RENDER') or os.environ.get('VERCEL') == '1':
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads', 'students')
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'students')

    # ── Production detection (Render sets RENDER=true automatically) ──
    IS_PRODUCTION = bool(os.environ.get('RENDER') or os.environ.get('PORT'))
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # True on Render (HTTPS)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # ── School Info ──────────────────────────────────────────
    SCHOOL_NAME    = os.getenv('SCHOOL_NAME', 'Vivekanand Vidya Mandir Dharampur')
    SCHOOL_ADDRESS = os.getenv('SCHOOL_ADDRESS', 'Dharampur, Tatijhariya Hazaribagh,Jharkhand')
    SCHOOL_PHONE   = os.getenv('SCHOOL_PHONE', '7070373801')
    SCHOOL_EMAIL   = os.getenv('SCHOOL_EMAIL', 'deepak7070@gmail.com')

    # ── Rate Limiting ────────────────────────────────────────
    RATELIMIT_DEFAULT          = '200 per day;50 per hour'
    RATELIMIT_STORAGE_URL      = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')

    # ── OpenAI (optional chatbot) ────────────────────────────
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    # ── Classes ──────────────────────────────────────────────
    CLASSES  = ['Nursery','LKG','UKG','1','2','3','4','5',
                '6','7','8','9','10','11','12']
    SECTIONS = ['A','B','C','D','E']
    MONTHS   = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']
