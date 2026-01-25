"""
Flask application factory for Core Service.
Handles authentication, users, and shared infrastructure.
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
import logging
import sys
import os

# Initialize extensions
cors = CORS()
jwt = JWTManager()
db = SQLAlchemy()


def create_app(config_name: str = 'default') -> Flask:
    """
    Application factory for Core Service.

    Args:
        config_name: Configuration name (development, production, testing)

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    from config import config as config_map, Config
    config_class = config_map.get(config_name, config_map['default'])

    try:
        config_class.validate()
    except ValueError as exc:
        if config_class.DEBUG or config_name in ('development', 'default'):
            logging.warning("Configuration validation warning: %s", exc)
        else:
            raise

    app.config.from_object(config_class)

    # Initialize extensions
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": config_class.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    jwt.init_app(app)
    db.init_app(app)

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Configure logging
    log_level = getattr(logging, config_class.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.auth import auth_bp
    from app.routes.leads import leads_bp

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(leads_bp, url_prefix='/api/leads')

    # Register v1 API routes
    from app.routes.v1 import v1_bp
    app.register_blueprint(v1_bp, url_prefix='/api')

    # JWT validation endpoint for other services
    from app.routes.internal import internal_bp
    app.register_blueprint(internal_bp, url_prefix='/internal')

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500

    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request'}, 400

    # Create database tables
    with app.app_context():
        db.create_all()

    logging.info(f"Core Service initialized on port {config_class.PORT}")

    return app
