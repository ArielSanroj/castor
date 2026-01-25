"""
API v1 routes for Core Service.
"""
from flask import Blueprint

# Create v1 blueprint
v1_bp = Blueprint('v1', __name__, url_prefix='/v1')

# Import and register v1 routes
from app.routes.v1.auth import auth_v1_bp
from app.routes.v1.users import users_v1_bp

v1_bp.register_blueprint(auth_v1_bp)
v1_bp.register_blueprint(users_v1_bp)
