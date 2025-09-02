# app/routes/auth_routes.py
from flask import Blueprint, request
from flask_cors import cross_origin
from app.controllers import auth_controller

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

auth_bp.route("/register", methods=["POST"])(auth_controller.register)
auth_bp.route("/verify", methods=["GET"])(auth_controller.verify_email)
auth_bp.route("/login", methods=["POST"])(auth_controller.login)
auth_bp.route("/forgot-password", methods=["POST"])(auth_controller.forgot_password)
auth_bp.route("/reset-password", methods=["POST"])(auth_controller.reset_password)


@cross_origin(
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True,
)
def signup_alias():
    if request.method == "OPTIONS":
        return ("", 204)
    return auth_controller.register()
