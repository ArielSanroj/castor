"""
Lead management endpoints.
Handles demo requests and lead tracking.
"""
import logging
from flask import Blueprint, request, jsonify
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

leads_bp = Blueprint('leads', __name__)

# Initialize service
db_service = None


def get_db_service():
    """Lazy initialization of database service."""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service


class DemoRequest(BaseModel):
    """Pydantic model for demo request."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    candidacy_type: str = Field(..., pattern="^(congreso|regionales|presidencia)$")


@leads_bp.route('/demo-request', methods=['POST'])
def create_demo_request():
    """
    Create a demo request (lead).
    
    Request body:
    {
        "first_name": "Juan",
        "last_name": "Pérez",
        "email": "juan@example.com",
        "phone": "+573001234567",
        "candidacy_type": "congreso"
    }
    
    Returns:
        Success confirmation with lead ID
    """
    try:
        req_data = request.get_json() or {}
        
        # Validate request
        try:
            demo_req = DemoRequest(**req_data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Invalid request data',
                'details': e.errors()
            }), 400
        
        # Get database service
        db = get_db_service()
        
        # Create lead
        lead = db.create_lead(
            first_name=demo_req.first_name,
            last_name=demo_req.last_name,
            email=demo_req.email,
            phone=demo_req.phone,
            candidacy_type=demo_req.candidacy_type
        )
        
        if not lead:
            return jsonify({
                'success': False,
                'error': 'Failed to create lead (may already exist)'
            }), 400
        
        logger.info(f"Demo request created: {lead.id} - {lead.email}")
        
        return jsonify({
            'success': True,
            'lead_id': str(lead.id),
            'message': 'Solicitud de demo recibida exitosamente'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating demo request: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@leads_bp.route('/leads/count', methods=['GET'])
def get_leads_count():
    """
    Get total count of leads.
    
    Query parameters:
    - status: Filter by status (optional)
    - candidacy_type: Filter by candidacy type (optional)
    
    Returns:
        Total count of leads
    """
    try:
        db = get_db_service()
        
        status = request.args.get('status')
        candidacy_type = request.args.get('candidacy_type')
        
        count = db.count_leads(status=status, candidacy_type=candidacy_type)
        
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
            'error': 'Internal server error',
            'message': str(e)
        }), 500

