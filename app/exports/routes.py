"""
exports/routes.py
Routes for downloading Excel workbooks.
"""
import os
from datetime import datetime, timezone
from flask import Blueprint, redirect, url_for, flash, send_file, current_app, abort
from flask_login import login_required, current_user
from app_extensions import db
from app.models.application import Application
from app.services.excel_service import export_to_excel

exports_bp = Blueprint('exports', __name__)


@exports_bp.route('/application/<int:app_id>')
@login_required
def export_single(app_id):
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        flash(f'Application #{app_id} was not found.', 'warning')
        return redirect(url_for('dashboard.index'))
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: You can only export your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    return _do_export([app_obj], f'application_{app_obj.app_number}')


@exports_bp.route('/all')
@login_required
def export_all():
    query = Application.query.filter_by(is_archived=False)
    if current_user.role != 'admin':
        query = query.filter(Application.created_by == current_user.id)
    apps = query.order_by(Application.updated_at.desc()).all()
    label = 'my_applications' if current_user.role != 'admin' else 'all_applications'
    return _do_export(apps, label)


@exports_bp.route('/status')
@login_required
def export_status():
    """Returns JSON status of current user's or admin's exported Excel file."""
    folder = current_app.config['GENERATED_FOLDER']
    label = 'all_applications' if current_user.role == 'admin' else 'my_applications'
    server_filename = 'all_applications.xlsx' if current_user.role == 'admin' else f'my_applications_user_{current_user.id}.xlsx'
    download_name = 'all_applications.xlsx' if current_user.role == 'admin' else 'my_applications.xlsx'
    path = os.path.join(folder, server_filename)

    exists = os.path.exists(path)
    updated_at = None
    file_size = 0
    if exists:
        mtime = os.path.getmtime(path)
        updated_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        file_size = os.path.getsize(path)

    return {
        'has_exported': exists,
        'label': label,
        'download_name': download_name,
        'updated_at': updated_at,
        'file_size': file_size,
        'user_id': current_user.id,
        'role': current_user.role
    }


def _do_export(apps, label):
    folder = current_app.config['GENERATED_FOLDER']
    os.makedirs(folder, exist_ok=True)

    # Deterministic filenames: update the existing file in place
    if label == 'all_applications':
        server_filename = 'all_applications.xlsx'
        download_name = 'all_applications.xlsx'
    elif label == 'my_applications':
        server_filename = f'my_applications_user_{current_user.id}.xlsx'
        download_name = 'my_applications.xlsx'
    else:
        server_filename = f'{label}.xlsx'
        download_name = f'{label}.xlsx'

    path = os.path.join(folder, server_filename)
    try:
        export_to_excel(apps, path)
        response = send_file(
            path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response.headers['X-Export-Name'] = download_name
        response.headers['X-Export-Label'] = label
        return response
    except Exception as e:
        current_app.logger.exception('Excel export failed')
        flash(f'Excel export failed: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))
