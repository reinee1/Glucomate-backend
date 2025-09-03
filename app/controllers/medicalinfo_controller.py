import json
import datetime
from sqlalchemy.exc import IntegrityError
from flask import request, jsonify
from app.extensions import db
from app.models import MedicalProfile
from app.models import MedicalHistory
from app.models import UserMedication
from app.models import Monitoring
from app.models import Lifestyle
from app.models import Allergy     
from app.models import Condition
from sqlalchemy import func

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
    """
    Save medical history data, medications, allergies, and (insert-only) conditions for a user.
    NOTE: This version matches your models: UserMedication has NO `medical_history_id`,
          and (assuming) Allergy is (id, user_id, name, ...). We therefore do not pass
          `medical_history_id` when inserting those rows.
    """
    # -------- Step 1: Get user ID from JWT --------
    try:
        identity = get_jwt_identity()
        try:
            user_id = int(identity)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # -------- Step 2: Get request data --------
    data = request.get_json() or {}
    required_fields = ["medicalConditions", "familyHeartDisease", "takingInsulin"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

    # -------- Step 3: Conditional validation --------
    if data["familyHeartDisease"] and not data.get("familyMember"):
        return jsonify({"success": False, "message": "Please specify family member with heart disease"}), 422

    if data["takingInsulin"]:
        insulin_fields = ["insulinType", "insulinDosage", "insulinSchedule"]
        missing_insulin = [f for f in insulin_fields if not (data.get(f) or "").strip()]
        if missing_insulin:
            return jsonify({"success": False, "message": f"Missing insulin info: {missing_insulin}"}), 422

    # -------- Normalize MEDICAL CONDITIONS (strings or {name}) --------
    raw_conditions = data.get("medicalConditions", []) or []
    norm_conditions = []
    for item in raw_conditions:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = (item.get("name") or "").strip()
        else:
            candidate = ""
        if candidate:
            norm_conditions.append(candidate)

    # case-insensitive de-dup while preserving first spelling
    seen_cond = set()
    deduped_conditions = []
    for name in norm_conditions:
        low = name.lower()
        if low not in seen_cond:
            seen_cond.add(low)
            deduped_conditions.append(name)

    # -------- Normalize ALLERGIES (strings or {name}) --------
    raw_allergies = data.get("allergies", []) or []
    norm_allergies = []
    for item in raw_allergies:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = (item.get("name") or "").strip()
        else:
            candidate = ""
        if candidate:
            norm_allergies.append(candidate)

    seen_allerg = set()
    deduped_allergies = []
    for a in norm_allergies:
        low = a.lower()
        if low not in seen_allerg:
            seen_allerg.add(low)
            deduped_allergies.append(a)

    # -------- Step 4: Save MedicalHistory + Conditions + Meds + Allergies --------
    try:
        # 4a) Upsert MedicalHistory (1:1 per user)
        history = MedicalHistory.query.filter_by(user_id=user_id).first()
        if not history:
            history = MedicalHistory(user_id=user_id)

        history.family_history_heart_disease = bool(data["familyHeartDisease"])
        history.currently_on_insulin = bool(data["takingInsulin"])
        history.family_member = (data.get("familyMember") or "").strip() or None
        history.insulin_type = (data.get("insulinType") or "").strip() or None
        history.insulin_dosage = (data.get("insulinDosage") or "").strip() or None
        history.insulin_schedule = (data.get("insulinSchedule") or "").strip() or None

        db.session.add(history)
        db.session.flush()  # ensures history.id if needed later

        # 4b) CONDITIONS: insert-only into Condition table (no linking)
        if deduped_conditions:
            lower_names = [n.lower() for n in deduped_conditions]

            existing_rows = (
                db.session.query(Condition.name)
                .filter(func.lower(Condition.name).in_(lower_names))
                .all()
            )
            existing_set = {name.lower() for (name,) in existing_rows}

            to_create = [Condition(name=n) for n in deduped_conditions if n.lower() not in existing_set]
            if to_create:
                db.session.add_all(to_create)

        # 4c) Medications: replace for this user (NO medical_history_id in your model)
        medications = data.get("medications", []) or []
        UserMedication.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        for med in medications:
            name = (med.get("medication_name") or "").strip()
            if not name:
                continue
            db.session.add(UserMedication(
                user_id=user_id,
                medication_name=name,
                dosage=(med.get("dosage") or "").strip(),
                frequency=(med.get("frequency") or "").strip(),
            ))

        # 4d) Allergies: replace for this user (assumes Allergy has fields: id, user_id, name)
        Allergy.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        if deduped_allergies:
            db.session.add_all([
                Allergy(name=a, user_id=user_id) for a in deduped_allergies
            ])

        # 4e) Commit once
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Medical history, medications, allergies saved; conditions inserted into Condition table.",
            "counts": {
                "conditions_inserted_or_existing": len(deduped_conditions),
                "medications": len(medications),
                "allergies": len(deduped_allergies),
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error saving data", "error": str(e)}), 500

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
    """
    Update medical history, medications, allergies, and medical conditions for a user.

    Requires (in JSON body):
      - medicalConditions: [str | {"name": str}]
      - familyHeartDisease: bool
      - takingInsulin: bool
    Optional:
      - familyMember: str
      - insulinType / insulinDosage / insulinSchedule
      - medications: [{ medication_name, dosage, frequency }]
      - allergies: [str | {"name": str}]

    Notes:
      - Conditions are upserted into the Condition catalog table.
      - If a UserCondition link table exists, user links are replaced.
      - Else, if MedicalHistory has `medical_conditions` column, it will be set.
    """
    from sqlalchemy import func  # make sure this import exists at file top in your codebase too

    # Try to import an optional link model user_condition (if your app has it)
    try:
        from app.models.user_condition import UserCondition  # type: ignore
        HAS_USER_CONDITION = True
    except Exception:
        HAS_USER_CONDITION = False

    # ---- Step 1: JWT user (authorize) ----
    try:
        identity = get_jwt_identity()
        try:
            token_user_id = int(identity)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid user ID format in token"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": "Invalid token", "error": str(e)}), 401

    # Optional: ensure the caller is updating their own record
    if token_user_id != int(user_id):
        return jsonify({"success": False, "message": "Forbidden: cannot update another user's data"}), 403

    # ---- Step 2: Parse body ----
    data = request.get_json() or {}

    required_fields = ["medicalConditions", "familyHeartDisease", "takingInsulin"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {missing}"}), 422

    if data["familyHeartDisease"] and not (data.get("familyMember") or "").strip():
        return jsonify({"success": False, "message": "Please specify family member with heart disease"}), 422

    if data["takingInsulin"]:
        insulin_fields = ["insulinType", "insulinDosage", "insulinSchedule"]
        missing_insulin = [f for f in insulin_fields if not (data.get(f) or "").strip()]
        if missing_insulin:
            return jsonify({"success": False, "message": f"Missing insulin info: {missing_insulin}"}), 422

    # ---- Normalize medical conditions ----
    raw_conditions = data.get("medicalConditions", []) or []
    norm_conditions = []
    for item in raw_conditions:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = (item.get("name") or "").strip()
        else:
            candidate = ""
        if candidate:
            norm_conditions.append(candidate)

    # case-insensitive de-dup while preserving first spelling
    seen_c = set()
    deduped_conditions = []
    for name in norm_conditions:
        low = name.lower()
        if low not in seen_c:
            seen_c.add(low)
            deduped_conditions.append(name)

    # ---- Normalize allergies ----
    raw_allergies = data.get("allergies", []) or []
    norm_allergies = []
    for item in raw_allergies:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = (item.get("name") or "").strip()
        else:
            candidate = ""
        if candidate:
            norm_allergies.append(candidate)

    seen_a = set()
    deduped_allergies = []
    for a in norm_allergies:
        low = a.lower()
        if low not in seen_a:
            seen_a.add(low)
            deduped_allergies.append(a)

    # ---- Step 3: Update DB ----
    try:
        # 3a) MedicalHistory
        history = MedicalHistory.query.filter_by(user_id=user_id).first()
        if not history:
            return jsonify({"success": False, "message": "Medical history not found"}), 404

        history.family_history_heart_disease = bool(data["familyHeartDisease"])
        history.currently_on_insulin = bool(data["takingInsulin"])
        history.family_member = (data.get("familyMember") or "").strip() or None
        history.insulin_type = (data.get("insulinType") or "").strip() or None
        history.insulin_dosage = (data.get("insulinDosage") or "").strip() or None
        history.insulin_schedule = (data.get("insulinSchedule") or "").strip() or None

        # If your schema has a JSON/TEXT column to keep user's own list, set it too
        if hasattr(history, "medical_conditions"):
            setattr(history, "medical_conditions", deduped_conditions)

        db.session.add(history)
        db.session.flush()

        # 3b) Upsert catalog Condition rows and update user links (if link table exists)
        if deduped_conditions:
            lower_names = [n.lower() for n in deduped_conditions]

            existing_rows = (
                db.session.query(Condition.id, Condition.name)
                .filter(func.lower(Condition.name).in_(lower_names))
                .all()
            )
            existing_by_lower = {name.lower(): cid for cid, name in existing_rows}

            # create missing
            to_create = [Condition(name=n) for n in deduped_conditions if n.lower() not in existing_by_lower]
            if to_create:
                db.session.add_all(to_create)
                db.session.flush()
                # re-query to include new ones
                refreshed = (
                    db.session.query(Condition.id, Condition.name)
                    .filter(func.lower(Condition.name).in_(lower_names))
                    .all()
                )
                existing_by_lower = {name.lower(): cid for cid, name in refreshed}

            # link to user if link table exists
            if HAS_USER_CONDITION:
                UserCondition.query.filter_by(user_id=user_id).delete(synchronize_session=False)
                db.session.add_all([
                    UserCondition(user_id=user_id, condition_id=existing_by_lower[n.lower()])
                    for n in deduped_conditions
                ])
        else:
            # if client sends empty, clear links if present
            if HAS_USER_CONDITION:
                UserCondition.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        # 3c) Replace medications
        medications = data.get("medications", []) or []
        UserMedication.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        for med in medications:
            name = (med.get("medication_name") or "").strip()
            if not name:
                continue
            db.session.add(UserMedication(
                user_id=user_id,
                medication_name=name,
                dosage=(med.get("dosage") or "").strip(),
                frequency=(med.get("frequency") or "").strip(),
            ))

        # 3d) Replace allergies
        Allergy.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        if deduped_allergies:
            db.session.add_all([Allergy(name=a, user_id=user_id) for a in deduped_allergies])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Medical history, medications, allergies, and conditions updated successfully.",
            "counts": {
                "conditions": len(deduped_conditions),
                "medications": len(medications),
                "allergies": len(deduped_allergies),
            }
        }), 200

    except Exception as e:
        db.session.rollback()
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
def _date_to_ymd(d: datetime.date):
    if not d:
        return None, None, None
    return d.year, d.month, d.day


