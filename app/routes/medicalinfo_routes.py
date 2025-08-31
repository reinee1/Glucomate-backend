# app/routes/medicalinfo_routes.py
from flask import Blueprint
from app.controllers import medicalinfo_controller

medical_profile_bp = Blueprint("medical_profile", __name__, url_prefix="/api/v1/medical-profile")

medical_profile_bp.route("/personalinfo", methods=["POST"])(medicalinfo_controller.save_medical_profile)
medical_profile_bp.route("/medicalhistory", methods=["POST"])(medicalinfo_controller.save_medical_history)
medical_profile_bp.route("/monitoringinfo", methods=["POST"])(medicalinfo_controller.save_monitoring_info)
medical_profile_bp.route("/lifestylehabits", methods=["POST"])(medicalinfo_controller.save_lifestyle_habits)



# New PUT routes for updates
medical_profile_bp.route("/personalinfo/<int:user_id>", methods=["PUT"])(medicalinfo_controller.update_medical_profile)
medical_profile_bp.route("/medicalhistory/<int:user_id>", methods=["PUT"])(medicalinfo_controller.update_medical_history)
medical_profile_bp.route("/monitoringinfo/<int:user_id>", methods=["PUT"])(medicalinfo_controller.update_monitoring_info)
medical_profile_bp.route("/lifestylehabits/<int:user_id>", methods=["PUT"])(medicalinfo_controller.update_lifestyle_habits)