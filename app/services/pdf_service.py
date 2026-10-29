"""
pdf_service.py
Generates official statutory drug licence PDF documents exactly replicating
the layout, wording, attestation photo boxes, two-column From/To headers,
and 15-row declaration table from the DCA statutory draft documents (Draft.pdf).

Includes:
1. Application Letter (Page 1) - Addressed to Licensing Authority in Form 20/21
2. Declaration of Building Owner (Page 2) - With Attested Photo Box & Signature
3. Declaration of Proprietor / Registered Pharmacist (Page 3) - 15-Row Grid with Photo Box
4. Appointment / Acceptance Letter (Page 4) - Appointment statement & Signature
5. Complete Dossier (Draft.pdf) - All 4 pages unified into a single statutory document
"""
import os
from datetime import datetime, timezone, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak
)

from app_extensions import db
from app.models.generated_document import GeneratedDocument


# ─── Styles ──────────────────────────────────────────────────────────────────

def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='DraftSubject',
        fontName='Times-Bold',
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        name='DraftDocTitle',
        fontName='Times-Bold',
        fontSize=11.5,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name='DraftFromTo',
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13.5,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='DraftSalutation',
        fontName='Times-Bold',
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceBefore=6,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name='DraftBody',
        fontName='Times-Roman',
        fontSize=9.5,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        name='DraftBodyIndent',
        fontName='Times-Roman',
        fontSize=9.5,
        leading=14,
        alignment=TA_JUSTIFY,
        firstLineIndent=20,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        name='DraftSignoff',
        fontName='Times-Roman',
        fontSize=9.5,
        leading=14,
        alignment=TA_RIGHT,
    ))

    styles.add(ParagraphStyle(
        name='DraftSignoffCenter',
        fontName='Times-Roman',
        fontSize=9.5,
        leading=14,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='PhotoBoxLabel',
        fontName='Times-Bold',
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
        textColor=black,
    ))

    styles.add(ParagraphStyle(
        name='TableHeaderTitle',
        fontName='Times-Bold',
        fontSize=10,
        leading=13.5,
        alignment=TA_LEFT,
        textColor=black,
    ))

    styles.add(ParagraphStyle(
        name='GridQuestion',
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='GridAnswer',
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='GridAnswerNormal',
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='DraftCertify',
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=8,
    ))

    return styles


# ─── Data Helpers ────────────────────────────────────────────────────────────

def _d(dt):
    if not dt:
        return ''
    if isinstance(dt, datetime):
        return dt.strftime('%d/%m/%Y')
    if isinstance(dt, date):
        return dt.strftime('%d/%m/%Y')
    return str(dt)


def _get_applicant_info(app):
    bd = app.business_details
    firm_name = ''
    if bd and bd.firm_name:
        firm_name = bd.firm_name.strip()
    elif bd and bd.trading_name:
        firm_name = bd.trading_name.strip()
    elif app.premises and app.premises.shop_name:
        firm_name = app.premises.shop_name.strip()
    firm_name = firm_name.replace('M/s ', '').replace('M/s. ', '').strip()

    constitution = (app.business_constitution or 'proprietorship').lower()

    if constitution == 'partnership' and app.partners:
        auth_partner = next((p for p in app.partners if p.is_authorized_signatory), app.partners[0])
        name = (auth_partner.full_name or '').strip()
        father = (auth_partner.father_husband_name or '').strip()
        address = (auth_partner.residential_address or (bd.full_address if bd else '') or '').strip()
        mobile = (auth_partner.mobile or (bd.mobile if bd else '') or '').strip()
        pan = (auth_partner.pan or (bd.pan if bd else '') or '').strip()
        email = (auth_partner.email or (bd.email if bd else '') or '').strip()
    elif bd:
        name = (getattr(bd, 'proprietor_name', None) or '').strip()
        father = (getattr(bd, 'proprietor_father_husband', None) or '').strip()
        address = (getattr(bd, 'proprietor_residential_address', None) or getattr(bd, 'full_address', None) or '').strip()
        mobile = (getattr(bd, 'proprietor_mobile', None) or getattr(bd, 'mobile', None) or '').strip()
        pan = (getattr(bd, 'proprietor_pan', None) or getattr(bd, 'pan', None) or '').strip()
        email = (getattr(bd, 'proprietor_email', None) or getattr(bd, 'email', None) or '').strip()
    else:
        name = ''
        father = ''
        address = ''
        mobile = ''
        pan = ''
        email = ''

    return {
        'name': name,
        'father': father,
        'address': address,
        'mobile': mobile,
        'email': email,
        'pan': pan,
        'firm_name': firm_name or 'Medical Agency',
    }


