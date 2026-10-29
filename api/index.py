"""
api/index.py — Vercel Serverless Function entry point for Flask WSGI
"""
import os
import sys
import shutil

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# If running on Vercel, copy database and create required folders in /tmp
if 'VERCEL' in os.environ or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    dest_db = '/tmp/medical_agency.db'
    src_db = os.path.join(BASE_DIR, 'instance', 'medical_agency.db')
    if not os.path.exists(dest_db):
        os.makedirs('/tmp', exist_ok=True)
        if os.path.exists(src_db):
            shutil.copy2(src_db, dest_db)
    os.makedirs('/tmp/uploads', exist_ok=True)
    os.makedirs('/tmp/generated_documents', exist_ok=True)

from app import create_app

app = create_app('production')

if __name__ == '__main__':
    app.run()
