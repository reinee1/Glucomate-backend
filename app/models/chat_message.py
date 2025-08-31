from app.extensions import db
from sqlalchemy.sql import func

class ChatMessage(db.Model):
    __tablename__ = "chat_message"
    id = db.Column(db.Integer, primary_key=True)
    chat_session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=False, index=True)

    sender = db.Column(db.String(20), nullable=False)  # "user" | "bot"
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = db.relationship("ChatSession", backref=db.backref("messages", order_by="ChatMessage.timestamp", cascade="all,delete-orphan"))
