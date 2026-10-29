"""
app/__init__.py — Flask Application Package & Factory
"""
import os
import logging
from datetime import datetime, timezone
from flask import Flask
from app_extensions import db, login_manager, csrf
from config import config


def create_app(config_name='default'):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])

    # Ensure required folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.applications.routes import applications_bp
    from app.exports.routes import exports_bp
    from app.pdf_generator.routes import pdf_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(applications_bp, url_prefix='/applications')
    app.register_blueprint(exports_bp, url_prefix='/exports')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Template filters
    @app.template_filter('format_local_time')
    def format_local_time_filter(dt, fmt='%d/%m/%Y %I:%M %p'):
        if not dt:
            return '—'
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                return dt
        if dt.tzinfo is None:
            # Naive datetime from DB stored as UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime(fmt)

    # Error handlers
    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('404.html'), 500

    with app.app_context():
        db.create_all()
        _seed_users(app)

    return app


def _seed_users(app):
    """Create default admin and standard user on first run."""
    from app.models.user import User
    from werkzeug.security import generate_password_hash

    # 1. Admin user
    admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
    if not admin:
        admin = User(
            username=app.config['ADMIN_USERNAME'],
            email=app.config['ADMIN_EMAIL'],
            password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
            role='admin',
            is_active=True,
        )
        db.session.add(admin)
        app.logger.info('Admin user created: %s', app.config['ADMIN_USERNAME'])

    # 2. Standard user
    std_user = User.query.filter_by(username='user').first()
    if not std_user:
        std_user = User(
            username='user',
            email='user@medicalagency.com',
            password_hash=generate_password_hash('user123'),
            role='user',
            is_active=True,
        )
        db.session.add(std_user)
        app.logger.info('Standard user created: user')

    db.session.commit()
