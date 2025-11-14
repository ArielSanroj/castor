"""
Routes module for CASTOR ELECCIONES API.
"""
from .analysis import analysis_bp
from .chat import chat_bp
from .health import health_bp
from .auth import auth_bp
from .campaign import campaign_bp

__all__ = ['analysis_bp', 'chat_bp', 'health_bp', 'auth_bp', 'campaign_bp']

