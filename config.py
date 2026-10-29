import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Detect Vercel serverless environment (/tmp writeable path)
    IS_VERCEL = bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        or os.environ.get('LAMBDA_TASK_ROOT')
        or os.environ.get('IS_VERCEL')
        or os.path.exists('/var/task')
    )

    if IS_VERCEL:
        # On Vercel / serverless environments, files outside /tmp are read-only.
        # Ensure SQLite and file storage always use writable /tmp directories.
        db_url = os.environ.get('DATABASE_URL', '')
        if not db_url or 'sqlite' in db_url:
            SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/medical_agency.db'
        else:
            SQLALCHEMY_DATABASE_URI = db_url

        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
        if not UPLOAD_FOLDER.startswith('/tmp'):
            UPLOAD_FOLDER = '/tmp/uploads'

        GENERATED_FOLDER = os.environ.get('GENERATED_FOLDER', '/tmp/generated_documents')
        if not GENERATED_FOLDER.startswith('/tmp'):
            GENERATED_FOLDER = '/tmp/generated_documents'
    else:
        _instance_db = os.path.join(BASE_DIR, 'instance', 'medical_agency.db')
        _default_db = _instance_db if os.path.exists(_instance_db) else os.path.join(BASE_DIR, 'medical_agency.db')
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + _default_db)
        UPLOAD_FOLDER = os.path.join(BASE_DIR, os.environ.get('UPLOAD_FOLDER', 'uploads'))
        GENERATED_FOLDER = os.path.join(BASE_DIR, os.environ.get('GENERATED_FOLDER', 'generated_documents'))

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
    WTF_CSRF_ENABLED = True
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

    # Admin seeding
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@medicalagency.com')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
