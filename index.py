"""
index.py — Vercel Serverless Function entry point for Flask WSGI
"""
import os
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Detect Vercel / AWS Lambda serverless execution environment
is_serverless = bool(
    os.environ.get('VERCEL')
    or os.environ.get('VERCEL_ENV')
    or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    or os.environ.get('LAMBDA_TASK_ROOT')
    or os.environ.get('IS_VERCEL')
    or os.path.exists('/var/task')
)

if is_serverless:
    os.environ['IS_VERCEL'] = '1'
    dest_db = '/tmp/medical_agency.db'
    src_db = os.path.join(BASE_DIR, 'instance', 'medical_agency.db')
    if not os.path.exists(src_db):
        src_db = os.path.join(BASE_DIR, 'medical_agency.db')
    os.makedirs('/tmp', exist_ok=True)
    # Check if src_db is newer or dest_db does not exist
    should_copy = not os.path.exists(dest_db)
    if not should_copy and os.path.exists(src_db):
        try:
            if os.path.getmtime(src_db) > os.path.getmtime(dest_db):
                should_copy = True
        except Exception:
            pass

    if should_copy and os.path.exists(src_db):
        shutil.copyfile(src_db, dest_db)
        try:
            os.chmod(dest_db, 0o666)
        except Exception:
            pass
    elif os.path.exists(dest_db):
        try:
            os.chmod(dest_db, 0o666)
        except Exception:
            pass
    os.makedirs('/tmp/uploads', exist_ok=True)
    os.makedirs('/tmp/generated_documents', exist_ok=True)

from app import create_app

app = create_app('production')

if __name__ == '__main__':
    app.run()
