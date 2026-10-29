from datetime import datetime, timezone
from app_extensions import db


class Attachment(db.Model):
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    document_type = db.Column(db.String(100))   # id_proof | pan | pharmacist_cert | etc.
    original_filename = db.Column(db.String(300))
    stored_filename = db.Column(db.String(300))
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    application = db.relationship('Application', back_populates='attachments')

    def __repr__(self):
        return f'<Attachment {self.application_id} {self.document_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'document_type': self.document_type,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
