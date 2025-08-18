# app/__init__.py
from flask import Flask, jsonify
from .extensions import db
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
load_dotenv()
def create_app():
    app = Flask(__name__)

    # Config (recommend env vars instead of hardcoding)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://postgres:Glucomate123@database-glucomate.cwt606ekoliv.us-east-1.rds.amazonaws.com:5432/Glucomate_db'
)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["EMAIL_ENABLED"] = os.getenv("EMAIL_ENABLED", "true").lower() == "true"
    app.config['SMTP_HOST'] = os.getenv('SMTP_HOST')
    app.config['SMTP_PORT'] = os.getenv('SMTP_PORT')
    app.config['SMTP_USER'] = os.getenv('SMTP_USER')
    app.config['SMTP_PASS'] = os.getenv('SMTP_PASS')
    app.config['PUBLIC_BASE_URL'] = 'http://127.0.0.1:5000'  # or your actual public URL
    # Init extensions
    db.init_app(app)
    Migrate(app, db)
    @app.errorhandler(Exception)
    def handle_error(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return jsonify(success=False, message=e.description), e.code
        # log e here if you want
        return jsonify(success=False, message=str(e)), 500

    # ⬇️ Import AFTER db.init_app so Alembic sees models
    from app import models  # app/models/__init__.py must import your submodules

    # Blueprints
    from .routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)


    return app