def _get_premises_info(app):
    prem = app.premises
    bd = app.business_details

    asst_no = (prem.assessment_number if prem and prem.assessment_number else (bd.assessment_number if bd and bd.assessment_number else '') or '').strip()
    door_no = (prem.door_number if prem and prem.door_number else (bd.door_number if bd and bd.door_number else '') or '').strip()
    floor = (prem.floor if prem and prem.floor else (bd.floor if bd and bd.floor else '') or '').strip()
    village = (prem.village if prem and prem.village else (bd.village if bd and bd.village else '') or '').strip()
    mandal = (prem.mandal if prem and prem.mandal else (bd.mandal if bd and bd.mandal else '') or '').strip()
    district = (prem.district if prem and prem.district else (bd.district if bd and bd.district else 'Kadapa') or 'Kadapa').strip()
    state = (prem.state if prem and prem.state else (bd.state if bd and bd.state else 'Andhra Pradesh') or 'Andhra Pradesh').strip()
    pincode = (prem.pincode if prem and prem.pincode else (bd.pincode if bd and bd.pincode else '') or '').strip()

    # Carpet Area in Sq. Mts & Sq. Ft.
    area_sqm_num = prem.area_sqm if (prem and prem.area_sqm) else None
    if area_sqm_num:
        area_sqm_str = f"{area_sqm_num:.2f}".rstrip('0').rstrip('.')
        area_sqft_str = f"{area_sqm_num * 10.7639:.1f}"
    else:
        area_sqm_str = ''
        area_sqft_str = ''

    # Get the user's actual entered full address
    raw_addr = ''
    if prem and prem.full_address and prem.full_address.strip():
        raw_addr = prem.full_address.strip()
    elif bd and bd.full_address and bd.full_address.strip():
        raw_addr = bd.full_address.strip()

    if raw_addr:
        if asst_no and asst_no not in raw_addr:
            full_addr = f"Asst. No. {asst_no}, {raw_addr}"
        else:
            full_addr = raw_addr
    else:
        parts = []
        if asst_no: parts.append(f"Asst. No. {asst_no}")
        if door_no: parts.append(f"D. No. {door_no}")
        if floor: parts.append(floor)
        if village: parts.append(village)
        if mandal: parts.append(f"{mandal} Mandal" if "mandal" not in mandal.lower() else mandal)
        if district: parts.append(f"{district} District" if "district" not in district.lower() else district)
        if pincode: parts.append(f"PIN - {pincode}")
        full_addr = ', '.join(parts) if parts else 'Premises Address'

    return {
        'full_address': full_addr,
        'area_sqm': area_sqm_str,
        'area_sqft': area_sqft_str,
        'district': district,
        'mandal': mandal or district,
        'state': state,
        'pincode': pincode,
        'assessment_number': asst_no,
        'door_number': door_no,
    }


def _get_pharma_info(app):
    if app.pharmacists and len(app.pharmacists) > 0:
        ph = app.pharmacists[0]
        name = (ph.full_name or '').strip()
        father = (ph.father_husband_name or '').strip()
        qual = (ph.qualification or '').strip()
        reg_no = (ph.registration_number or '').strip()
        validity = _d(ph.registration_validity) if ph.registration_validity else ''
        mobile = (ph.mobile or '').strip()
        email = (ph.email or '').strip()
        address = (ph.residential_address or '').strip()

        return {
            'name': name,
            'father': father,
            'qualification': qual or 'B.Pharm / D.Pharm',
            'reg_no': reg_no,
            'validity': validity,
            'mobile': mobile,
            'email': email,
            'address': address,
        }

    return {
        'name': '',
        'father': '',
        'qualification': 'B.Pharm / D.Pharm',
        'reg_no': '',
        'validity': '',
        'mobile': '',
        'email': '',
        'address': '',
    }


