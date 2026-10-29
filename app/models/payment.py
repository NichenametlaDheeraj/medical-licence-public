from app_extensions import db


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    challan_number = db.Column(db.String(100))
    challan_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(10, 2))
    payment_status = db.Column(db.String(20), default='pending')
    # pending | paid | verified | failed
    payment_reference = db.Column(db.String(200))
    receipt_filename = db.Column(db.String(300))

    application = db.relationship('Application', back_populates='payments')

    def __repr__(self):
        return f'<Payment {self.application_id} {self.challan_number}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
