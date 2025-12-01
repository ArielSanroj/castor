"""
Health check endpoint.
"""
from flask import Blueprint, jsonify
from datetime import datetime
from utils.twitter_rate_tracker import get_twitter_usage_stats

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    
    Returns:
        Status and timestamp
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'CASTOR ELECCIONES API',
        'version': '1.0.0'
    }), 200


@health_bp.route('/twitter-usage', methods=['GET'])
def twitter_usage():
    """Get Twitter API usage statistics (Free tier monitoring)."""
    try:
        stats = get_twitter_usage_stats()
        return jsonify({
            'success': True,
            'plan': 'Free Tier (100 posts/month)',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

