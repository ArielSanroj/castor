"""
Authentication endpoints.
Handles user registration and login via database service.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from services.database_service import DatabaseService
from utils.validators import validate_email, validate_phone_number

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Initialize service
db_service = None


def get_db_service():
    """Lazy initialization of database service."""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    """
    User registration endpoint.
    
    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword",
        "phone": "+573001234567",
        "first_name": "Juan",
        "last_name": "Pérez",
        "campaign_role": "Candidato",
        "candidate_position": "Presidencia",
        "whatsapp_number": "+573001234567",
        "whatsapp_opt_in": true
    }
    
    Returns:
        Access token and user data
    """
    try:
        req_data = request.get_json() or {}
        
        # Validate required fields
        email = req_data.get('email')
        password = req_data.get('password')
        
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
        
        # Validate WhatsApp number if provided
        whatsapp_number = req_data.get('whatsapp_number')
        if whatsapp_number and not validate_phone_number(whatsapp_number):
            return jsonify({
                'success': False,
                'error': 'Invalid WhatsApp number format'
            }), 400
        
        # Get database service
        db_svc = get_db_service()
        
        # Create user
        user = db_svc.create_user(
            email=email,
            password=password,
            phone=req_data.get('phone'),
            first_name=req_data.get('first_name'),
            last_name=req_data.get('last_name'),
            campaign_role=req_data.get('campaign_role'),
            candidate_position=req_data.get('candidate_position'),
            whatsapp_number=whatsapp_number,
            whatsapp_opt_in=req_data.get('whatsapp_opt_in', False)
        )
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Failed to create user (email may already exist)'
            }), 400
        
        # Create JWT token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': {
                'id': str(user.id),
                'email': user.email
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error in register endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """
    User login endpoint.
    
    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    
    Returns:
        Access token and user data
    """
    try:
        req_data = request.get_json() or {}
        
        email = req_data.get('email')
        password = req_data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Get database service
        db_svc = get_db_service()
        
        # Authenticate user
        user = db_svc.authenticate_user(email, password)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
        
        # Create JWT token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': {
                'id': str(user.id),
                'email': user.email
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}", exc_info=True)
        # Don't expose internal error details to client
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@auth_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user.
    
    Returns:
        User profile data
    """
    try:
        user_id = get_jwt_identity()
        db_svc = get_db_service()
        
        user = db_svc.get_user(str(user_id))
        
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
                'whatsapp_opt_in': user.whatsapp_opt_in
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

