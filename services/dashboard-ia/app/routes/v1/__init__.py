"""
API v1 routes for Dashboard IA Service.
"""
from flask import Blueprint

v1_bp = Blueprint('v1', __name__, url_prefix='/v1')

from app.routes.v1.sentiment import sentiment_v1_bp
from app.routes.v1.twitter import twitter_v1_bp
from app.routes.v1.rag import rag_v1_bp
from app.routes.v1.forecast import forecast_v1_bp

v1_bp.register_blueprint(sentiment_v1_bp)
v1_bp.register_blueprint(twitter_v1_bp)
v1_bp.register_blueprint(rag_v1_bp)
v1_bp.register_blueprint(forecast_v1_bp)