def _get_bo_info(app):
    # 1. If building owner was explicitly saved:
    if app.building_owners and len(app.building_owners) > 0:
        bo = app.building_owners[0]
        if getattr(bo, 'full_name', None) and bo.full_name.strip():
            return {
                'name': bo.full_name.strip(),
                'father': (getattr(bo, 'father_husband_name', '') or '').strip(),
                'address': (getattr(bo, 'residential_address', '') or '').strip(),
                'mobile': (getattr(bo, 'mobile', '') or '').strip(),
                'ownership_doc': (getattr(bo, 'ownership_doc_details', '') or 'Sale Deed / Property Tax / Registered Rental Agreement').strip(),
                'is_blank': False,
            }

    # 2. If applicant owns the premises:
    prem = app.premises
    if prem and getattr(prem, 'ownership_type', '') == 'owned':
        applicant = _get_applicant_info(app)
        return {
            'name': applicant['name'],
            'father': applicant['father'],
            'address': applicant['address'],
            'mobile': applicant['mobile'],
            'ownership_doc': getattr(prem, 'ownership_doc_details', '') or 'Sale Deed / Property Tax Receipt',
            'is_blank': False,
        }

    # 3. For rental without pre-filled building owner:
    return {
        'name': '______________________________',
        'father': '______________________________',
        'address': '__________________________________________________________________',
        'mobile': '',
        'ownership_doc': 'Registered Rental Agreement / Ownership Deed',
        'is_blank': True,
    }


def _get_declaration_dict(app):
    res = {
        'prev_occupation': 'Nil',
        'prev_drug_licence': 'No',
        'licence_cancelled': 'No',
        'criminal_conviction': 'No',
        'drug_case': 'No',
        'dca_compliance': 'Yes',
        'rules_understood': 'Yes',
    }
    if app.declarations:
        for d in app.declarations:
            ans = (d.answer or '').strip()
            if ans.lower() == 'yes':
                res[d.question_key] = f'Yes ({d.details})' if d.details else 'Yes'
            elif ans.lower() == 'no':
                res[d.question_key] = 'No'
            elif ans:
                res[d.question_key] = ans
    return res


def _format_from_block(applicant):
    lines = ['<b>From:</b>']
    name_display = applicant['name'].strip()
    if name_display:
        lines.append(f"<b>{name_display}</b>")
    else:
        lines.append('______________________________')
    if applicant['father']:
        lines.append(f"C/o {applicant['father']},")
    addr = applicant['address']
    if addr:
        chunks = [c.strip() for c in addr.split(',') if c.strip()]
        for chunk in chunks:
            lines.append(chunk)
    if applicant['mobile']:
        lines.append(f"Mobile. No: {applicant['mobile']}")
    if applicant['email']:
        lines.append(f"Mail Id: {applicant['email']}")
    if applicant['pan']:
        lines.append(f"PAN No: {applicant['pan']}")
    return '<br/>'.join(lines)


def _format_bo_from_block(bo):
    lines = ['<b>From:</b>']
    if bo.get('is_blank'):
        lines.append('______________________________ (Building Owner)')
        lines.append('W/o / S/o ____________________')
        lines.append('Address: ____________________')
    else:
        name_display = bo['name'].strip()
        lines.append(f"<b>{name_display}</b>")
        if bo['father']:
            lines.append(f"W/o / S/o {bo['father']},")
        addr = bo['address']
        if addr:
            chunks = [c.strip() for c in addr.split(',') if c.strip()]
            for chunk in chunks:
                lines.append(chunk)
        if bo['mobile']:
            lines.append(f"Mobile. No: {bo['mobile']}")
    return '<br/>'.join(lines)


def _format_to_block(district='Kadapa', state='Andhra Pradesh'):
    dist = district or 'Kadapa'
    st = state or 'Andhra Pradesh'
    return (
        '<b>To,</b><br/>'
        'The Assistant Director,<br/>'
        'District Sales Licensing and<br/>'
        'Enforcement Authority,<br/>'
        'Drugs & Control Administration,<br/>'
        f'{dist} District,<br/>'
        f'{st}.'
    )


