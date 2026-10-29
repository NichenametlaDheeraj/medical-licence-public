"""
application_service.py
Business logic for creating, updating, and retrieving applications.
"""
from datetime import date, datetime, timezone
from app_extensions import db
from app.models.application import Application, ApplicationHistory
from app.models.business_details import BusinessDetails
from app.models.partner import Partner
from app.models.premises import Premises
from app.models.building_owner import BuildingOwner
from app.models.pharmacist import Pharmacist
from app.models.declaration import Declaration
from app.models.payment import Payment
from app.models.generated_document import GeneratedDocument


def _generate_app_number():
    year = date.today().year
    prefix = f'MED-{year}-'
    last = Application.query.filter(
        Application.app_number.like(f'{prefix}%')
    ).order_by(Application.id.desc()).first()
    if last:
        seq = int(last.app_number.split('-')[-1]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'


def create_application(data: dict, user_id: int) -> Application:
    app = Application(
        app_number=_generate_app_number(),
        app_date=data.get('app_date') or date.today(),
        licence_category=data.get('application_category', data.get('licence_category', 'new_licence')),
        licence_type=data.get('licence_type', 'retail'),
        licence_forms=data.get('licence_forms', ''),
        status='draft',
        business_constitution=data.get('business_constitution', ''),
        created_by=user_id,
    )
    db.session.add(app)
    db.session.flush()  # get app.id

    _upsert_business(app, data)
    _upsert_premises(app, data)
    _sync_partners(app, data.get('partners', []))
    _sync_building_owners(app, data.get('building_owners', []))
    _sync_pharmacists(app, data.get('pharmacists', []))
    _sync_declarations(app, data.get('declarations', []))
    _upsert_payment(app, data)

    _add_history(app, 'created', 'Application created', user_id)
    db.session.commit()
    return app


def update_application(app: Application, data: dict, user_id: int) -> Application:
    app.licence_category = data.get('application_category', data.get('licence_category', app.licence_category))
    app.licence_type = data.get('licence_type', app.licence_type)
    app.licence_forms = data.get('licence_forms', app.licence_forms)
    app.status = data.get('status', app.status)
    app.business_constitution = data.get('business_constitution', app.business_constitution)
    app.updated_at = datetime.now(timezone.utc)

    _upsert_business(app, data)
    _upsert_premises(app, data)
    _sync_partners(app, data.get('partners', []))
    _sync_building_owners(app, data.get('building_owners', []))
    _sync_pharmacists(app, data.get('pharmacists', []))
    _sync_declarations(app, data.get('declarations', []))
    _upsert_payment(app, data)

    # Mark existing generated docs as outdated
    for doc in app.generated_documents:
        if doc.status == 'current':
            doc.status = 'outdated'

    _add_history(app, 'updated', 'Application updated', user_id)
    db.session.commit()
    return app


def archive_application(app: Application, user_id: int):
    app.is_archived = True
    app.status = 'archived'
    _add_history(app, 'archived', 'Application archived', user_id)
    db.session.commit()


def get_application(app_id: int) -> Application | None:
    return db.session.get(Application, app_id)


# ── helpers ────────────────────────────────────────────────────────────────

def _upsert_business(app, data):
    bd = app.business_details
    if not bd:
        bd = BusinessDetails(application_id=app.id)
        db.session.add(bd)
        app.business_details = bd

    # Alias form field names to model column names
    aliases = {
        'alternate_contact': 'alt_contact',
        'proprietor_address': 'proprietor_residential_address',
        'llp_reg_date': 'llp_registration_date',
        'llp_reg_address': 'llp_registered_office',
        'llp_auth_signatory': 'llp_authorized_signatory',
        'company_reg_address': 'company_registered_office',
        'company_auth_rep': 'company_authorized_signatory',
        'deed_reg_details': 'deed_registration_details',
        'reg_office_address': 'deed_registered_office',
        'proprietor_identity_doc': 'proprietor_id_doc_details',
        'application_category': None,  # stored on Application, not BusinessDetails
    }

    fields = [
        'firm_name', 'trading_name', 'firm_reg_number', 'pan', 'email',
        'mobile', 'alt_contact', 'alternate_contact', 'assessment_number',
        'door_number', 'floor', 'street', 'village', 'gram_panchayat',
        'mandal', 'district', 'state', 'pincode', 'full_address',
        'proprietor_name', 'proprietor_father_husband', 'proprietor_dob',
        'proprietor_residential_address', 'proprietor_address',
        'proprietor_mobile', 'proprietor_email',
        'proprietor_pan', 'proprietor_id_doc_details', 'proprietor_identity_doc',
        'llp_name', 'llpin', 'llp_registration_date', 'llp_reg_date',
        'llp_registered_office', 'llp_reg_address', 'llp_authorized_signatory', 'llp_auth_signatory',
        'company_name', 'cin', 'incorporation_date',
        'company_registered_office', 'company_reg_address',
        'company_authorized_signatory', 'company_auth_rep', 'company_auth_signatory',
        'deed_date', 'deed_registration_details', 'deed_reg_details',
        'deed_registered_office', 'reg_office_address',
        'other_constitution_desc', 'other_constitution_details', 'commencement_date',
    ]
    for f in fields:
        if f not in data:
            continue
        target = aliases.get(f, f)
        if target is None:
            continue
        if hasattr(bd, target):
            setattr(bd, target, data[f] or None)


def _upsert_premises(app, data):
    if 'premises' not in data:
        return
    pd = data['premises']
    p = app.premises
    if not p:
        p = Premises(application_id=app.id)
        db.session.add(p)
        app.premises = p
    fields = [
        'ownership_type', 'shop_name', 'assessment_number', 'door_number',
        'floor', 'street', 'village', 'gram_panchayat', 'mandal', 'district',
        'state', 'pincode', 'area_sqm', 'full_address', 'storage_facilities',
        'ownership_doc_details', 'rent_agreement_details',
    ]
    for f in fields:
        if f in pd and hasattr(p, f):
            setattr(p, f, pd[f] or None)
    # Handle shop address aliases
    if 'shop_address' in pd and pd['shop_address']:
        p.full_address = pd['shop_address']
    elif 'full_address' in pd and pd['full_address']:
        p.full_address = pd['full_address']


def _sync_partners(app, partners_data):
    # Delete all existing and re-insert to keep ordering clean
    for p in list(app.partners):
        db.session.delete(p)
    db.session.flush()
    for idx, pd in enumerate(partners_data, start=1):
        partner = Partner(
            application_id=app.id,
            partner_number=idx,
            full_name=pd.get('full_name'),
            father_husband_name=pd.get('father_husband_name'),
            residential_address=pd.get('residential_address'),
            mobile=pd.get('mobile'),
            email=pd.get('email'),
            pan=pd.get('pan'),
            role=pd.get('role'),
            is_designated_partner=pd.get('is_designated_partner', False),
            is_authorized_signatory=pd.get('is_authorized_signatory', False),
            id_doc_details=pd.get('id_doc_details'),
        )
        db.session.add(partner)


def _sync_building_owners(app, bos_data):
    for bo in list(app.building_owners):
        db.session.delete(bo)
    db.session.flush()
    for bod in bos_data:
        bo = BuildingOwner(
            application_id=app.id,
            full_name=bod.get('full_name'),
            father_husband_name=bod.get('father_husband_name'),
            residential_address=bod.get('residential_address'),
            mobile=bod.get('mobile'),
            ownership_doc_details=bod.get('ownership_doc_details'),
        )
        db.session.add(bo)


def _sync_pharmacists(app, ph_data):
    for ph in list(app.pharmacists):
        db.session.delete(ph)
    db.session.flush()
    for phd in ph_data:
        ph = Pharmacist(
            application_id=app.id,
            full_name=phd.get('full_name'),
            father_husband_name=phd.get('father_husband_name'),
            qualification=phd.get('qualification'),
            registration_number=phd.get('registration_number'),
            registration_authority=phd.get('registration_authority'),
            registration_validity=phd.get('registration_validity') or None,
            residential_address=phd.get('residential_address'),
            mobile=phd.get('mobile'),
            email=phd.get('email'),
            appointment_date=phd.get('appointment_date') or None,
            employment_status=phd.get('employment_status'),
        )
        db.session.add(ph)


def _sync_declarations(app, decl_data):
    existing = {d.question_key: d for d in app.declarations}
    for dd in decl_data:
        key = dd.get('question_key')
        if not key:
            continue
        if key in existing:
            d = existing[key]
        else:
            d = Declaration(application_id=app.id, question_key=key)
            db.session.add(d)
        d.question_text = dd.get('question_text', d.question_text)
        d.answer = dd.get('answer')
        d.details = dd.get('details')


def _upsert_payment(app, data):
    pd = data.get('payment')
    if not pd or not isinstance(pd, dict):
        return
    if app.payments:
        p = app.payments[0]
    else:
        p = Payment(application_id=app.id)
        db.session.add(p)
    p.challan_number = pd.get('challan_number', p.challan_number)
    p.challan_date = pd.get('challan_date') or p.challan_date
    p.amount = pd.get('amount', p.amount)
    p.payment_status = pd.get('payment_status', p.payment_status or 'pending')
    p.payment_reference = pd.get('payment_reference', p.payment_reference)


def _add_history(app, action, description, user_id):
    h = ApplicationHistory(
        application_id=app.id,
        action=action,
        description=description,
        changed_by=user_id,
    )
    db.session.add(h)
