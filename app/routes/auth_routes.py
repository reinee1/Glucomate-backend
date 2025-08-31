from flask import Blueprint
from app.controllers import auth_controller

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

auth_bp.route("/register", methods=["POST"])(auth_controller.register)
auth_bp.route("/verify", methods=["GET"])(auth_controller.verify_email)
auth_bp.route("/login", methods=["POST"])(auth_controller.login)
