from app_extensions import db


class Partner(db.Model):
    __tablename__ = 'partners'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    partner_number = db.Column(db.Integer, nullable=False)   # 1-based display index

    full_name = db.Column(db.String(200))
    father_husband_name = db.Column(db.String(200))
    residential_address = db.Column(db.Text)
    mobile = db.Column(db.String(15))
    email = db.Column(db.String(120))
    pan = db.Column(db.String(20))
    role = db.Column(db.String(100))
    is_designated_partner = db.Column(db.Boolean, default=False)
    is_authorized_signatory = db.Column(db.Boolean, default=False)
    id_doc_details = db.Column(db.String(200))

    application = db.relationship('Application', back_populates='partners')

    def __repr__(self):
        return f'<Partner {self.application_id} #{self.partner_number} {self.full_name}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
