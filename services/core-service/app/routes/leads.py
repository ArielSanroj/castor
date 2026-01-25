"""
Lead management endpoints for Core Service.
Handles demo requests and lead tracking.
"""
import logging
from flask import Blueprint, request, jsonify
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional

from app import db
from models.database import Lead

logger = logging.getLogger(__name__)

leads_bp = Blueprint('leads', __name__)


class DemoRequest(BaseModel):
    """Pydantic model for demo request."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    interest: str = Field(..., pattern="^(forecast|campanas|medios|dashboard|estratega|comunicaciones|candidato|analista|otro)$")
    location: str = Field(..., min_length=1, max_length=120)
    candidacy_type: Optional[str] = Field(None, pattern="^(congreso|regionales|presidencia)$")


@leads_bp.route('/demo-request', methods=['POST'])
def create_demo_request():
    """
    Create a demo request (lead).

    Request body:
    {
        "first_name": "Juan",
        "last_name": "Perez",
        "email": "juan@example.com",
        "phone": "+573001234567",
        "interest": "forecast",
        "location": "Bogota",
        "candidacy_type": "congreso" (optional)
    }
    """
    try:
        data = request.get_json() or {}

        # Validate request
        try:
            demo_req = DemoRequest(**data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Invalid request data',
                'details': e.errors()
            }), 400

        # Check if lead exists
        existing = Lead.query.filter_by(email=demo_req.email).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 400

        # Create lead
        lead = Lead(
            first_name=demo_req.first_name,
            last_name=demo_req.last_name,
            email=demo_req.email,
            phone=demo_req.phone,
            interest=demo_req.interest,
            location=demo_req.location,
            candidacy_type=demo_req.candidacy_type
        )

        db.session.add(lead)
        db.session.commit()

        logger.info(f"Demo request created: {lead.id} - {lead.email}")

        return jsonify({
            'success': True,
            'lead_id': str(lead.id),
            'message': 'Solicitud de demo recibida exitosamente'
        }), 201

    except Exception as e:
        logger.error(f"Error creating demo request: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@leads_bp.route('/', methods=['GET'])
def get_leads():
    """
    Get all leads (admin only in production).

    Query parameters:
    - status: Filter by status
    - candidacy_type: Filter by candidacy type
    - limit: Max results (default 50)
    - offset: Pagination offset
    """
    try:
        status = request.args.get('status')
        candidacy_type = request.args.get('candidacy_type')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        query = Lead.query

        if status:
            query = query.filter_by(status=status)
        if candidacy_type:
            query = query.filter_by(candidacy_type=candidacy_type)

        total = query.count()
        leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()

        return jsonify({
            'success': True,
            'total': total,
            'leads': [{
                'id': str(lead.id),
                'first_name': lead.first_name,
                'last_name': lead.last_name,
                'email': lead.email,
                'phone': lead.phone,
                'interest': lead.interest,
                'location': lead.location,
                'candidacy_type': lead.candidacy_type,
                'status': lead.status,
                'created_at': lead.created_at.isoformat() if lead.created_at else None
            } for lead in leads]
        }), 200

    except Exception as e:
        logger.error(f"Error getting leads: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@leads_bp.route('/count', methods=['GET'])
def get_leads_count():
    """Get total count of leads with filters."""
    try:
        status = request.args.get('status')
        candidacy_type = request.args.get('candidacy_type')

        query = Lead.query

        if status:
            query = query.filter_by(status=status)
        if candidacy_type:
            query = query.filter_by(candidacy_type=candidacy_type)

        count = query.count()

        return jsonify({
            'success': True,
            'total_leads': count,
            'filters': {
                'status': status,
                'candidacy_type': candidacy_type
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting leads count: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