# ─── Page 1: Application Letter (Form 20/21) ────────────────────────────────

def _build_application_form(app, styles):
    applicant = _get_applicant_info(app)
    premises = _get_premises_info(app)
    pharma = _get_pharma_info(app)

    licence_type_label = (app.licence_type or 'retail').title()
    forms = app.licence_forms or ('Form 20 & 21' if app.licence_type == 'retail' else 'Form 20B & 21B')
    forms_clean = forms.replace(',', ' & ').replace('Form', 'Form ').strip()

    elements = []

    # 1. Subject Header (Centered, Bold, Underlined)
    subject_text = (
        f'<u><b>Application of M/s {applicant["firm_name"]}, {premises["full_address"]} '
        f'for Grant of New Drug licenses in {forms_clean}.</b></u>'
    )
    elements.append(Paragraph(subject_text, styles['DraftSubject']))
    elements.append(Spacer(1, 10))

    # 2. Two-Column From & To Table
    from_html = _format_from_block(applicant)
    to_html = _format_to_block(premises['district'], premises['state'])

    from_to_table = Table(
        [[Paragraph(from_html, styles['DraftFromTo']), Paragraph(to_html, styles['DraftFromTo'])]],
        colWidths=[9.2 * cm, 8.8 * cm],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]
    )
    elements.append(from_to_table)
    elements.append(Spacer(1, 12))

    # 3. Salutation
    elements.append(Paragraph('<b>Sir,</b>', styles['DraftSalutation']))

    # Paragraph 1
    father_str = f" C/o {applicant['father']}," if applicant['father'] else ""
    addr_str = f" {applicant['address']}." if applicant['address'] else "."
    app_name = applicant['name'] or '____________________'
    p1 = (
        f'I, {app_name}{father_str}{addr_str} '
        f'I want to establish a new medical {licence_type_label} Store under style '
        f'<u><b>M/s {applicant["firm_name"]}, {premises["full_address"]}</b></u>. '
        f'In this connection I have acquired sales premises with necessary net carpet area and proper storage facility. '
        f'I am herewith submitting all necessary documents for consideration of my/our request.'
    )
    elements.append(Paragraph(p1, styles['DraftBodyIndent']))

    # Paragraph 2
    ph_name = pharma['name'] or '____________________'
    reg_no_str = f" with Regd. No.: {pharma['reg_no']}" if pharma['reg_no'] else ""
    is_proprietor_pharma = bool(pharma['name'] and applicant['name'] and (
        pharma['name'].lower() in applicant['name'].lower() or applicant['name'].lower() in pharma['name'].lower()
    ))
    if is_proprietor_pharma:
        p2 = (
            f'It is further submitted that, I, {ph_name}, '
            f'Registered Pharmacist{reg_no_str} and I shall supervise all {licence_type_label.lower()} '
            f'transactions of drugs in my shop.'
        )
    else:
        p2 = (
            f'It is further submitted that, I have appointed {ph_name}, '
            f'Registered Pharmacist{reg_no_str} and supervises all {licence_type_label.lower()} '
            f'transactions of drugs in my shop.'
        )
    elements.append(Paragraph(p2, styles['DraftBodyIndent']))

    # Paragraph 3
    p3 = (
        'Proper storage conditions maintained for preservation of properties of the drugs and '
        'proper purchase and sales records and other related requirements shall be maintained in '
        'compliance of statutory requirements.'
    )
    elements.append(Paragraph(p3, styles['DraftBodyIndent']))

    # Paragraph 4
    p4 = (
        'It is ensured that all relevant Rules and Regulations of Drugs and Cosmetics '
        'Act,1940 and other allied Acts, shall be duly complied.'
    )
    elements.append(Paragraph(p4, styles['DraftBodyIndent']))

    # Paragraph 5
    if premises['area_sqm']:
        area_str = f"{premises['area_sqm']} Sq. mts ({premises['area_sqft']} Sq. ft.)"
    else:
        area_str = "______ Sq. mts"
    p5 = f'Proper net carpet area of {area_str} provided as per plan submitted herewith.'
    elements.append(Paragraph(p5, styles['DraftBodyIndent']))

    # Paragraph 6 (Challan)
    curr_month = date.today().strftime('%m')
    curr_year = date.today().strftime('%Y')
    challan_no = '______'
    challan_date_str = f'/{curr_month}/{curr_year}'
    if app.payments and len(app.payments) > 0 and app.payments[0].challan_number:
        challan_no = app.payments[0].challan_number
        if app.payments[0].challan_date:
            challan_date_str = _d(app.payments[0].challan_date)

    p6 = (
        f'An amount of Rs. 3,000/- was remitted to the Govt. Account vide Challan No. {challan_no}, '
        f'dated: {challan_date_str}. Hence it is requested that drugs licenses in {forms_clean}, may be issued.'
    )
    elements.append(Paragraph(p6, styles['DraftBodyIndent']))
    elements.append(Spacer(1, 24))

    # 4. Signoff
    elements.append(Paragraph('Yours faithfully', styles['DraftSignoff']))

    return elements


