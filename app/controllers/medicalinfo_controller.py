import json
import datetime

from flask import request, jsonify
from app.extensions import db
from app.models import MedicalProfile
from app.models import MedicalHistory
from app.models import UserMedication
from app.models import Monitoring
from app.models import Lifestyle
from flask_jwt_extended import jwt_required, get_jwt_identity


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

@jwt_required()
def save_medical_history():
    """Save medical history data and medications for a user"""
    # Step 1: Get user ID from JWT
    try:
        identity = get_jwt_identity()
        print("JWT identity:", identity)  # Debug
        try:
            user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity to int:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401
    except Exception as e:
        print("Error reading JWT:", e)
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # Step 2: Get request data
    data = request.get_json() or {}
    print("Received medical history data:", data)

    required_fields = ["medicalConditions", "familyHeartDisease", "takingInsulin"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

    # Step 3: Conditional validation
    if data["familyHeartDisease"] and not data.get("familyMember"):
        return jsonify({"success": False, "message": "Please specify family member with heart disease"}), 422

    if data["takingInsulin"]:
        insulin_fields = ["insulinType", "insulinDosage", "insulinSchedule"]
        missing_insulin = [f for f in insulin_fields if not data.get(f)]
        if missing_insulin:
            return jsonify({"success": False, "message": f"Missing insulin info: {missing_insulin}"}), 422

    # Step 4: Save MedicalHistory and medications
    try:
        # 4a: Get or create MedicalHistory record
        history = MedicalHistory.query.filter_by(user_id=user_id).first()
        if not history:
            history = MedicalHistory(user_id=user_id)

        history.family_history_heart_disease = bool(data["familyHeartDisease"])
        history.currently_on_insulin = bool(data["takingInsulin"])

        db.session.add(history)
        db.session.commit()
        print("Medical history saved:", history.id)

        # Step 5: Save medications in the same style as MedicalHistory
        medications = data.get("medications", [])
        # Delete old medications (optional)
        UserMedication.query.filter_by(user_id=user_id).delete()

        for med in medications:
            name = med.get("medication_name")  # must match model field
            if not name:
                continue  # skip invalid entries

            # Check if medication already exists
            existing_med = UserMedication.query.filter_by(user_id=user_id, medication_name=name).first()
            if not existing_med:
                existing_med = UserMedication(user_id=user_id, medication_name=name)

            # Update fields
            existing_med.dosage = med.get("dosage", "")
            existing_med.frequency = med.get("frequency", "")
            db.session.add(existing_med)

        # Commit all medications
        db.session.commit()
        print(f"Saved {len(medications)} medications for user {user_id}")

        return jsonify({"success": True, "message": "Medical history and medications saved successfully."}), 201

    except Exception as e:
        db.session.rollback()
        print("Error saving medical history:", e)
        return jsonify({"success": False, "message": "Error saving medical history", "error": str(e)}), 500

@jwt_required()
def save_monitoring_info():
    """Save monitoring and control data from the monitoring form"""
    try:
        # Step 1: Get user ID from JWT
        identity = get_jwt_identity()
        print("JWT identity:", identity)  # Debug
        try:
            user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401

        # Step 2: Get request data
        data = request.get_json() or {}
        print("Received monitoring data:", data)

        # Step 3: Validate required fields
        required_fields = ["bloodSugarMonitoring", "usesCGM", "frequentHypoglycemia"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

        # Conditional validation
        if data["usesCGM"] == "yes" and not data.get("cgmFrequency"):
            return jsonify({"success": False, "message": "Please specify how often you check your CGM"}), 422

        if data["frequentHypoglycemia"] == "yes" and not data.get("hypoglycemiaFrequency"):
            return jsonify({"success": False, "message": "Please specify how often you experience hypoglycemia"}), 422

        # Validate HbA1c if provided
        hba1c = None
        if data.get("hba1cReading"):
            try:
                hba1c = float(data["hba1cReading"])
                if hba1c < 4 or hba1c > 20:
                    return jsonify({"success": False, "message": "Please enter a valid HbA1c reading (between 4% and 20%)"}), 422
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "Please enter a valid numeric value for HbA1c"}), 422

        # Step 4: Get or create Monitoring record
        monitoring = Monitoring.query.filter_by(user_id=user_id).first()
        if not monitoring:
            monitoring = Monitoring(user_id=user_id)

        # Step 5: Update monitoring fields
        monitoring.glucose_frequency = data["bloodSugarMonitoring"]
        monitoring.latest_hba1c_percent = hba1c
        monitoring.uses_cgm = data["usesCGM"] == "yes"
        monitoring.frequent_hypoglycemia = data["frequentHypoglycemia"] == "yes"

        db.session.add(monitoring)
        db.session.commit()
        print("Monitoring saved:", monitoring.id)

        return jsonify({"success": True, "message": "Monitoring information saved successfully."}), 201

    except Exception as e:
        db.session.rollback()
        print("Error saving monitoring information:", e)
        return jsonify({"success": False, "message": "Error saving monitoring information", "error": str(e)}), 500


