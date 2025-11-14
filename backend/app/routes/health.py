"""
Health check endpoint.
"""
from flask import Blueprint, jsonify
from datetime import datetime

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

