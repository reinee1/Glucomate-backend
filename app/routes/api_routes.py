# app/routes/api_routes.py
from flask import Blueprint

bp = Blueprint('api', __name__)

@bp.route('/api')
def api_test():
    return {"message": "API routes working!"}