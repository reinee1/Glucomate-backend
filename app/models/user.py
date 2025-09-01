from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name  = db.Column(db.String(80), nullable=False)
    email      = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    is_verified   = db.Column(db.Boolean, default=False)
    verified_at   = db.Column(db.DateTime, nullable=True)

    verification_token = db.Column(db.String(255), nullable=True, unique=True)
    verification_token_expires_at = db.Column(db.DateTime, nullable=True)

    # NEW: password reset
    password_reset_token = db.Column(db.String(255), nullable=True, unique=True)
    password_reset_expires_at = db.Column(db.DateTime, nullable=True)
    last_password_reset_sent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def set_verification_token(self, ttl_minutes=1440):
        import secrets
        self.verification_token = secrets.token_urlsafe(48)
        self.verification_token_expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

    # NEW: password reset token helper
    def set_password_reset_token(self, ttl_minutes=30):
        import secrets
        self.password_reset_token = secrets.token_urlsafe(48)
        self.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        self.last_password_reset_sent_at = datetime.utcnow()

    # NEW: invalidate reset token after use
    def clear_password_reset_token(self):
        self.password_reset_token = None
        self.password_reset_expires_at = None

    weekly_assessments = db.relationship("WeeklyAssessment", back_populates="user", cascade="all,delete-orphan")
