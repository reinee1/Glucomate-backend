from app.extensions import db
from sqlalchemy.sql import func

class Notification(db.Model):
    __tablename__ = "notification"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(40), nullable=True)  # e.g., "reminder", "alert"
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref=db.backref("notifications", cascade="all,delete-orphan"))
