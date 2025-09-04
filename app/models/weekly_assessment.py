# app/models/weekly_assessment.py
from app.extensions import db

class WeeklyAssessment(db.Model):
    __tablename__ = "weekly_assessments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_date = db.Column(db.Date, nullable=False)

    glucose_frequency = db.Column(db.Integer)
    range_compliance = db.Column(db.Float)
    energy_level = db.Column(db.Integer)
    sleep_quality = db.Column(db.Integer)

    # CHANGE THIS:
    # medication_adherence = db.Column(db.Boolean)
    medication_adherence = db.Column(db.Integer)   # store 0–100 adherence or a bucket code

    concerns = db.Column(db.Text)
    overall_feeling = db.Column(db.String(255))

    __table_args__ = (
        db.UniqueConstraint("user_id", "week_date", name="uq_weekly_assessments_user_week"),
    )

    user = db.relationship("User", back_populates="weekly_assessments")