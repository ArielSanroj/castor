"""
API v1 User management endpoints.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from models.database import User

logger = logging.getLogger(__name__)

users_v1_bp = Blueprint('users_v1', __name__, url_prefix='/users')


def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, status_code: int = 400):
    return jsonify({"ok": False, "error": error}), status_code


@users_v1_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    GET /api/v1/users/me

    Get current user profile.
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return error_response("User not found", 404)

        return success_response({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "campaign_role": user.campaign_role,
            "candidate_position": user.candidate_position,
            "roles": user.roles or ["user"],
            "created_at": user.created_at.isoformat() if user.created_at else None
        })

    except Exception as e:
        logger.error(f"Get user error: {e}")
        return error_response("Internal server error", 500)


@users_v1_bp.route('/me', methods=['PATCH'])
@jwt_required()
def update_current_user():
    """
    PATCH /api/v1/users/me

    Update current user profile.

    Request:
        {
            "first_name": "Juan",
            "last_name": "Perez",
            "phone": "+573001234567"
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return error_response("User not found", 404)

        data = request.get_json() or {}

        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'phone', 'campaign_role',
                          'candidate_position', 'whatsapp_number', 'whatsapp_opt_in']

        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        db.session.commit()

        return success_response({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "updated": True
        })

    except Exception as e:
        logger.error(f"Update user error: {e}")
        db.session.rollback()
        return error_response("Internal server error", 500)
