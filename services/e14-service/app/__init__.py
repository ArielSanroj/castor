"""
Flask application factory for E-14 Service.
Handles electoral form processing, OCR, and ingestion.
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
    Application factory for E-14 Service.

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
        return response

    # Configure logging
    log_level = getattr(logging, config_class.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Initialize E-14 services
    try:
        from app.services.e14_ocr_service import E14OCRService
        from app.services.e14_ingestion_pipeline import E14IngestionPipeline

        app.extensions['e14_ocr_service'] = E14OCRService()
        app.extensions['e14_pipeline'] = E14IngestionPipeline()
        logging.info("E-14 services initialized")
    except Exception as exc:
        logging.warning(f"E-14 services not fully initialized: {exc}")
        app.extensions['e14_ocr_service'] = None
        app.extensions['e14_pipeline'] = None

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.electoral import electoral_bp
    from app.routes.ingestion import ingestion_bp
    from app.routes.review import review_bp

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(electoral_bp, url_prefix='/api/e14')
    app.register_blueprint(ingestion_bp, url_prefix='/api/pipeline')
    app.register_blueprint(review_bp, url_prefix='/api/review')

    # Register v1 API routes
    from app.routes.v1 import v1_bp
    app.register_blueprint(v1_bp, url_prefix='/api')

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

    logging.info(f"E-14 Service initialized on port {config_class.PORT}")

    return app
