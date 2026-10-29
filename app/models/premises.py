from app_extensions import db


class Premises(db.Model):
    __tablename__ = 'premises'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'),
                               nullable=False, unique=True)

    ownership_type = db.Column(db.String(20))   # owned | rented | other
    shop_name = db.Column(db.String(200))

    # Shop address
    assessment_number = db.Column(db.String(50))
    door_number = db.Column(db.String(50))
    floor = db.Column(db.String(30))
    street = db.Column(db.String(200))
    village = db.Column(db.String(100))
    gram_panchayat = db.Column(db.String(100))
    mandal = db.Column(db.String(100))
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    full_address = db.Column(db.Text)

    area_sqm = db.Column(db.Float)
    storage_facilities = db.Column(db.Text)

    # Ownership / rent
    ownership_doc_details = db.Column(db.String(300))
    rent_agreement_details = db.Column(db.String(300))

    application = db.relationship('Application', back_populates='premises')

    def __repr__(self):
        return f'<Premises {self.application_id}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
