from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()  # Loads the .env file

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register all blueprints (routes)
    from app.routes.test_routes import test_bp
    app.register_blueprint(test_bp)

    return app
