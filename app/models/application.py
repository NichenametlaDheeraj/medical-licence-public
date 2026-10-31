from datetime import datetime, timezone, date
from app_extensions import db


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    app_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    app_date = db.Column(db.Date, default=date.today)
    licence_category = db.Column(db.String(30), default='new')  # new
    licence_type = db.Column(db.String(20), nullable=False)     # retail | wholesale | both
    licence_forms = db.Column(db.String(100))                   # e.g. Form 20,Form 21
    status = db.Column(db.String(20), default='draft')
    # draft | in_progress | ready | documents_generated | archived

    business_constitution = db.Column(db.String(30))
    # proprietorship | partnership | llp | private_limited | other

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    is_archived = db.Column(db.Boolean, default=False)

    # User who created the application
    creator = db.relationship('User', foreign_keys=[created_by])

    # Relationships
    business_details = db.relationship('BusinessDetails', back_populates='application',
                                       uselist=False, cascade='all, delete-orphan')
    partners = db.relationship('Partner', back_populates='application',
                               cascade='all, delete-orphan', order_by='Partner.partner_number')
    premises = db.relationship('Premises', back_populates='application',
                               uselist=False, cascade='all, delete-orphan')
    building_owners = db.relationship('BuildingOwner', back_populates='application',
                                      cascade='all, delete-orphan',
                                      order_by='BuildingOwner.id')
    pharmacists = db.relationship('Pharmacist', back_populates='application',
                                  cascade='all, delete-orphan',
                                  order_by='Pharmacist.id')
    declarations = db.relationship('Declaration', back_populates='application',
                                   cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='application',
                               cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', back_populates='application',
                                  cascade='all, delete-orphan')
    generated_documents = db.relationship('GeneratedDocument', back_populates='application',
                                          cascade='all, delete-orphan',
                                          order_by='GeneratedDocument.created_at.desc()')
    history = db.relationship('ApplicationHistory', back_populates='application',
                              cascade='all, delete-orphan',
                              order_by='ApplicationHistory.created_at.desc()')

    def __repr__(self):
        return f'<Application {self.app_number}>'

    def get_attachment(self, doc_type):
        """Return the most recent attachment for a given document_type."""
        if not self.attachments:
            return None
        for att in reversed(self.attachments):
            if att.document_type == doc_type:
                return att
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'app_number': self.app_number,
            'app_date': self.app_date.isoformat() if self.app_date else None,
            'licence_type': self.licence_type,
            'licence_forms': self.licence_forms,
            'status': self.status,
            'business_constitution': self.business_constitution,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ApplicationHistory(db.Model):
    __tablename__ = 'application_history'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    application = db.relationship('Application', back_populates='history')
    user = db.relationship('User', foreign_keys=[changed_by])

    def __repr__(self):
        return f'<History {self.application_id} {self.action}>'
