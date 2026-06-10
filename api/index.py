import os
import sys
import traceback

# Add parent directory (project root) to sys.path so Flask can find local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app
except Exception as e:
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        tb = traceback.format_exc()
        return f"""
        <html>
        <head>
            <title>Vercel Startup Debugger</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f1f5f9; padding: 40px; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
                h1 {{ color: #ef4444; margin-top: 0; font-size: 24px; }}
                pre {{ background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #1e293b; overflow-x: auto; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 14px; color: #fda4af; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛑 Application Startup Failed</h1>
                <p>The Flask application failed to import or initialize on Vercel. Here is the traceback:</p>
                <pre>{tb}</pre>
                <p style="color: #94a3b8; font-size: 13px;">Please share this error traceback to help diagnose the issue.</p>
            </div>
        </body>
        </html>
        """, 500