# ─── Page 2: Declaration of Building Owner ──────────────────────────────────

def _build_building_owner_declaration(app, styles):
    applicant = _get_applicant_info(app)
    premises = _get_premises_info(app)
    bo = _get_bo_info(app)

    elements = []

    # 1. Centered Title
    elements.append(Paragraph('<u><b>Declaration of Building Owner</b></u>', styles['DraftDocTitle']))
    elements.append(Spacer(1, 8))

    # 2. From & To Table
    from_html = _format_bo_from_block(bo)
    to_html = _format_to_block(premises['district'], premises['state'])

    from_to_table = Table(
        [[Paragraph(from_html, styles['DraftFromTo']), Paragraph(to_html, styles['DraftFromTo'])]],
        colWidths=[9.2 * cm, 8.8 * cm],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]
    )
    elements.append(from_to_table)
    elements.append(Spacer(1, 14))

    # 3. Body Paragraphs
    if premises['area_sqm']:
        area_str = f"{premises['area_sqm']} Sq. mts ({premises['area_sqft']} Sq. ft.)"
    else:
        area_str = "______ Sq. mts"

    father_str = f" W/o / S/o {bo['father']}," if bo['father'] else ""
    addr_str = f" {bo['address']}." if bo['address'] else "."
    bo_name = bo['name'] or '______________________________'
    app_name = applicant['name'] or '____________________'

    p1 = (
        f'I, {bo_name}{father_str}{addr_str} '
        f'I am owner of the building at <u><b>{premises["full_address"]}</b></u>.'
    )
    elements.append(Paragraph(p1, styles['DraftBodyIndent']))

    p2 = (
        f'I have given a portion of my Building to run medical business in the name and '
        f'style of <u><b>M/s {applicant["firm_name"]}</b></u> to <u><b>{app_name}</b></u>.'
    )
    elements.append(Paragraph(p2, styles['DraftBodyIndent']))

    p3 = (
        f'The portion has been allotted at <u><b>{premises["full_address"]}</b></u> '
        f'and the portion which was let out measures {area_str}.'
    )
    elements.append(Paragraph(p3, styles['DraftBodyIndent']))

    p4 = (
        f'I am herewith submitting attested copy of {bo["ownership_doc"]} as a proof of '
        f'ownership of the premises and also the plan of the premises of the said building let out to '
        f'the said firm duly attested by me.'
    )
    elements.append(Paragraph(p4, styles['DraftBodyIndent']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph('Thanking You', styles['DraftBodyIndent']))
    elements.append(Spacer(1, 20))

    # 4. Attestation Photo Box & Signature
    photo_box = Table(
        [[Paragraph('BUILDING<br/>OWNER<br/>PASSPORT SIZE<br/>PHOTO<br/>ATTESTED BY<br/>GAZETTED<br/>OFFICER', styles['PhotoBoxLabel'])]],
        colWidths=[3.4 * cm],
        rowHeights=[4.2 * cm],
        style=[
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
    )

    sig_markup = (
        '<b>SIGNATURE OF THE BUILDING OWNER</b><br/>'
        '(Signature also to be Attested by Gazetted Officer)'
    )

    attest_table = Table(
        [[photo_box, Paragraph(sig_markup, styles['DraftSignoffCenter'])]],
        colWidths=[5.0 * cm, 13.0 * cm],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]
    )
    elements.append(attest_table)

    return elements


# ─── Page 3: Declaration of Proprietor / Pharmacist ─────────────────────────

def _build_pharmacist_declaration(app, styles):
    applicant = _get_applicant_info(app)
    premises = _get_premises_info(app)
    pharma = _get_pharma_info(app)
    decls = _get_declaration_dict(app)

    elements = []

    # 1. Header with Photo Box (Unified Header Table)
    photo_box_cell = Table(
        [[Paragraph('RECENT PASS<br/>PORT SIZE<br/>PHOTO<br/>ATTESTED BY<br/>GAZETTED<br/>OFFICER', styles['PhotoBoxLabel'])]],
        colWidths=[3.2 * cm],
        rowHeights=[3.4 * cm],
        style=[
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]
    )

    header_cell = Paragraph(
        '<b>DECLARATION OF THE PROPRIETOR CUM REGISTERED PHARAMCIST</b>',
        styles['TableHeaderTitle']
    )

    header_table = Table(
        [[header_cell, photo_box_cell]],
        colWidths=[14.8 * cm, 3.2 * cm],
        style=[
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 6),
            ('RIGHTPADDING', (0, 0), (0, 0), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]
    )
    elements.append(header_table)

    # 2. 15-Row Numbered Legal Grid Table matching statutory draft exactly
    proposed_shop_text = f'<u><b>M/s {applicant["firm_name"]}, {premises["full_address"]}</b></u>'

    mob = pharma["mobile"] or applicant["mobile"] or ''
    em = applicant["email"] or pharma["email"] or ''
    contact_parts = []
    if mob: contact_parts.append(f"Mobile. No: {mob}")
    if em: contact_parts.append(f"Mail Id : {em}")
    email_mobile_text = '<br/>'.join(contact_parts) if contact_parts else 'Mobile. No: ______'

    effective_name = pharma["name"] or applicant["name"] or '____________________'
    full_name_text = f'<b>{effective_name.upper()}</b>'

    father_prof_text = pharma['father'] or applicant['father'] or '____________________'

    # Age calculation from DOB
    age_text = '______'
    bd = app.business_details
    dob = getattr(bd, 'proprietor_dob', None)
    if dob:
        today = date.today()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        age_text = f"{years} Years."
    else:
        age_text = 'As per SSC'

    perm_addr_text = pharma['address'] or applicant['address'] or 'As per ID Proof'
    present_addr_text = pharma['address'] or applicant['address'] or 'As per ID Proof'

    reg_val_str = f", valid upto:<br/>{pharma['validity']}" if pharma['validity'] else ""
    reg_num_str = f", Regd No. {pharma['reg_no']}" if pharma['reg_no'] else ""
    edu_qual_text = f'{pharma["qualification"]}{reg_num_str}{reg_val_str}'

    rows = [
        ('1. Name & address of the proposed shop:', proposed_shop_text, 'normal'),
        ('2. Email ID<br/>&nbsp;&nbsp;&nbsp;&nbsp;Mobile No’s:', email_mobile_text, 'normal'),
        ('3. Full Name (Block Letters', full_name_text, 'normal'),
        ('4. Father’s/Husband’s Name<br/>&nbsp;&nbsp;&nbsp;&nbsp;and his profession', father_prof_text, 'normal'),
        ('5. Age', age_text, 'normal'),
        ('6. Permanent Address<br/>&nbsp;&nbsp;&nbsp;&nbsp;(Proof to be attached)', perm_addr_text, 'normal'),
        ('7. Present Residential Address', present_addr_text, 'normal'),
        ('8. Educational Qualification<br/>&nbsp;&nbsp;&nbsp;&nbsp;(all certificate copies to be attached)', edu_qual_text, 'normal'),
        ('9. Details of Earlier Occupation<br/>&nbsp;&nbsp;&nbsp;&nbsp;For last five years<br/>&nbsp;&nbsp;&nbsp;&nbsp;(Please specify details clearly)', decls.get('prev_occupation', 'Nil'), 'center'),
        ('10. Whether You / Your Spouse are in<br/>possession of any Licenses under Drugs<br/>and Cosmetics Rules Earlier or Present?<br/>If yes, Details', decls.get('prev_drug_licence', 'No'), 'center'),
        ('11. Whether at any time You / Your<br/>Spouses Drug Licenses Cancelled?<br/>&nbsp;&nbsp;&nbsp;&nbsp;If yes, Details', decls.get('licence_cancelled', 'No'), 'center'),
        ('12. Whether You / Your Spouse at<br/>&nbsp;&nbsp;&nbsp;&nbsp;any time convicted under any<br/>&nbsp;&nbsp;&nbsp;&nbsp;Criminal law ? if yes, Details', decls.get('criminal_conviction', 'No'), 'center'),
        ('13. Either alone or with anybody, You /<br/>Your spouse involved in any Drug<br/>Cases ? If yes, Details', decls.get('drug_case', 'No'), 'center'),
        ('14. Are You /Your spouse convicted /<br/>Acquitted in any Cases Under Drugs<br/>and Cosmetic Act, 1940? If Yes, Details', decls.get('drug_case', 'No'), 'center'),
        ('15. Have you studied the Rules and<br/>Regulations of Drugs and Cosmetics<br/>Act, 1940 and Rules 1945 and under–Stand<br/>Responsibilities of a Licensed Dealer?', decls.get('rules_understood', 'Yes'), 'center'),
    ]

    table_data = []
    for q, a, align_mode in rows:
        q_p = Paragraph(q, styles['GridQuestion'])
        a_p = Paragraph(a, styles['GridAnswer'] if align_mode == 'center' else styles['GridAnswerNormal'])
        table_data.append([q_p, a_p])

    grid_table = Table(
        table_data,
        colWidths=[8.8 * cm, 9.2 * cm],
        style=[
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.8, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]
    )
    elements.append(grid_table)

    # 3. Certification Text
    cert_text = (
        f'Certified that the above information furnished by me is true and correct and in case if any '
        f'above stated information is found to be false, I am liable for any action to be taken by the officers '
        f'of the Drugs Control Administration, {premises["state"]}.'
    )
    elements.append(Paragraph(cert_text, styles['DraftCertify']))

    # 4. Footer Place / Date & Signature
    place_text = premises['mandal'] or premises['district'] or '______'
    footer_left = f'Place : {place_text}<br/>Date :'
    footer_right = 'SIGNATURE'

    footer_table = Table(
        [[Paragraph(footer_left, styles['DraftFromTo']), Paragraph(footer_right, styles['DraftSignoff'])]],
        colWidths=[9.0 * cm, 9.0 * cm],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]
    )
    elements.append(footer_table)

    return elements


