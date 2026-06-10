import os
import sys
import traceback

# Add parent directory (project root) to sys.path so Flask can find local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing the real app, capture any crash
_startup_error = None
try:
    from app import app
except Exception:
    _startup_error = traceback.format_exc()
    from flask import Flask
    app = Flask(__name__)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return f"<h1>Startup Error</h1><pre>{_startup_error}</pre>", 500
