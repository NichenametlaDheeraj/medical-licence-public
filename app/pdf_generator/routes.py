"""
pdf_generator/routes.py
Routes for generating, previewing, and downloading PDF documents.
Supports on-demand in-memory streaming for stateless/serverless environments (Vercel).
"""
import io
import os
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   send_file, abort, current_app)
from flask_login import login_required, current_user
from app_extensions import db
from app.models.application import Application
from app.models.generated_document import GeneratedDocument
from app.services.pdf_service import generate_all_documents, build_pdf_bytes

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/generate/<int:app_id>', methods=['POST'])
@login_required
def generate(app_id):
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: You can only generate documents for your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    try:
        docs = generate_all_documents(app_obj, current_user.id)
        if any(d.status == 'current' for d in docs):
            flash('Official statutory Draft.pdf (4 pages) generated successfully.', 'success')
        else:
            notes = [d.generation_notes for d in docs if d.generation_notes]
            flash(f'PDF generation issue: {", ".join(notes) if notes else "Please check details"}', 'warning')
    except Exception as e:
        current_app.logger.exception('PDF generation failed')
        flash(f'PDF generation failed: {str(e)}', 'danger')
    return redirect(url_for('pdf.preview', app_id=app_id))


@pdf_bp.route('/download/<int:doc_id>')
@login_required
def download(doc_id):
    doc = db.session.get(GeneratedDocument, doc_id)
    if not doc:
        abort(404)
    if current_user.role != 'admin' and doc.application and doc.application.created_by != current_user.id:
        abort(403)
    folder = current_app.config['GENERATED_FOLDER']
    clean_name = (doc.filename or '').replace('\\', '/')
    path = os.path.join(folder, *clean_name.split('/')) if clean_name else ''
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    # On-demand in-memory generation fallback (stateless serverless compatible)
    if doc.application:
        try:
            pdf_bytes, filename = build_pdf_bytes(doc.application, doc.document_type or 'complete_dossier')
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        except Exception:
            current_app.logger.exception('On-demand PDF generation failed in download')
    abort(404)


@pdf_bp.route('/view/<int:doc_id>')
@login_required
def view_pdf(doc_id):
    doc = db.session.get(GeneratedDocument, doc_id)
    if not doc:
        abort(404)
    if current_user.role != 'admin' and doc.application and doc.application.created_by != current_user.id:
        abort(403)
    folder = current_app.config['GENERATED_FOLDER']
    clean_name = (doc.filename or '').replace('\\', '/')
    path = os.path.join(folder, *clean_name.split('/')) if clean_name else ''
    if path and os.path.exists(path):
        return send_file(path, as_attachment=False, mimetype='application/pdf')
    # On-demand in-memory generation fallback (stateless serverless compatible)
    if doc.application:
        try:
            pdf_bytes, filename = build_pdf_bytes(doc.application, doc.document_type or 'complete_dossier')
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=filename
            )
        except Exception:
            current_app.logger.exception('On-demand PDF generation failed in view_pdf')
    abort(404)


@pdf_bp.route('/app/<int:app_id>/download')
@login_required
def download_app_pdf(app_id):
    """Directly stream statutory Draft.pdf download by application ID."""
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        abort(403)
    try:
        pdf_bytes, filename = build_pdf_bytes(app_obj, 'complete_dossier')
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.exception('Failed streaming app PDF download')
        flash(f'Failed to generate PDF: {str(e)}', 'danger')
        return redirect(url_for('applications.view_application', app_id=app_id))


@pdf_bp.route('/app/<int:app_id>/view')
@login_required
def view_app_pdf(app_id):
    """Directly stream statutory Draft.pdf inline by application ID."""
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        abort(403)
    try:
        pdf_bytes, filename = build_pdf_bytes(app_obj, 'complete_dossier')
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.exception('Failed streaming app PDF view')
        abort(500)


@pdf_bp.route('/preview/<int:app_id>')
@login_required
def preview(app_id):
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: You can only preview documents of your own applications.', 'danger')
        return redirect(url_for('dashboard.index'))
    docs = GeneratedDocument.query.filter_by(
        application_id=app_id,
        document_type='complete_dossier'
    ).order_by(GeneratedDocument.created_at.desc()).all()
    current_docs = [d for d in docs if d.status == 'current']
    if not current_docs:
        try:
            docs = generate_all_documents(app_obj, current_user.id)
            current_docs = [d for d in docs if d.status == 'current']
        except Exception as e:
            current_app.logger.exception('Auto document generation failed')
    current_doc = current_docs[0] if current_docs else (docs[0] if docs else None)
    return render_template('pdf/preview.html', app=app_obj, docs=docs, current_doc=current_doc)
