# app/__init__.py
from flask import Flask, jsonify
from .extensions import db
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from flask_jwt_extended import exceptions as jwt_exceptions
FRONTEND_URL = "http://localhost:5173"  

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql://postgres:Glucomate123@database-glucomate.cwt606ekoliv.us-east-1.rds.amazonaws.com:5432/Glucomate_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["EMAIL_ENABLED"] = os.getenv("EMAIL_ENABLED", "true").lower() == "true"
    app.config['SMTP_HOST'] = os.getenv('SMTP_HOST')
    app.config['SMTP_PORT'] = os.getenv('SMTP_PORT')
    app.config['SMTP_USER'] = os.getenv('SMTP_USER')
    app.config['SMTP_PASS'] = os.getenv('SMTP_PASS')
    app.config['PUBLIC_BASE_URL'] = 'http://127.0.0.1:5000'
    
    
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret')  

    db.init_app(app)
    Migrate(app, db)
    jwt = JWTManager(app)

    CORS(app, 
         origins=["http://localhost:5173", "http://127.0.0.1:5173"],
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = FRONTEND_URL
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.errorhandler(Exception)
    def handle_error(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return jsonify(success=False, message=e.description), e.code
        return jsonify(success=False, message=str(e)), 500

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(err_msg):
        return jsonify({"success": False, "message": f"Invalid token: {err_msg}"}), 422

    @jwt.unauthorized_loader
    def missing_token_callback(err_msg):
        return jsonify({"success": False, "message": f"Missing token: {err_msg}"}), 401

    from .routes.auth_routes import auth_bp
    from .routes.medicalinfo_routes import medical_profile_bp
    from .routes.chat_routes import chat_bp
    
    app.register_blueprint(chat_bp)
    app.register_blueprint(medical_profile_bp)   
    app.register_blueprint(auth_bp)

    return app

