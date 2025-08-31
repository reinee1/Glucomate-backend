from app.extensions import db
from sqlalchemy.sql import func

class Monitoring(db.Model):
    __tablename__ = "monitoring"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    glucose_frequency = db.Column(db.String(30), nullable=True)   # e.g., 4/day
    latest_hba1c_percent = db.Column(db.Numeric(4,2), nullable=True)
    uses_cgm = db.Column(db.Boolean, nullable=True)
    frequent_hypoglycemia = db.Column(db.Boolean, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = db.relationship("User", backref=db.backref("monitoring", uselist=False, cascade="all,delete"))