# ─── Page 4: Appointment / Acceptance Letter ────────────────────────────────

def _build_appointment_letter(app, styles):
    applicant = _get_applicant_info(app)
    premises = _get_premises_info(app)
    pharma = _get_pharma_info(app)

    licence_type = (app.licence_type or 'Retail').title()

    elements = []

    # 1. Centered Title
    elements.append(Paragraph('<u><b>Appointment /Acceptance Letter</b></u>', styles['DraftDocTitle']))
    elements.append(Spacer(1, 24))

    # 2. Appointment Declaration Body
    is_proprietor_pharma = bool(pharma['name'] and applicant['name'] and (
        pharma['name'].lower() in applicant['name'].lower() or applicant['name'].lower() in pharma['name'].lower()
    ))
    father_str = f" C/o {applicant['father']}," if applicant['father'] else ""
    addr_str = f" {applicant['address']}." if applicant['address'] else "."
    app_name = applicant['name'] or '____________________'
    ph_name = pharma['name'] or '____________________'

    if is_proprietor_pharma:
        letter_text = (
            f'I, {app_name}{father_str}{addr_str} '
            f'I am Proprietor cum Registered Pharmacist in new medical {licence_type} Store under style '
            f'<u><b>M/s {applicant["firm_name"]}, {premises["full_address"]}</b></u>.'
        )
    else:
        letter_text = (
            f'I, {app_name}{father_str}{addr_str} '
            f'I have appointed {ph_name} as Registered Pharmacist in new medical {licence_type} Store under style '
            f'<u><b>M/s {applicant["firm_name"]}, {premises["full_address"]}</b></u>. '
            f'And I, {ph_name}, accept the appointment as Registered Pharmacist in the said firm.'
        )
    elements.append(Paragraph(letter_text, styles['DraftBody']))
    elements.append(Spacer(1, 54))

    # 3. Center-Aligned Signature
    if is_proprietor_pharma:
        elements.append(Paragraph('<u><b>Signature of Proprietor cum Registered Pharmacist</b></u>', styles['DraftSignoffCenter']))
    else:
        sig_table = Table(
            [[
                Paragraph('<u><b>Signature of Applicant / Firm</b></u>', styles['DraftSignoffCenter']),
                Paragraph('<u><b>Signature of Registered Pharmacist</b></u>', styles['DraftSignoffCenter'])
            ]],
            colWidths=[9.0 * cm, 9.0 * cm],
            style=[
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]
        )
        elements.append(sig_table)

    return elements


