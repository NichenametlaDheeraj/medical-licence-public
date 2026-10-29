from app_extensions import db


class Pharmacist(db.Model):
    __tablename__ = 'pharmacists'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    full_name = db.Column(db.String(200))
    father_husband_name = db.Column(db.String(200))
    qualification = db.Column(db.String(100))
    registration_number = db.Column(db.String(100))
    registration_authority = db.Column(db.String(200))
    registration_validity = db.Column(db.Date, nullable=True)
    residential_address = db.Column(db.Text)
    mobile = db.Column(db.String(15))
    email = db.Column(db.String(120))
    appointment_date = db.Column(db.Date, nullable=True)
    employment_status = db.Column(db.String(50))  # employed | part_time | consultant

    application = db.relationship('Application', back_populates='pharmacists')

    def __repr__(self):
        return f'<Pharmacist {self.application_id} {self.full_name}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
