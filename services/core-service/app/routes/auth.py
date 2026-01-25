"""
Authentication endpoints for Core Service.
Handles user registration, login, and token management.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import re

from app import db
from models.database import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format."""
    pattern = r'^\+?[1-9]\d{6,14}$'
    return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint.

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword",
        "phone": "+573001234567",
        "first_name": "Juan",
        "last_name": "Perez",
        "campaign_role": "Candidato",
        "candidate_position": "Presidencia"
    }
    """
    try:
        data = request.get_json() or {}

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400

        if not validate_email(email):
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400

        if len(password) < 8:
            return jsonify({
                'success': False,
                'error': 'Password must be at least 8 characters'
            }), 400

        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 400

        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            phone=data.get('phone'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            campaign_role=data.get('campaign_role'),
            candidate_position=data.get('candidate_position'),
            whatsapp_number=data.get('whatsapp_number'),
            whatsapp_opt_in=data.get('whatsapp_opt_in', False)
        )

        db.session.add(user)
        db.session.commit()

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': str(user.id),
                'email': user.email
            }
        }), 201

    except Exception as e:
        logger.error(f"Error in register: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    try:
        data = request.get_json() or {}

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401

        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Account is disabled'
            }), 401

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': str(user.id),
                'email': user.email
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in login: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        return jsonify({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone': user.phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'campaign_role': user.campaign_role,
                'candidate_position': user.candidate_position,
                'whatsapp_number': user.whatsapp_number,
                'whatsapp_opt_in': user.whatsapp_opt_in,
                'roles': user.roles or ['user']
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    try:
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=user_id)

        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200

    except Exception as e:
        logger.error(f"Error in refresh: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
