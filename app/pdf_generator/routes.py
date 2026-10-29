"""
pdf_generator/routes.py
Routes for generating and downloading PDF documents.
"""
import os
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   send_file, abort, current_app)
from flask_login import login_required, current_user
from app.auth.decorators import admin_required
from app_extensions import db
from app.models.application import Application
from app.models.generated_document import GeneratedDocument
from app.services.pdf_service import generate_all_documents

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/generate/<int:app_id>', methods=['POST'])
@login_required
def generate(app_id):
    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        abort(404)
    if current_user.role != 'admin' and app_obj.created_by != current_user.id:
        flash('Access denied: Administrator privileges required to generate documents for other users.', 'danger')
        return redirect(url_for('dashboard.index'))
    try:
        docs = generate_all_documents(app_obj, current_user.id)
        flash('Official statutory Draft.pdf (4 pages) generated successfully.', 'success')
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
    path = os.path.join(folder, doc.filename)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(doc.filename))


@pdf_bp.route('/view/<int:doc_id>')
@login_required
def view_pdf(doc_id):
    doc = db.session.get(GeneratedDocument, doc_id)
    if not doc:
        abort(404)
    if current_user.role != 'admin' and doc.application and doc.application.created_by != current_user.id:
        abort(403)
    folder = current_app.config['GENERATED_FOLDER']
    path = os.path.join(folder, doc.filename)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=False, mimetype='application/pdf')


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
