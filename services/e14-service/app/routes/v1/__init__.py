"""
API v1 routes for E-14 Service.
"""
from flask import Blueprint

v1_bp = Blueprint('v1', __name__, url_prefix='/v1')

from app.routes.v1.e14 import e14_v1_bp
from app.routes.v1.pipeline import pipeline_v1_bp

v1_bp.register_blueprint(e14_v1_bp)
v1_bp.register_blueprint(pipeline_v1_bp)
