# app/routes/chat_routes.py
from flask import Blueprint
from app.controllers import chat_controller

# Create chat blueprint
chat_bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")

# Register chat routes
chat_bp.route("/message", methods=["POST"])(chat_controller.send_message_to_glucomate)
chat_bp.route("/history", methods=["GET"])(chat_controller.get_chat_history)
chat_bp.route("/history/<int:session_id>", methods=["GET"])(chat_controller.get_chat_history)
chat_bp.route("/session/<int:session_id>/end", methods=["PUT"])(chat_controller.end_chat_session)
chat_bp.route("/status", methods=["GET"])(chat_controller.get_chat_status)