# ─── Combined 4-Page Dossier (Draft.pdf) ────────────────────────────────────

def _build_complete_dossier(app, styles):
    elements = []

    # Page 1
    elements.extend(_build_application_form(app, styles))
    elements.append(PageBreak())

    # Page 2
    elements.extend(_build_building_owner_declaration(app, styles))
    elements.append(PageBreak())

    # Page 3
    elements.extend(_build_pharmacist_declaration(app, styles))
    elements.append(PageBreak())

    # Page 4
    elements.extend(_build_appointment_letter(app, styles))

    return elements


# ─── Document Builders Registry ─────────────────────────────────────────────

DOCUMENT_BUILDERS = {
    'complete_dossier': _build_complete_dossier,
    'application_form': _build_application_form,
    'building_owner_declaration': _build_building_owner_declaration,
    'pharmacist_declaration': _build_pharmacist_declaration,
    'appointment_letter': _build_appointment_letter,
}


def _generate_one(app, doc_type: str, output_dir: str) -> str:
    styles = _get_styles()
    builder = DOCUMENT_BUILDERS.get(doc_type)
    if not builder:
        raise ValueError(f'Unknown document type: {doc_type}')

    safe_num = (app.app_number or str(app.id)).replace('/', '-')
    if doc_type == 'complete_dossier':
        filename = f'{safe_num}_Draft.pdf'
    else:
        filename = f'{safe_num}_{doc_type}.pdf'
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )

    elements = builder(app, styles)
    doc.build(elements)
    return filename


