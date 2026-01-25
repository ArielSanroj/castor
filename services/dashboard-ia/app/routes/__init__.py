"""Routes package for Dashboard IA Service."""
from app.routes.health import health_bp
from app.routes.media import media_bp
from app.routes.chat import chat_bp
from app.routes.campaign import campaign_bp
from app.routes.campaign_team import campaign_team_bp
from app.routes.forecast import forecast_bp
from app.routes.advisor import advisor_bp

__all__ = [
    'health_bp',
    'media_bp',
    'chat_bp',
    'campaign_bp',
    'campaign_team_bp',
    'forecast_bp',
    'advisor_bp'
]
