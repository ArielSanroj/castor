"""
API v1 Authentication endpoints.
Versioned endpoints with standardized response format.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional

from app import db
from models.database import User

logger = logging.getLogger(__name__)

auth_v1_bp = Blueprint('auth_v1', __name__, url_prefix='/auth')


# ============================================================================
# Pydantic Schemas (Request/Response contracts)
# ============================================================================

class RegisterRequest(BaseModel):
    """Registration request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list = ["user"]


# ============================================================================
# Standardized Response Helpers
# ============================================================================

def success_response(data: dict, status_code: int = 200):
    """Create standardized success response."""
    return jsonify({
        "ok": True,
        "data": data
    }), status_code


def error_response(error: str, details: Optional[dict] = None, status_code: int = 400):
    """Create standardized error response."""
    response = {
        "ok": False,
        "error": error
    }
    if details:
        response["details"] = details
    return jsonify(response), status_code


# ============================================================================
# Endpoints
# ============================================================================

@auth_v1_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/v1/auth/register

    Register a new user.

    Request:
        {
            "email": "user@example.com",
            "password": "securepassword",
            "first_name": "Juan",
            "last_name": "Perez"
        }

    Response:
        {
            "ok": true,
            "data": {
                "user": { "id": "...", "email": "..." },
                "tokens": { "access_token": "...", "refresh_token": "..." }
            }
        }
    """
    try:
        # Validate request
        try:
            req = RegisterRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", {"fields": e.errors()})

        # Check if user exists
        if User.query.filter_by(email=req.email).first():
            return error_response("Email already registered", status_code=409)

        # Create user
        user = User(
            email=req.email,
            password_hash=generate_password_hash(req.password),
            first_name=req.first_name,
            last_name=req.last_name,
            phone=req.phone
        )

        db.session.add(user)
        db.session.commit()

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return success_response({
            "user": {
                "id": str(user.id),
                "email": user.email
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
        }, status_code=201)

    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        db.session.rollback()
        return error_response("Internal server error", status_code=500)


@auth_v1_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/v1/auth/login

    Authenticate user and return tokens.

    Request:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }

    Response:
        {
            "ok": true,
            "data": {
                "user": { "id": "...", "email": "..." },
                "tokens": { "access_token": "...", "refresh_token": "..." }
            }
        }
    """
    try:
        # Validate request
        try:
            req = LoginRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", {"fields": e.errors()})

        # Find user
        user = User.query.filter_by(email=req.email).first()

        if not user or not check_password_hash(user.password_hash, req.password):
            return error_response("Invalid credentials", status_code=401)

        if not user.is_active:
            return error_response("Account is disabled", status_code=403)

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return success_response({
            "user": {
                "id": str(user.id),
                "email": user.email
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
        })

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@auth_v1_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """
    GET /api/v1/auth/me

    Get current authenticated user.

    Response:
        {
            "ok": true,
            "data": {
                "user": { "id": "...", "email": "...", "roles": [...] }
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return error_response("User not found", status_code=404)

        return success_response({
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "roles": user.roles or ["user"]
            }
        })

    except Exception as e:
        logger.error(f"Get user error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@auth_v1_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    POST /api/v1/auth/refresh

    Refresh access token using refresh token.

    Response:
        {
            "ok": true,
            "data": {
                "access_token": "...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=user_id)

        return success_response({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600
        })

    except Exception as e:
        logger.error(f"Refresh error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)