@jwt_required()
def save_lifestyle_habits():
    """Save lifestyle habits data from the lifestyle form"""
    try:
        # Step 1: Get user ID from JWT
        identity = get_jwt_identity()
        print("JWT identity:", identity)  # Debug
        try:
            user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401

        # Step 2: Get request data
        data = request.get_json() or {}
        print("Received lifestyle habits data:", data)

        # Step 3: Validate required fields
        required_fields = ["smokingStatus", "alcoholConsumption", "exerciseFrequency"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

        # Step 4: Get or create Lifestyle record
        lifestyle = Lifestyle.query.filter_by(user_id=user_id).first()
        if not lifestyle:
            lifestyle = Lifestyle(user_id=user_id)

        # Step 5: Update lifestyle fields
        lifestyle.smoking_status = data["smokingStatus"]
        lifestyle.alcohol_consumption = data["alcoholConsumption"]
        lifestyle.exercise_frequency = data["exerciseFrequency"]

        db.session.add(lifestyle)
        db.session.commit()
        print("Lifestyle saved:", lifestyle.id)

        return jsonify({"success": True, "message": "Lifestyle habits saved successfully."}), 201

    except Exception as e:
        db.session.rollback()
        print("Error saving lifestyle habits:", e)
        return jsonify({"success": False, "message": "Error saving lifestyle habits", "error": str(e)}), 500
    

@jwt_required()
def update_medical_profile(user_id):
    # Step 1: Get user ID from JWT
    try:
        identity = get_jwt_identity()
        print("JWT identity:", identity)  # Debug print
        try:
            token_user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401
    except Exception as e:
        print("Error reading JWT:", e)
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # Step 2: Get request data
    data = request.get_json() or {}

    # Step 3: Ensure the profile exists
    profile = MedicalProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"success": False, "message": "Medical profile not found"}), 404

    try:
        # Update date_of_birth if birthYear, birthMonth, birthDay provided
        if all(k in data for k in ("birthYear", "birthMonth", "birthDay")):
            profile.date_of_birth = datetime.date(
                int(data["birthYear"]),
                int(data["birthMonth"]),
                int(data["birthDay"])
            )

        # Update gender
        profile.gender = data.get("gender", profile.gender)

        # Update height
        if "height" in data:
            height = float(data["height"])
            if data.get("heightUnit") == "ft/in":
                height *= 30.48
            profile.height = height

        # Update weight
        if "weight" in data:
            weight = float(data["weight"])
            if data.get("weightUnit") == "lb":
                weight *= 0.453592
            profile.weight = weight

        # Update diabetes_type
        profile.diabetes_type = data.get("diabetesType", profile.diabetes_type)

        # Update diagnosis_year
        if "diagnosisYear" in data:
            profile.diagnosis_year = int(data["diagnosisYear"])

        db.session.add(profile)
        db.session.commit()

        return jsonify({"success": True, "message": "Medical profile updated successfully."})

    except Exception as e:
        db.session.rollback()
        print("Error updating medical profile:", e)
        return jsonify({"success": False, "message": "Error updating profile", "error": str(e)}), 500


