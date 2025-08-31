import uuid
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"
    # app/models/user.py
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name  = db.Column(db.String(80), nullable=False)
    email      = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    is_verified   = db.Column(db.Boolean, default=False)
    verified_at   = db.Column(db.DateTime, nullable=True)

    verification_token       = db.Column(db.String(255), nullable=True, unique=True)
    verification_token_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def set_verification_token(self, ttl_minutes=1440):  # default 24h
        import secrets
        self.verification_token = secrets.token_urlsafe(48)
        self.verification_token_expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
