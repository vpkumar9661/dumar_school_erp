"""
VVM Dharampur School ERP v2.0 — Quick Start
Run: python run.py
Then open: http://localhost:5000
Default login: admin / Admin@123
"""
import os
from app import app

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Check if we are in production (based on PORT or a specific flag)
    is_prod = os.environ.get('PORT') is not None
    
    if not is_prod:
        print("=" * 55)
        print("  Vivekanand Vidya Mandir Dharampur ERP v2.0")
        print("  Secure | Role-Based | Production-Ready")
        print("=" * 55)
        print(f"  URL:      http://localhost:{port}")
        print("  Admin:    admin / Admin@123")
        print("=" * 55)
    
    # Run the app
    app.run(debug=(not is_prod), host='0.0.0.0', port=port)