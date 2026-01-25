"""
Routes module for CASTOR ELECCIONES API.
"""
from .analysis import analysis_bp
from .chat import chat_bp
from .health import health_bp
from .auth import auth_bp
from .campaign import campaign_bp
from .web import web_bp
from .leads import leads_bp
from .media import media_bp
from .forecast import forecast_bp
from .advisor import advisor_bp
from .electoral import electoral_bp
from .campaign_team import campaign_team_bp
from .review import review_bp
from .ingestion import ingestion_bp
from .incidents import incidents_bp
from .geography import geography_bp

__all__ = [
    'analysis_bp',
    'chat_bp',
    'health_bp',
    'auth_bp',
    'campaign_bp',
    'web_bp',
    'leads_bp',
    'media_bp',
    'forecast_bp',
    'advisor_bp',
    'electoral_bp',
    'campaign_team_bp',
    'review_bp',
    'ingestion_bp',
    'incidents_bp',
    'geography_bp',
]
