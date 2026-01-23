"""
Flask application factory for CASTOR ELECCIONES.
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import sys

try:
    from flask_compress import Compress
    compress = Compress()
    COMPRESS_AVAILABLE = True
except ImportError:
    compress = None
    COMPRESS_AVAILABLE = False

from config import Config, config as config_map
from utils.rate_limiter import init_rate_limiter
from utils.cache import init_cache
from services.background_jobs import init_background_jobs
from app.services.analysis_core import AnalysisCorePipeline
from app.services.topic_classifier_service import TopicClassifierService
from app.services.chart_service import ChartService
# Service imports moved inside create_app to avoid circular imports

# Initialize extensions
cors = CORS()
jwt = JWTManager()


def create_app(config_name: str = 'default') -> Flask:
    """
    Application factory pattern.
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Flask application instance
    """
    # Determine template and static folders
    # Check if templates exist in parent directory (root of project)
    import os
    # __file__ is backend/app/__init__.py
    # os.path.dirname(__file__) = backend/app/
    # os.path.dirname(os.path.dirname(__file__)) = backend/
    # os.path.dirname(os.path.dirname(os.path.dirname(__file__))) = project root
    backend_dir = os.path.dirname(os.path.dirname(__file__))  # backend/
    project_root = os.path.dirname(backend_dir)  # project root
    parent_templates = os.path.join(project_root, 'templates')
    parent_static = os.path.join(project_root, 'static')
    
    template_folder = parent_templates if os.path.exists(parent_templates) else 'templates'
    static_folder = parent_static if os.path.exists(parent_static) else 'static'
    
    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder
    )
    
    # Load configuration based on requested environment
    config_class = config_map.get(config_name, Config)
    try:
        config_class.validate()
    except ValueError as exc:
        # Allow dev/default to boot with warnings; enforce in other environments
        is_dev_env = getattr(config_class, "DEBUG", False) or config_name in ('development', 'default')
        if is_dev_env:
            logging.warning("Configuration validation warning: %s", exc)
        else:
            raise
    app.config.from_object(config_class)
    
    # Initialize extensions
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    jwt.init_app(app)

    # HTTPS enforcement in production
    if not app.debug and os.environ.get('FORCE_HTTPS', 'true').lower() == 'true':
        from flask import request, redirect

        @app.before_request
        def enforce_https():
            """Redirect HTTP to HTTPS in production."""
            # Check X-Forwarded-Proto header (set by reverse proxy/load balancer)
            if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
                if request.url.startswith('http://'):
                    url = request.url.replace('http://', 'https://', 1)
                    return redirect(url, code=301)

        @app.after_request
        def add_security_headers(response):
            """Add security headers to all responses."""
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            # HSTS - only enable in production with valid SSL
            if os.environ.get('ENABLE_HSTS', 'false').lower() == 'true':
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
    
    # Initialize rate limiting
    init_rate_limiter(app)

    # Initialize caching
    init_cache()

    # Initialize response compression (if available)
    if COMPRESS_AVAILABLE and compress:
        app.config['COMPRESS_ALGORITHM'] = 'gzip'
        app.config['COMPRESS_LEVEL'] = 6
        app.config['COMPRESS_MIN_SIZE'] = 500
        compress.init_app(app)

    # Initialize background jobs
    init_background_jobs()

    # Configure logging with multiple handlers
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Create handlers list
    handlers = [logging.StreamHandler(sys.stdout)]
    if Config.LOG_FILE:
        handlers.append(logging.FileHandler(Config.LOG_FILE))

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    # Initialize shared pipeline (best-effort, non-fatal)
    try:
        # Import services here to avoid circular imports
        from services.twitter_service import TwitterService
        from services.sentiment_service import SentimentService
        from services.trending_service import TrendingService
        from services.database_service import DatabaseService
        from services.openai_service import OpenAIService

        topic_classifier = TopicClassifierService()
        chart_service = ChartService()
        twitter_service = TwitterService()
        sentiment_service = SentimentService()
        trending_service = TrendingService()
        db_service = DatabaseService()
        analysis_core = AnalysisCorePipeline(
            twitter_service=twitter_service,
            sentiment_service=sentiment_service,
            trending_service=trending_service,
            topic_classifier_service=topic_classifier,
            chart_service=chart_service,
            db_service=db_service
        )
        app.extensions["analysis_core_pipeline"] = analysis_core
        app.extensions["twitter_service"] = twitter_service
        app.extensions["sentiment_service"] = sentiment_service
        app.extensions["database_service"] = db_service
        
        # Initialize OpenAI separately to catch specific errors
        try:
            openai_service = OpenAIService()
            app.extensions["openai_service"] = openai_service
        except Exception as openai_exc:
            logging.warning(f"OpenAI service not initialized: {openai_exc}")
            app.extensions["openai_service"] = None

        # Initialize RAG service with database connection
        try:
            from services.rag_service import init_rag_service
            rag_service = init_rag_service(db_service=db_service)
            app.extensions["rag_service"] = rag_service
            logging.info(f"RAG service initialized with {rag_service.vector_store.count()} documents")
        except Exception as rag_exc:
            logging.warning(f"RAG service not initialized: {rag_exc}")
            app.extensions["rag_service"] = None
            
    except Exception as exc:
        logging.warning(f"Core analysis services not fully initialized: {exc}")
        app.extensions["analysis_core_pipeline"] = None
        app.extensions["openai_service"] = None

    # Register blueprints
    from app.routes import analysis_bp, chat_bp, health_bp, auth_bp, campaign_bp, web_bp, leads_bp, media_bp, forecast_bp, advisor_bp
    app.register_blueprint(web_bp)  # No prefix for web routes
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(media_bp, url_prefix='/api/media')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(campaign_bp, url_prefix='/api')
    app.register_blueprint(leads_bp, url_prefix='/api')
    app.register_blueprint(forecast_bp, url_prefix='/api/forecast')
    app.register_blueprint(advisor_bp, url_prefix='/api')
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request'}, 400
    
    return app
