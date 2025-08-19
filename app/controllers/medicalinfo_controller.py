from flask import request, jsonify
from app.extensions import db
from app.models import MedicalProfile
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime

# app/controllers/medical_profile_controller.py
from flask import request, jsonify
from app.extensions import db
from app.models import MedicalProfile
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime

@jwt_required()
def save_medical_profile():
    # Step 1: Get user ID from JWT
    try:
        identity = get_jwt_identity()
        print("JWT identity:", identity)  # Debug print to check token contents

        try:
            user_id = int(identity)  # Convert string to int for DB
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity to int:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401

    except Exception as e:
        print("Error reading JWT:", e)
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # Step 2: Get request data
    data = request.get_json() or {}

    required_fields = [
        "birthYear", "birthMonth", "birthDay", "gender",
        "height", "heightUnit", "weight", "weightUnit",
        "diabetesType", "diagnosisYear"
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

    # Step 3: Process and save data
    try:
        # Combine birth date
        birth_date = datetime.date(
            int(data["birthYear"]),
            int(data["birthMonth"]),
            int(data["birthDay"])
        )

        # Convert height/weight to metric
        height = float(data["height"])
        if data["heightUnit"] == "ft/in":
            height = height * 30.48  # Convert feet/inches to cm

        weight = float(data["weight"])
        if data["weightUnit"] == "lb":
            weight = weight * 0.453592  # Convert pounds to kg

        # Check if profile exists
        profile = MedicalProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = MedicalProfile(user_id=user_id)

        # Update profile fields
        profile.date_of_birth = birth_date
        profile.gender = data["gender"]
        profile.height = height
        profile.weight = weight
        profile.diabetes_type = data["diabetesType"]
        profile.diagnosis_year = int(data["diagnosisYear"])

        db.session.add(profile)
        db.session.commit()

        return jsonify({"success": True, "message": "Medical profile saved successfully."}), 201

    except Exception as e:
        db.session.rollback()
        print("Error saving medical profile:", e)  # Debug print
        return jsonify({"success": False, "message": "Error saving profile", "error": str(e)}), 500
