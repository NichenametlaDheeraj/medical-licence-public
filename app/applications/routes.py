"""
applications/routes.py
Multi-step wizard for creating and editing drug licence applications.
"""
import json
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, current_app, abort)
from flask_login import login_required, current_user
from app.auth.decorators import admin_required
from app_extensions import db
from app.models.application import Application, ApplicationHistory
from app.models.attachment import Attachment
from app.services.application_service import (
    create_application, update_application, get_application, archive_application
)
from werkzeug.utils import secure_filename
import os

applications_bp = Blueprint('applications', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def _allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_partners(form):
    """Parse array-style partner fields: partner_name[], partner_father[], etc."""
    names   = form.getlist('partner_name[]')
    fathers = form.getlist('partner_father[]')
    addrs   = form.getlist('partner_address[]')
    mobiles = form.getlist('partner_mobile[]')
    emails  = form.getlist('partner_email[]')
    pans    = form.getlist('partner_pan[]')
    roles   = form.getlist('partner_role[]')
    desigs_list = form.getlist('partner_designated[]')
    auths_list  = form.getlist('partner_auth_signatory[]')
    desigs_set  = set(desigs_list)
    auths_set   = set(auths_list)
    id_docs     = form.getlist('partner_id_doc[]')
    ids_raw     = form.getlist('partner_id[]')

    partners = []
    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        idx_str = str(i + 1)
        is_desig = (idx_str in desigs_set) or (len(desigs_list) == len(names) and desigs_list[i] == '1')
        is_auth  = (idx_str in auths_set) or (len(auths_list) == len(names) and auths_list[i] == '1')

        partners.append({
            'id': _safe_int(ids_raw[i] if i < len(ids_raw) else None),
            'partner_number': i + 1,
            'full_name': name,
            'father_husband_name': fathers[i] if i < len(fathers) else '',
            'residential_address': addrs[i] if i < len(addrs) else '',
            'mobile': mobiles[i] if i < len(mobiles) else '',
            'email': emails[i] if i < len(emails) else '',
            'pan': pans[i] if i < len(pans) else '',
            'role': roles[i] if i < len(roles) and roles[i] else 'Partner',
            'is_designated_partner': is_desig,
            'is_authorized_signatory': is_auth,
            'id_doc_details': id_docs[i] if i < len(id_docs) else '',
        })
    return partners


def _parse_building_owners(form):
    """Parse array-style building owner fields."""
    names   = form.getlist('bo_name[]')
    fathers = form.getlist('bo_father[]')
    addrs   = form.getlist('bo_address[]')
    mobiles = form.getlist('bo_mobile[]')
    docs    = form.getlist('bo_ownership_doc[]')
    ids_raw = form.getlist('bo_id[]')

    bos = []
    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        bos.append({
            'id': _safe_int(ids_raw[i] if i < len(ids_raw) else None),
            'full_name': name,
            'father_husband_name': fathers[i] if i < len(fathers) else '',
            'residential_address': addrs[i] if i < len(addrs) else '',
            'mobile': mobiles[i] if i < len(mobiles) else '',
            'ownership_doc_details': docs[i] if i < len(docs) else '',
        })
    return bos


def _parse_pharmacists(form):
    """Parse array-style pharmacist fields."""
    names       = form.getlist('pharma_name[]')
    fathers     = form.getlist('pharma_father[]')
    quals       = form.getlist('pharma_qual[]')
    reg_nos     = form.getlist('pharma_reg_no[]')
    reg_auths   = form.getlist('pharma_reg_auth[]')
    validities  = form.getlist('pharma_reg_validity[]')
    appt_dates  = form.getlist('pharma_appt_date[]')
    statuses    = form.getlist('pharma_status[]')
    mobiles     = form.getlist('pharma_mobile[]')
    emails      = form.getlist('pharma_email[]')
    addrs       = form.getlist('pharma_address[]')
    ids_raw     = form.getlist('pharma_id[]')

    phs = []
    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        phs.append({
            'id': _safe_int(ids_raw[i] if i < len(ids_raw) else None),
            'full_name': name,
            'father_husband_name': fathers[i] if i < len(fathers) else '',
            'qualification': quals[i] if i < len(quals) else '',
            'registration_number': reg_nos[i] if i < len(reg_nos) else '',
            'registration_authority': reg_auths[i] if i < len(reg_auths) else '',
            'registration_validity': _parse_date(validities[i] if i < len(validities) else None),
            'appointment_date': _parse_date(appt_dates[i] if i < len(appt_dates) else None),
            'employment_status': statuses[i] if i < len(statuses) else 'full_time',
            'mobile': mobiles[i] if i < len(mobiles) else '',
            'email': emails[i] if i < len(emails) else '',
            'residential_address': addrs[i] if i < len(addrs) else '',
        })
    return phs


def _safe_int(val):
    try:
        return int(val) if val else None
    except (TypeError, ValueError):
        return None


def _safe_float(val):
    if not val:
        return None
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return None


def _parse_area_value(sqm_raw, sqft_raw):
    sqm = _safe_float(sqm_raw)
    if sqm:
        return sqm
    sqft = _safe_float(sqft_raw)
    if sqft:
        return round(sqft / 10.7639, 2)
    return None


def _parse_declarations(form):
    DECLARATION_KEYS = [
        'prev_occupation', 'prev_drug_licence', 'licence_cancelled',
        'criminal_conviction', 'drug_case', 'dca_compliance', 'rules_understood',
    ]
    decls = []
    for key in DECLARATION_KEYS:
        default_val = 'yes' if key in ('dca_compliance', 'rules_understood') else 'no'
        decls.append({
            'question_key': key,
            'answer': form.get(f'decl_{key}') or default_val,
            'details': form.get(f'decl_{key}_details', ''),
        })
    return decls


def _parse_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _build_data_from_form(form):
    """Extract all form fields into the data dict expected by application_service."""
    data = {
        'application_category': form.get('application_category', 'new_licence'),
        'licence_type': form.get('licence_type', 'retail'),
        'licence_forms': ','.join(form.getlist('licence_forms')),
        'status': form.get('status', 'draft'),
        'business_constitution': form.get('business_constitution', ''),
        'app_date': _parse_date(form.get('app_date')) or date.today(),

        # Business details (flat fields)
        'firm_name': form.get('firm_name'),
        'trading_name': form.get('trading_name'),
        'firm_reg_number': form.get('firm_reg_number'),
        'pan': form.get('pan'),
        'email': form.get('email'),
        'mobile': form.get('mobile'),
        'alternate_contact': form.get('alternate_contact'),
        'commencement_date': _parse_date(form.get('commencement_date')),
        'assessment_number': form.get('assessment_number'),
        'door_number': form.get('door_number'),
        'floor': form.get('floor'),
        'street': form.get('street'),
        'village': form.get('village'),
        'gram_panchayat': form.get('gram_panchayat'),
        'mandal': form.get('mandal'),
        'district': form.get('district'),
        'state': form.get('state'),
        'pincode': form.get('pincode'),
        'full_address': form.get('full_address'),

        # Proprietor
        'proprietor_name': form.get('proprietor_name'),
        'proprietor_father_husband': form.get('proprietor_father_husband'),
        'proprietor_dob': _parse_date(form.get('proprietor_dob')),
        'proprietor_address': form.get('proprietor_address'),
        'proprietor_mobile': form.get('proprietor_mobile'),
        'proprietor_email': form.get('proprietor_email'),
        'proprietor_pan': form.get('proprietor_pan'),
        'proprietor_identity_doc': form.get('proprietor_identity_doc'),

        # LLP
        'llp_name': form.get('llp_name'),
        'llpin': form.get('llpin'),
        'llp_reg_date': _parse_date(form.get('llp_reg_date')),
        'llp_reg_address': form.get('llp_reg_address'),
        'llp_auth_signatory': form.get('llp_auth_signatory'),

        # Company
        'company_name': form.get('company_name'),
        'cin': form.get('cin'),
        'incorporation_date': _parse_date(form.get('incorporation_date')),
        'company_reg_address': form.get('company_reg_address'),
        'company_auth_rep': form.get('company_auth_rep'),
        'company_auth_signatory': form.get('company_auth_signatory'),

        # Partnership deed
        'deed_date': _parse_date(form.get('deed_date')),
        'deed_reg_details': form.get('deed_reg_details'),
        'reg_office_address': form.get('reg_office_address'),

        # Other
        'other_constitution_desc': form.get('other_constitution_desc'),
        'other_constitution_details': form.get('other_constitution_details'),

        # Nested
        'partners': _parse_partners(form),
        'building_owners': _parse_building_owners(form),
        'pharmacists': _parse_pharmacists(form),
        'declarations': _parse_declarations(form),

        'premises': {
            'ownership_type': form.get('ownership_type', 'owned'),
            'shop_name': form.get('shop_name') or form.get('firm_name', ''),
            'assessment_number': form.get('shop_assessment_number', '') or form.get('assessment_number', ''),
            'door_number': form.get('shop_door_number', '') or form.get('door_number', ''),
            'floor': form.get('shop_floor', '') or form.get('floor', ''),
            'street': form.get('shop_street', '') or form.get('street', ''),
            'village': form.get('shop_village', '') or form.get('village', ''),
            'mandal': form.get('shop_mandal', '') or form.get('mandal', ''),
            'district': form.get('shop_district') or form.get('district', ''),
            'state': form.get('shop_state') or form.get('state', 'Andhra Pradesh'),
            'pincode': form.get('shop_pincode') or form.get('pincode', ''),
            'full_address': form.get('shop_address') or form.get('full_address', ''),
            'area_sqm': _parse_area_value(form.get('area_sqm'), form.get('area_sqft')),
            'storage_facilities': form.get('storage_facilities'),
            'ownership_doc_details': form.get('ownership_doc_details'),
            'rent_agreement_details': form.get('rent_agreement_details'),
        },

        'payment': {
            'challan_number': form.get('challan_number', ''),
            'challan_date': _parse_date(form.get('challan_date')),
            'amount': form.get('payment_amount'),
            'bank_name': form.get('bank_name', ''),
            'bank_branch': form.get('bank_branch', ''),
            'payment_status': form.get('payment_status', 'pending'),
            'notes': form.get('payment_notes', ''),
        } if (form.get('challan_number') or form.get('payment_amount')) else None,
    }
    return data


# ── Routes ──────────────────────────────────────────────────────────────────

@applications_bp.route('/')
@login_required
def list_applications():
    query = Application.query.filter_by(is_archived=False)
    if current_user.role != 'admin':
        query = query.filter(Application.created_by == current_user.id)
    apps = query.order_by(Application.updated_at.desc()).all()
    return render_template('applications/list.html', applications=apps)


@applications_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_application():
    if request.method == 'POST':
        data = _build_data_from_form(request.form)
        try:
            app_obj = create_application(data, current_user.id)
            _handle_file_uploads(request.files, app_obj.id)
            flash(f'Application {app_obj.app_number} created successfully!', 'success')
            return redirect(url_for('applications.view_application', app_id=app_obj.id))
        except Exception as e:
            current_app.logger.exception('Error creating application')
            flash(f'Error creating application: {str(e)}', 'danger')
    return render_template('applications/form.html', app=None, is_new=True, today=date.today().isoformat())


@applications_bp.route('/<int:app_id>')
@login_required
def view_application(app_id):
    app_obj = get_application(app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: You can only view your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    return render_template('applications/view.html', app=app_obj)


@applications_bp.route('/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(app_id):
    app_obj = get_application(app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: You can only edit your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        data = _build_data_from_form(request.form)
        try:
            update_application(app_obj, data, current_user.id)
            _handle_file_uploads(request.files, app_obj.id)
            flash(f'Application {app_obj.app_number} updated successfully!', 'success')
            return redirect(url_for('applications.view_application', app_id=app_obj.id))
        except Exception as e:
            current_app.logger.exception('Error updating application')
            flash(f'Error updating application: {str(e)}', 'danger')
    return render_template('applications/form.html', app=app_obj, is_new=False, today=date.today().isoformat())


@applications_bp.route('/<int:app_id>/archive', methods=['POST'])
@admin_required
def archive(app_id):
    app_obj = get_application(app_id)
    if not app_obj:
        abort(404)
    archive_application(app_obj, current_user.id)
    flash(f'Application {app_obj.app_number} has been archived.', 'info')
    return redirect(url_for('dashboard.index'))


@applications_bp.route('/<int:app_id>/delete', methods=['POST'])
@admin_required
def delete_application(app_id):
    app_obj = get_application(app_id)
    if not app_obj:
        abort(404)
    app_num = app_obj.app_number
    db.session.delete(app_obj)
    db.session.commit()
    flash(f'Application {app_num} permanently deleted.', 'warning')
    return redirect(url_for('dashboard.index'))


@applications_bp.route('/<int:app_id>/approve', methods=['POST'])
@admin_required
def approve_application(app_id):
    app_obj = get_application(app_id)
    if not app_obj:
        abort(404)
    app_obj.status = 'ready'
    h = ApplicationHistory(
        application_id=app_obj.id,
        action='approved',
        description='Application approved by administrator',
        changed_by=current_user.id
    )
    db.session.add(h)
    db.session.commit()
    flash(f'Application {app_obj.app_number} marked as Approved / Ready for Review.', 'success')
    return redirect(url_for('applications.view_application', app_id=app_obj.id))


@applications_bp.route('/<int:app_id>/duplicate', methods=['POST'])
@login_required
def duplicate_application(app_id):
    src = get_application(app_id)
    if not src:
        abort(404)
    if current_user.role != 'admin' and src.created_by != current_user.id:
        flash('Access denied: You can only duplicate your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    # Build data dict from source
    bd = src.business_details
    data = {
        'licence_category': src.licence_category,
        'licence_type': src.licence_type,
        'licence_forms': src.licence_forms,
        'status': 'draft',
        'business_constitution': src.business_constitution,
        'app_date': date.today(),
    }
    if bd:
        for col in bd.__table__.columns:
            if col.name not in ('id', 'application_id'):
                data[col.name] = getattr(bd, col.name)

    data['partners'] = [p.to_dict() for p in src.partners]
    data['pharmacists'] = [p.to_dict() for p in src.pharmacists]
    data['building_owners'] = [b.to_dict() for b in src.building_owners]
    data['declarations'] = [d.to_dict() for d in src.declarations]
    if src.premises:
        data['premises'] = src.premises.to_dict()
    if src.payments:
        data['payment'] = src.payments[0].to_dict()

    new_app = create_application(data, current_user.id)
    flash(f'Application duplicated as {new_app.app_number}.', 'success')
    return redirect(url_for('applications.edit_application', app_id=new_app.id))


def _handle_file_uploads(files, app_id):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    app_folder = os.path.join(upload_folder, str(app_id))
    os.makedirs(app_folder, exist_ok=True)

    for field_name, file in files.items():
        if file and file.filename and _allowed_file(file.filename):
            sf = secure_filename(file.filename)
            stored = f"{field_name}_{sf}"
            file.save(os.path.join(app_folder, stored))
            att = Attachment(
                application_id=app_id,
                document_type=field_name,
                original_filename=file.filename,
                stored_filename=os.path.join(str(app_id), stored),
                file_size=os.path.getsize(os.path.join(app_folder, stored)),
                uploaded_by=current_user.id if (current_user and current_user.is_authenticated) else 1,
            )
            db.session.add(att)
    db.session.commit()


@applications_bp.route('/<int:app_id>/download-attachment/<int:att_id>')
@login_required
def download_attachment(app_id, att_id):
    from flask import send_from_directory
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        abort(403)
    att = db.session.get(Attachment, att_id)
    if not att or att.application_id != app_id:
        abort(404)
    folder = current_app.config['UPLOAD_FOLDER']
    directory = os.path.join(folder, str(app_id))
    filename = os.path.basename(att.stored_filename)
    return send_from_directory(directory, filename, as_attachment=True,
                               download_name=att.original_filename)
