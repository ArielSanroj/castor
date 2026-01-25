"""Routes package for E-14 Service."""
from app.routes.health import health_bp
from app.routes.electoral import electoral_bp
from app.routes.ingestion import ingestion_bp
from app.routes.review import review_bp

__all__ = ['health_bp', 'electoral_bp', 'ingestion_bp', 'review_bp']
