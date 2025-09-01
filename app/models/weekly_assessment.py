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
    medication_adherence = db.Column(db.Boolean)

    concerns = db.Column(db.Text)
    overall_feeling = db.Column(db.String(255))

    # ensure a user can have only one record per week
    __table_args__ = (
        db.UniqueConstraint("user_id", "week_date", name="uq_weekly_assessments_user_week"),
    )

    user = db.relationship("User", back_populates="weekly_assessments")

    def __repr__(self):
        return f"<WeeklyAssessment user_id={self.user_id} week_date={self.week_date}>"
