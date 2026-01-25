"""Internal endpoints for service-to-service communication."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import decode_token, get_jwt_identity
from jwt.exceptions import InvalidTokenError
import logging

internal_bp = Blueprint('internal', __name__)
logger = logging.getLogger(__name__)


@internal_bp.route('/validate-token', methods=['POST'])
def validate_token():
    """
    Validate JWT token for other microservices.

    Request Body:
        token: JWT access token to validate

    Returns:
        user_id, roles, valid status
    """
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({'valid': False, 'error': 'No token provided'}), 400

    try:
        # Decode and validate the token
        decoded = decode_token(token)
        user_id = decoded.get('sub')

        # Get user info from database
        from models.database import User
        user = User.query.get(user_id)

        if not user:
            return jsonify({'valid': False, 'error': 'User not found'}), 401

        return jsonify({
            'valid': True,
            'user_id': user.id,
            'email': user.email,
            'roles': user.roles if hasattr(user, 'roles') else ['user'],
            'exp': decoded.get('exp')
        })

    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({'valid': False, 'error': str(e)}), 500


@internal_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_info(user_id: int):
    """
    Get user information for internal services.

    This endpoint should only be accessible from internal network.
    """
    try:
        from models.database import User
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': user.id,
            'email': user.email,
            'roles': user.roles if hasattr(user, 'roles') else ['user'],
            'created_at': user.created_at.isoformat() if user.created_at else None
        })

    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return jsonify({'error': str(e)}), 500