def generate_all_documents(app, user_id: int) -> list:
    from flask import current_app
    output_dir = current_app.config['GENERATED_FOLDER']
    app_dir = os.path.join(output_dir, str(app.id))
    os.makedirs(app_dir, exist_ok=True)

    # Mark existing docs outdated
    for doc in app.generated_documents:
        if doc.status == 'current':
            doc.status = 'outdated'
    db.session.flush()

    # The user requires only the unified 4-page statutory Draft.pdf exactly replicating the uploaded statutory document.
    doc_types = [
        'complete_dossier',
    ]

    generated = []
    for doc_type in doc_types:
        try:
            filename = _generate_one(app, doc_type, app_dir)
            rel_filename = os.path.join(str(app.id), filename)
            gd = GeneratedDocument(
                application_id=app.id,
                document_type=doc_type,
                filename=rel_filename,
                status='current',
                created_by=user_id,
            )
            db.session.add(gd)
            generated.append(gd)
        except Exception as e:
            current_app.logger.exception(f'Error generating {doc_type}')
            gd = GeneratedDocument(
                application_id=app.id,
                document_type=doc_type,
                filename='',
                status='error',
                generation_notes=str(e),
                created_by=user_id,
            )
            db.session.add(gd)

    if any(g.status == 'current' for g in generated):
        app.status = 'documents_generated'

    db.session.commit()
    return generated
