"""
scripts/clean_database.py — Purge test applications and reset storage to fresh 0 state
"""
import os
import sqlite3
import shutil
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'medical_agency.db')

def clean_database():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    tables_to_clear = [
        'application_history',
        'business_details',
        'partners',
        'premises',
        'building_owners',
        'pharmacists',
        'declarations',
        'payments',
        'attachments',
        'generated_documents',
        'applications'
    ]

    for table in tables_to_clear:
        c.execute(f"DELETE FROM {table};")
        print(f"Cleared table: {table}")

    # Reset SQLite autoincrement sequences
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
    if c.fetchone():
        for table in tables_to_clear:
            c.execute("DELETE FROM sqlite_sequence WHERE name=?;", (table,))
        print("Reset sqlite_sequence autoincrement counters to 0")

    # Update/ensure known passwords for user accounts
    admin_pw_hash = generate_password_hash('admin123')
    user_pw_hash = generate_password_hash('user123')
    dheeraj_pw_hash = generate_password_hash('dheeraj123')

    c.execute("UPDATE users SET password_hash = ? WHERE username = 'admin';", (admin_pw_hash,))
    c.execute("UPDATE users SET password_hash = ? WHERE username = 'user';", (user_pw_hash,))
    c.execute("UPDATE users SET password_hash = ? WHERE username = 'dheeraj';", (dheeraj_pw_hash,))

    # Reset last_login to None so Logged In Users table is clean
    c.execute("UPDATE users SET last_login = NULL;")

    conn.commit()
    c.execute("VACUUM;")
    conn.close()
    print("Database vacuumed and closed successfully.")

    # Clean generated_documents directory (keep only empty folder with .gitkeep)
    gen_dir = os.path.join(BASE_DIR, 'generated_documents')
    if os.path.exists(gen_dir):
        for item in os.listdir(gen_dir):
            item_path = os.path.join(gen_dir, item)
            if item == '.gitkeep':
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                try:
                    os.remove(item_path)
                except Exception:
                    pass
        gitkeep = os.path.join(gen_dir, '.gitkeep')
        if not os.path.exists(gitkeep):
            with open(gitkeep, 'w') as f:
                f.write('')
        print("Cleaned generated_documents directory.")

    # Clean uploads directory
    uploads_dir = os.path.join(BASE_DIR, 'uploads')
    if os.path.exists(uploads_dir):
        for item in os.listdir(uploads_dir):
            item_path = os.path.join(uploads_dir, item)
            if item == '.gitkeep':
                continue
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                try:
                    os.remove(item_path)
                except Exception:
                    pass
        gitkeep = os.path.join(uploads_dir, '.gitkeep')
        if not os.path.exists(gitkeep):
            with open(gitkeep, 'w') as f:
                f.write('')
        print("Cleaned uploads directory.")

if __name__ == '__main__':
    clean_database()
