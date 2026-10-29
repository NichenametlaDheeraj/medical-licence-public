"""
app/admin/routes.py — Administrator routes for User Management, Audit Logs, and System Config
"""
import os
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   current_app, abort)
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app_extensions import db
from app.auth.decorators import admin_required
from app.models.user import User
from app.models.application import Application, ApplicationHistory
from app.models.generated_document import GeneratedDocument
from app.models.attachment import Attachment

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users', methods=['GET'])
@admin_required
def users():
    # Show only users who have logged in, ordered by most recent login
    user_list = User.query.filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).all()
    return render_template('admin/users.html', users=user_list)


@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')

    if not username or not email or not password:
        flash('Username, email, and password are required.', 'danger')
        return redirect(url_for('admin.users'))

    if User.query.filter_by(username=username).first():
        flash(f'Username "{username}" already exists.', 'danger')
        return redirect(url_for('admin.users'))

    if User.query.filter_by(email=email).first():
        flash(f'Email "{email}" already registered.', 'danger')
        return redirect(url_for('admin.users'))

    new_user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role if role in ('admin', 'user') else 'user',
        is_active=True,
    )
    db.session.add(new_user)
    db.session.commit()
    flash(f'User "{username}" created successfully with role "{new_user.role}".', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    if user_id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.users'))

    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.is_active = not user.is_active
    db.session.commit()
    status_str = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.username}" has been {status_str}.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'danger')
        return redirect(url_for('admin.users'))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash(f'Password for "{user.username}" updated successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def audit_logs():
    q = request.args.get('q', '').strip()
    action = request.args.get('action', '').strip()

    query = ApplicationHistory.query.join(Application)

    if q:
        query = query.filter(
            (Application.app_number.ilike(f'%{q}%')) |
            (ApplicationHistory.description.ilike(f'%{q}%'))
        )
    if action:
        query = query.filter(ApplicationHistory.action == action)

    logs = query.order_by(ApplicationHistory.created_at.desc()).limit(100).all()
    actions = db.session.query(ApplicationHistory.action).distinct().all()
    distinct_actions = [a[0] for a in actions if a[0]]

    return render_template('admin/audit_logs.html', logs=logs, q=q,
                           current_action=action, distinct_actions=distinct_actions)
