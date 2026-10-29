from app_extensions import db


class BuildingOwner(db.Model):
    __tablename__ = 'building_owners'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    full_name = db.Column(db.String(200))
    father_husband_name = db.Column(db.String(200))
    residential_address = db.Column(db.Text)
    mobile = db.Column(db.String(15))
    ownership_doc_details = db.Column(db.String(300))

    application = db.relationship('Application', back_populates='building_owners')

    def __repr__(self):
        return f'<BuildingOwner {self.application_id} {self.full_name}>'

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
