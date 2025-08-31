from app.extensions import db
from sqlalchemy.sql import func

class MedicalProfile(db.Model):
    __tablename__ = "medical_profile"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)         # consider Enum later
    weight = db.Column(db.Float, nullable=True)               # kg
    height = db.Column(db.Float, nullable=True)               # cm
    diabetes_type = db.Column(db.String(30), nullable=True)   # e.g. T1D, T2D
    diagnosis_year = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = db.relationship("User", backref=db.backref("medical_profile", uselist=False, cascade="all,delete"))
