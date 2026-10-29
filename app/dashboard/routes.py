from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app_extensions import db
from app.models.application import Application
from app.models.generated_document import GeneratedDocument
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    constitution_filter = request.args.get('constitution', '')
    licence_filter = request.args.get('licence_type', '')

    query = Application.query.filter_by(is_archived=False)

    # Scoped access: non-admin users only see their own applications
    if current_user.role != 'admin':
        query = query.filter(Application.created_by == current_user.id)

    if q:
        query = query.join(Application.business_details, isouter=True)
        from app.models.business_details import BusinessDetails
        query = query.filter(
            db.or_(
                Application.app_number.ilike(f'%{q}%'),
                BusinessDetails.firm_name.ilike(f'%{q}%'),
                BusinessDetails.mobile.ilike(f'%{q}%'),
                BusinessDetails.proprietor_name.ilike(f'%{q}%'),
            )
        )

    if status_filter:
        query = query.filter(Application.status == status_filter)
    if constitution_filter:
        query = query.filter(Application.business_constitution == constitution_filter)
    if licence_filter:
        query = query.filter(Application.licence_type == licence_filter)

    applications = query.order_by(Application.updated_at.desc()).all()

    # Stats scoped by role
    if current_user.role != 'admin':
        total = Application.query.filter_by(is_archived=False, created_by=current_user.id).count()
        drafts = Application.query.filter_by(status='draft', is_archived=False, created_by=current_user.id).count()
        ready = Application.query.filter_by(status='ready', is_archived=False, created_by=current_user.id).count()
        generated = GeneratedDocument.query.join(Application).filter(
            Application.created_by == current_user.id,
            GeneratedDocument.status == 'current'
        ).count()
        recent = Application.query.filter_by(is_archived=False, created_by=current_user.id).order_by(
            Application.updated_at.desc()).limit(5).all()
    else:
        total = Application.query.filter_by(is_archived=False).count()
        drafts = Application.query.filter_by(status='draft', is_archived=False).count()
        ready = Application.query.filter_by(status='ready', is_archived=False).count()
        generated = GeneratedDocument.query.filter_by(status='current').count()
        recent = Application.query.filter_by(is_archived=False).order_by(
            Application.updated_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        applications=applications,
        total=total,
        drafts=drafts,
        ready=ready,
        generated=generated,
        recent=recent,
        q=q,
        status_filter=status_filter,
        constitution_filter=constitution_filter,
        licence_filter=licence_filter,
    )
