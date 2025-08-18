from app.extensions import db
from sqlalchemy.sql import func

class ChatSession(db.Model):
    __tablename__ = "chat_session"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    started_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref=db.backref("chat_sessions", cascade="all,delete-orphan"))
