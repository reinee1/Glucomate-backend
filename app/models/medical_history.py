from app.extensions import db

class MedicalHistory(db.Model):
    __tablename__ = "medical_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    family_history_heart_disease = db.Column(db.Boolean, nullable=True)
    currently_on_insulin = db.Column(db.Boolean, nullable=True)

    user = db.relationship("User", backref=db.backref("medical_history", uselist=False, cascade="all,delete"))
