from datetime import datetime
from flask import current_app, jsonify, request, url_for
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlencode
from app.extensions import db
from app.models.user import User
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token

# Import from your email utility
from app.utils.email_utils import send_verification_email, send_password_reset_email

# Throttle password reset re-sends (in seconds)
MIN_RESET_INTERVAL_SECONDS = 300  # 5 minutes


# ---------------------------
# URL builders
# ---------------------------
def _base_url() -> str:
    """Prefer PUBLIC_BASE_URL; fallback to request.url_root."""
    return (current_app.config.get('PUBLIC_BASE_URL') or request.url_root).rstrip('/')


def _build_verify_url(token: str) -> str:
    return f"{_base_url()}/api/v1/auth/verify?{urlencode({'token': token})}"


def _build_password_reset_url(token: str) -> str:
    # Mirror verify URL style, but target reset-password endpoint
    return f"{_base_url()}/api/v1/auth/reset-password?{urlencode({'token': token})}"


# ---------------------------
# Controllers
# ---------------------------
def register():
    data = request.get_json() or {}
    first_name = (data.get("first_name") or "").strip()
    last_name  = (data.get("last_name") or "").strip()
    email      = (data.get("email") or "").lower().strip()
    password   = data.get("password")

    if not all([first_name, last_name, email, password]):
        return jsonify({"success": False, "message": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password too short"}), 400

    user = User(first_name=first_name, last_name=last_name, email=email)
    user.is_verified = False
    user.set_password(password)
    user.set_verification_token()  # must set both token + expires_at in your model

    try:
        db.session.add(user)
        db.session.commit()

        # Build URL **after** commit, using the stored token
        verify_url = _build_verify_url(user.verification_token)
        send_verification_email(user.email, verify_url)
        return jsonify({"success": True, "message": "User registered. Check email to verify."}), 201

    except IntegrityError:
        db.session.rollback()

        # Find the existing user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and not existing_user.is_verified:
            # Refresh token for EXISTING user, commit, then build URL from that token
            existing_user.set_verification_token()
            db.session.commit()

            verify_url = _build_verify_url(existing_user.verification_token)
            try:
                send_verification_email(existing_user.email, verify_url)
            except Exception:
                current_app.logger.exception("Failed to resend verification email")

            return jsonify({
                "success": True,
                "message": "Verification email resent. Please check your inbox."
            }), 200

        return jsonify({"success": False, "message": "Email already exists"}), 409


def verify_email():
    token = request.args.get("token")
    if not token:
        return jsonify({"success": False, "message": "Missing token"}), 400

    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify({"success": False, "message": "Invalid token"}), 400

    if user.verification_token_expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "Token expired"}), 400

    user.is_verified = True
    user.verified_at = datetime.utcnow()
    user.verification_token = None
    user.verification_token_expires_at = None
    db.session.commit()

    return jsonify({"success": True, "message": "Email verified successfully"}), 200


def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required", "success": False}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Invalid credentials", "success": False}), 401

    if not user.is_verified:
        return jsonify({"message": "Please verify your email first", "success": False}), 403

    if not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid credentials", "success": False}), 401

    # Create JWT token (use string identity)
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        },
        "access_token": access_token
    }), 200


def forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()

    # Always return the same message to avoid user enumeration
    generic_msg = {"success": True, "message": "If that email exists, a reset link has been sent."}

    if not email:
        return jsonify(generic_msg), 200

    user = User.query.filter_by(email=email).first()
    if not user:
        current_app.logger.info(f"Password reset requested for non-existent email: {email}")
        return jsonify(generic_msg), 200

    # Optional: require verified email to reset
    if not user.is_verified:
        current_app.logger.info(f"Password reset requested for unverified email: {email}")
        return jsonify(generic_msg), 200

    # Throttle re-sends
    if user.last_password_reset_sent_at:
        delta = (datetime.utcnow() - user.last_password_reset_sent_at).total_seconds()
        if delta < MIN_RESET_INTERVAL_SECONDS:
            current_app.logger.info(f"Password reset throttled for email: {email} (recent request)")
            return jsonify({"success": True, "message": "Please check your email. A recent reset link was already sent."}), 200

    # Generate token and mark send time, then commit
    user.set_password_reset_token(ttl_minutes=30)  # 30 minutes validity
    user.last_password_reset_sent_at = datetime.utcnow()
    db.session.commit()

    reset_url = _build_password_reset_url(user.password_reset_token)
    
    try:
        current_app.logger.info(f"Attempting to send password reset email to: {email}")
        send_password_reset_email(user.email, reset_url)
        current_app.logger.info(f"Password reset email sent successfully to: {email}")
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {email}: {str(e)}")

    return jsonify(generic_msg), 200

def reset_password():
    """
    Accepts token in JSON or query string.
    Body: { "token": "...", "new_password": "..." }
    """
    token = request.args.get("token") or (request.get_json() or {}).get("token")
    data = request.get_json() or {}
    new_password = (data.get("new_password") or "").strip()

    if not token or not new_password:
        return jsonify({"success": False, "message": "Token and new_password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password too short"}), 400

    user = User.query.filter_by(password_reset_token=token).first()
    if not user:
        return jsonify({"success": False, "message": "Invalid or already used token"}), 400

    if not user.password_reset_expires_at or user.password_reset_expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "Token expired"}), 400

    # Update password and invalidate token
    user.set_password(new_password)
    user.clear_password_reset_token()
    db.session.commit()

    return jsonify({"success": True, "message": "Password updated successfully"}), 200