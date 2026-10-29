from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from app_extensions import db, login_manager
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash(f'Account "{username}" is disabled. Please contact the administrator.', 'warning')
                return render_template('login.html')
            login_user(user, remember=bool(remember))
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return render_template('register.html', username=username, email=email)

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html', username=username, email=email)

        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', username=username, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', username=username, email=email)

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('register.html', username=username, email=email)

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered. Please log in.', 'danger')
            return render_template('register.html', username=username, email=email)

        # Create user with role='user'
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='user',
            is_active=True,
        )
        db.session.add(new_user)
        db.session.commit()

        # Log in the user
        login_user(new_user)
        new_user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        flash(f'Account created successfully! Welcome, {new_user.username}.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('register.html')


@auth_bp.route('/change-username', methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'POST':
        new_username = request.form.get('new_username', '').strip()
        password = request.form.get('password', '')

        if not new_username:
            flash('Please enter a new username.', 'warning')
            return render_template('change_username.html')

        if len(new_username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return render_template('change_username.html')

        if len(new_username) > 80:
            flash('Username cannot exceed 80 characters.', 'danger')
            return render_template('change_username.html')

        if new_username.lower() == current_user.username.lower():
            flash('New username is the same as your current username.', 'info')
            return render_template('change_username.html')

        # Check if username already exists across other users
        existing_user = User.query.filter(
            User.username.ilike(new_username),
            User.id != current_user.id
        ).first()
        if existing_user:
            flash(f'Username "{new_username}" is already taken. Please choose another.', 'danger')
            return render_template('change_username.html')

        # Verify current password
        if not check_password_hash(current_user.password_hash, password):
            flash('Incorrect password. Please verify your current password to change username.', 'danger')
            return render_template('change_username.html')

        old_username = current_user.username
        current_user.username = new_username
        db.session.commit()
        flash(f'Your username has been changed successfully from "{old_username}" to "{new_username}"!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('change_username.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('change_password.html')

        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Your password has been changed successfully!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('change_password.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        if not identifier:
            flash('Please enter your username or registered email address.', 'warning')
            return render_template('forgot_password.html')

        user = User.query.filter(
            (User.username.ilike(identifier)) | (User.email.ilike(identifier))
        ).first()

        if not user:
            flash('No account found with that username or email address.', 'danger')
            return render_template('forgot_password.html')

        if not user.is_active:
            flash(f'Account "{user.username}" is disabled. Please contact the administrator.', 'warning')
            return render_template('forgot_password.html')

        # Generate timed password reset token (valid for 30 minutes)
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = serializer.dumps(user.email, salt='password-reset-salt')

        flash(f'Identity confirmed for "{user.username}". Please choose your new password below.', 'info')
        return redirect(url_for('auth.reset_password', token=token))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)  # 30 mins
    except (SignatureExpired, BadTimeSignature, BadSignature):
        flash('The password reset link is invalid or has expired. Please try again.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('reset_password.html', user=user, token=token)

        if new_password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('reset_password.html', user=user, token=token)

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Password reset successfully! You can now sign in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', user=user, token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
