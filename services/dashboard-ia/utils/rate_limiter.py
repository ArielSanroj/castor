"""
Rate limiter utility using Flask-Limiter.
Provides rate limiting decorators for API endpoints.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize the limiter - will be configured when Flask app is created
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


def init_limiter(app):
    """Initialize rate limiter with Flask app."""
    limiter.init_app(app)
    return limiter


def get_limiter():
    """Get the rate limiter instance."""
    return limiter
