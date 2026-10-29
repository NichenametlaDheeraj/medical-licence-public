from datetime import datetime, timezone
from app_extensions import db


class GeneratedDocument(db.Model):
    __tablename__ = 'generated_documents'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    document_type = db.Column(db.String(100))
    # application_form | building_owner_declaration |
    # pharmacist_declaration | appointment_letter
    filename = db.Column(db.String(300))
    status = db.Column(db.String(20), default='current')  # current | outdated | error
    generation_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    application = db.relationship('Application', back_populates='generated_documents')

    def __repr__(self):
        return f'<GeneratedDocument {self.application_id} {self.document_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'document_type': self.document_type,
            'filename': self.filename,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
