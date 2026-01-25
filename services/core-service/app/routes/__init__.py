"""Routes package for Core Service."""
from app.routes.health import health_bp
from app.routes.auth import auth_bp
from app.routes.leads import leads_bp
from app.routes.internal import internal_bp

__all__ = ['health_bp', 'auth_bp', 'leads_bp', 'internal_bp']
