from app_extensions import db


class Declaration(db.Model):
    __tablename__ = 'declarations'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    question_key = db.Column(db.String(100), nullable=False)   # machine-readable key
    question_text = db.Column(db.Text)                         # full question wording
    answer = db.Column(db.String(10))                          # yes | no
    details = db.Column(db.Text)                               # conditional detail text

    application = db.relationship('Application', back_populates='declarations')

    def __repr__(self):
        return f'<Declaration {self.application_id} {self.question_key}={self.answer}>'

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'question_key': self.question_key,
            'question_text': self.question_text,
            'answer': self.answer,
            'details': self.details,
        }