@jwt_required()
def get_full_profile():
    """Fetch the user's full medical profile, including (if available) their medical conditions
    and a global catalog of known conditions.
    - If your MedicalHistory model has a field like `medical_conditions` (JSON/ARRAY/TEXT),
      we will return it as `medicalConditions`.
    - Independently, we also return `conditionCatalog` (all condition names in the Condition table).
    """
    user_id = int(get_jwt_identity())

    profile = MedicalProfile.query.filter_by(user_id=user_id).first()
    y, m, d = _date_to_ymd(profile.date_of_birth) if profile else (None, None, None)

    history = MedicalHistory.query.filter_by(user_id=user_id).first()
    meds = UserMedication.query.filter_by(user_id=user_id).all()
    allergies = Allergy.query.filter_by(user_id=user_id).all()
    monitoring = Monitoring.query.filter_by(user_id=user_id).first()
    lifestyle = Lifestyle.query.filter_by(user_id=user_id).first()

    # --- User-specific medical conditions (if your schema stores them on MedicalHistory) ---
    user_medical_conditions = None
    if history is not None:
        # Try to read a field named `medical_conditions` if it exists
        if hasattr(history, "medical_conditions"):
            raw_mc = getattr(history, "medical_conditions")
            # Accept list directly, or JSON string that parses to a list
            if isinstance(raw_mc, list):
                user_medical_conditions = raw_mc
            elif isinstance(raw_mc, str):
                try:
                    import json
                    parsed = json.loads(raw_mc)
                    if isinstance(parsed, list):
                        user_medical_conditions = parsed
                    else:
                        # keep raw string if not a list
                        user_medical_conditions = raw_mc
                except Exception:
                    user_medical_conditions = raw_mc  # not JSON; return as-is
            else:
                # fallback: just return whatever type is stored
                user_medical_conditions = raw_mc

    # --- Global catalog of known condition names (insert-only Condition table) ---
    condition_rows = db.session.query(Condition.name).order_by(Condition.name.asc()).all()
    condition_catalog = [name for (name,) in condition_rows]

    return jsonify({
        "success": True,
        "data": {
            "personalInfo": None if not profile else {
                "birthDateISO": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                "birthYear": y, "birthMonth": m, "birthDay": d,
                "gender": profile.gender,
                "heightCm": profile.height,
                "weightKg": profile.weight,
                "diabetesType": profile.diabetes_type,
                "diagnosisYear": profile.diagnosis_year,
            },
            "medicalHistory": None if (not history and not meds and not allergies) else {
                "familyHeartDisease": (bool(history.family_history_heart_disease) if history is not None else None),
                "takingInsulin": (bool(history.currently_on_insulin) if history is not None else None),
                # User-specific conditions if stored on MedicalHistory (else null)
                "medicalConditions": user_medical_conditions,
                # Catalog of all known conditions in the system (global, not user-linked)
                "conditionCatalog": condition_catalog,
                "medications": [
                    {"medication_name": m.medication_name, "dosage": m.dosage, "frequency": m.frequency}
                    for m in meds
                ],
                "allergies": [a.name for a in allergies],
            },
            "monitoring": None if not monitoring else {
                "bloodSugarMonitoring": monitoring.glucose_frequency,
                "hba1cReading": monitoring.latest_hba1c_percent,
                "usesCGM": "yes" if monitoring.uses_cgm else "no",
                "frequentHypoglycemia": "yes" if monitoring.frequent_hypoglycemia else "no",
            },
            "lifestyle": None if not lifestyle else {
                "smokingStatus": lifestyle.smoking_status,
                "alcoholConsumption": lifestyle.alcohol_consumption,
                "exerciseFrequency": lifestyle.exercise_frequency,
            }
        }
    }), 200
