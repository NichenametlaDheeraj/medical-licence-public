"""
app/auth/decorators.py — Role-based access control decorators
"""
from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if getattr(current_user, 'role', None) != 'admin':
            flash('Access denied: Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function
