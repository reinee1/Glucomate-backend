from app.extensions import db

class MedicalReminder(db.Model):
    __tablename__ = "medical_reminder"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    medication_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(60), nullable=True)
    frequency = db.Column(db.String(60), nullable=True)
    time_of_day = db.Column(db.Time(timezone=False), nullable=True)

    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, nullable=False, server_default="true")
    notes = db.Column(db.Text, nullable=True)

    user = db.relationship("User", backref=db.backref("medical_reminders", cascade="all,delete-orphan"))
