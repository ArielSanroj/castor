"""
Flask application factory for Dashboard IA Service.
Handles electoral strategy, Twitter analysis, sentiment, RAG, and forecasting.
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
    Application factory for Dashboard IA Service.

    Args:
        config_name: Configuration name (development, production, testing)

    Returns:
        Flask application instance
    """
    app = Flask(
        __name__,
        template_folder='../../templates',
        static_folder='../../static'
    )

    # Load configuration
    from config import config as config_map
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

    # Initialize services
    try:
        from services.twitter_service import TwitterService
        from services.sentiment_service import SentimentService
        from services.trending_service import TrendingService
        from services.database_service import DatabaseService
        from services.openai_service import OpenAIService
        from services.rag_service import RAGService

        db_service = DatabaseService()
        twitter_service = TwitterService()
        sentiment_service = SentimentService()
        trending_service = TrendingService()

        app.extensions['database_service'] = db_service
        app.extensions['twitter_service'] = twitter_service
        app.extensions['sentiment_service'] = sentiment_service
        app.extensions['trending_service'] = trending_service

        # OpenAI service
        try:
            openai_service = OpenAIService()
            app.extensions['openai_service'] = openai_service
        except Exception as e:
            logging.warning(f"OpenAI service not initialized: {e}")
            app.extensions['openai_service'] = None

        # RAG service
        try:
            rag_service = RAGService(db_service=db_service)
            app.extensions['rag_service'] = rag_service
            logging.info(f"RAG service initialized")
        except Exception as e:
            logging.warning(f"RAG service not initialized: {e}")
            app.extensions['rag_service'] = None

        logging.info("Dashboard IA services initialized")

    except Exception as exc:
        logging.warning(f"Services not fully initialized: {exc}")

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.media import media_bp
    from app.routes.chat import chat_bp
    from app.routes.campaign import campaign_bp
    from app.routes.campaign_team import campaign_team_bp
    from app.routes.forecast import forecast_bp
    from app.routes.advisor import advisor_bp

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(media_bp, url_prefix='/api/media')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(campaign_bp, url_prefix='/api/campaign')
    app.register_blueprint(campaign_team_bp, url_prefix='/api/team')
    app.register_blueprint(forecast_bp, url_prefix='/api/forecast')
    app.register_blueprint(advisor_bp, url_prefix='/api/advisor')

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

    logging.info(f"Dashboard IA Service initialized on port {config_class.PORT}")

    return app
