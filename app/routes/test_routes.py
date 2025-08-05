from flask import Blueprint, request, jsonify
from app.services.firebase_service import verify_id_token

test_bp = Blueprint("test", __name__)

@test_bp.route("/protected", methods=["GET"])
def protected_route():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    user = verify_id_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "message": f"Welcome {user['email']}",
        "uid": user["uid"]
    }), 200
