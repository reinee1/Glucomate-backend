from flask import Blueprint
from sqlalchemy import text
from app.extensions import db
from app.helpers import api_response

# This must come BEFORE any route decorators
bp = Blueprint('test', __name__)

@bp.route('/test')
def test_endpoint():
    return api_response(True, "Test successful", {"version": "1.0.0"})

@bp.route('/test-db')
def test_db_connection():
    try:
        db.session.execute(text('SELECT 1'))
        return api_response(
            success=True,
            message="Database connection successful",
            data={"status": "connected"}
        )
    except Exception as e:
        return api_response(
            success=False,
            message="Database connection failed",
            data={"error": str(e)},
            status_code=500
        )