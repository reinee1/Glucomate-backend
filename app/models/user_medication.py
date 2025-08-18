from app.extensions import db

class UserMedication(db.Model):
    __tablename__ = "user_medication"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    medication_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(60), nullable=True)      # e.g., "10 mg"
    frequency = db.Column(db.String(60), nullable=True)   # e.g., "BID"

    user = db.relationship("User", backref=db.backref("medications", cascade="all,delete-orphan"))

    __table_args__ = (db.Index("ix_user_med_medication", "user_id", "medication_name"),)
