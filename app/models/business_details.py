from app_extensions import db


class BusinessDetails(db.Model):
    __tablename__ = 'business_details'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'),
                               nullable=False, unique=True)

    # Firm info
    firm_name = db.Column(db.String(200))
    trading_name = db.Column(db.String(200))
    firm_reg_number = db.Column(db.String(100))
    pan = db.Column(db.String(20))
    email = db.Column(db.String(120))
    mobile = db.Column(db.String(15))
    alt_contact = db.Column(db.String(15))
    commencement_date = db.Column(db.Date, nullable=True)

    # Business address
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

    # Proprietor info (used when constitution == proprietorship)
    proprietor_name = db.Column(db.String(200))
    proprietor_father_husband = db.Column(db.String(200))
    proprietor_dob = db.Column(db.Date, nullable=True)
    proprietor_residential_address = db.Column(db.Text)
    proprietor_mobile = db.Column(db.String(15))
    proprietor_email = db.Column(db.String(120))
    proprietor_pan = db.Column(db.String(20))
    proprietor_id_doc_details = db.Column(db.String(200))

    # LLP fields
    llp_name = db.Column(db.String(200))
    llpin = db.Column(db.String(50))
    llp_registration_date = db.Column(db.Date, nullable=True)
    llp_registered_office = db.Column(db.Text)
    llp_authorized_signatory = db.Column(db.String(200))

    # Company fields
    company_name = db.Column(db.String(200))
    cin = db.Column(db.String(50))
    incorporation_date = db.Column(db.Date, nullable=True)
    company_registered_office = db.Column(db.Text)
    company_authorized_signatory = db.Column(db.String(200))

    # Partnership deed
    deed_date = db.Column(db.Date, nullable=True)
    deed_registration_details = db.Column(db.String(200))
    deed_registered_office = db.Column(db.Text)

    # Other constitution
    other_constitution_desc = db.Column(db.String(200))

    application = db.relationship('Application', back_populates='business_details')

    def __repr__(self):
        return f'<BusinessDetails {self.application_id}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
