from app.extensions import db
from sqlalchemy.sql import func

class Lifestyle(db.Model):
    __tablename__ = "lifestyle"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    smoking_status = db.Column(db.String(30), nullable=True)      # e.g., never/current/former
    alcohol_consumption = db.Column(db.String(30), nullable=True) # none/light/moderate/heavy
    exercise_frequency = db.Column(db.String(30), nullable=True)  # e.g., daily/weekly/rarely
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = db.relationship("User", backref=db.backref("lifestyle", uselist=False, cascade="all,delete"))