@jwt_required()
def update_medical_history(user_id):
    """Update medical history data and medications for a user"""
    # Step 1: Get user ID from JWT
    try:
        identity = get_jwt_identity()
        print("JWT identity:", identity)
        try:
            token_user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401
    except Exception as e:
        print("Error reading JWT:", e)
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # Step 2: Get request data
    data = request.get_json() or {}
    print("Received medical history update data:", data)

    # Step 3: Validate required fields
    required_fields = ["medicalConditions", "familyHeartDisease", "takingInsulin"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

    # Step 4: Conditional validation
    if data["familyHeartDisease"] and not data.get("familyMember"):
        return jsonify({"success": False, "message": "Please specify family member with heart disease"}), 422

    if data["takingInsulin"]:
        insulin_fields = ["insulinType", "insulinDosage", "insulinSchedule"]
        missing_insulin = [f for f in insulin_fields if not data.get(f)]
        if missing_insulin:
            return jsonify({"success": False, "message": f"Missing insulin info: {missing_insulin}"}), 422

    # Step 5: Update MedicalHistory and medications
    try:
        history = MedicalHistory.query.filter_by(user_id=user_id).first()
        if not history:
            return jsonify({"success": False, "message": "Medical history not found"}), 404

        history.family_history_heart_disease = bool(data["familyHeartDisease"])
        history.currently_on_insulin = bool(data["takingInsulin"])
        # Add other fields like medicalConditions if present in your model
        # history.medical_conditions = data.get("medicalConditions", history.medical_conditions)

        db.session.add(history)

        # Update medications
        medications = data.get("medications", [])
        # Optionally clear old medications
        UserMedication.query.filter_by(user_id=user_id).delete()

        for med in medications:
            name = med.get("medication_name")
            if not name:
                continue

            existing_med = UserMedication(user_id=user_id, medication_name=name)
            existing_med.dosage = med.get("dosage", "")
            existing_med.frequency = med.get("frequency", "")
            db.session.add(existing_med)

        db.session.commit()
        print(f"Updated medical history and {len(medications)} medications for user {user_id}")

        return jsonify({"success": True, "message": "Medical history and medications updated successfully."})

    except Exception as e:
        db.session.rollback()
        print("Error updating medical history:", e)
        return jsonify({"success": False, "message": "Error updating medical history", "error": str(e)}), 500



@jwt_required()
def update_monitoring_info(user_id):
    """Update monitoring and control data for a user"""
    try:
        # Step 1: Get user ID from JWT
        identity = get_jwt_identity()
        print("JWT identity:", identity)
        try:
            token_user_id = int(identity)
        except (ValueError, TypeError) as e:
            print("Error converting JWT identity:", e)
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401

        # Step 2: Get request data
        data = request.get_json() or {}
        print("Received monitoring update data:", data)

        # Step 3: Validate required fields
        required_fields = ["bloodSugarMonitoring", "usesCGM", "frequentHypoglycemia"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

        # Conditional validation
        if data["usesCGM"] == "yes" and not data.get("cgmFrequency"):
            return jsonify({"success": False, "message": "Please specify how often you check your CGM"}), 422

        if data["frequentHypoglycemia"] == "yes" and not data.get("hypoglycemiaFrequency"):
            return jsonify({"success": False, "message": "Please specify how often you experience hypoglycemia"}), 422

        # Validate HbA1c if provided
        hba1c = None
        if data.get("hba1cReading"):
            try:
                hba1c = float(data["hba1cReading"])
                if hba1c < 4 or hba1c > 20:
                    return jsonify({"success": False, "message": "Please enter a valid HbA1c reading (4-20%)"}), 422
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "HbA1c must be a numeric value"}), 422

        # Step 4: Get existing Monitoring record
        monitoring = Monitoring.query.filter_by(user_id=user_id).first()
        if not monitoring:
            return jsonify({"success": False, "message": "Monitoring record not found"}), 404

        # Step 5: Update fields
        monitoring.glucose_frequency = data["bloodSugarMonitoring"]
        monitoring.latest_hba1c_percent = hba1c
        monitoring.uses_cgm = data["usesCGM"] == "yes"
        monitoring.frequent_hypoglycemia = data["frequentHypoglycemia"] == "yes"

        db.session.add(monitoring)
        db.session.commit()
        print("Monitoring updated:", monitoring.id)

        return jsonify({"success": True, "message": "Monitoring information updated successfully."})

    except Exception as e:
        db.session.rollback()
        print("Error updating monitoring info:", e)
        return jsonify({"success": False, "message": "Error updating monitoring information", "error": str(e)}), 500


@jwt_required()
def update_lifestyle_habits(user_id):
    """Update lifestyle habits for a user"""
    try:
        data = request.get_json() or {}

        lifestyle = Lifestyle.query.filter_by(user_id=user_id).first()
        if not lifestyle:
            return jsonify({"success": False, "message": "Lifestyle record not found"}), 404

        # Update safely
        lifestyle.smoking_status = data.get("smokingStatus", lifestyle.smoking_status)
        lifestyle.alcohol_consumption = data.get("alcoholConsumption", lifestyle.alcohol_consumption)
        lifestyle.exercise_frequency = data.get("exerciseFrequency", lifestyle.exercise_frequency)

        db.session.add(lifestyle)
        db.session.commit()

        return jsonify({"success": True, "message": "Lifestyle habits updated successfully."}), 200

    except Exception as e:
        db.session.rollback()
        print("Error updating lifestyle habits:", e)
        return jsonify({"success": False, "message": "Error updating lifestyle habits", "error": str(e)}), 500
