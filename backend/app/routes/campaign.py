"""
Campaign agent endpoints.
Endpoints for vote-winning strategies and signature collection.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from services.campaign_agent import CampaignAgent
from services.database_service import DatabaseService
from utils.validators import validate_location

logger = logging.getLogger(__name__)

campaign_bp = Blueprint('campaign', __name__)

# Initialize services
campaign_agent = None
db_service = None


def get_services():
    """Lazy initialization of services."""
    global campaign_agent, db_service
    if campaign_agent is None:
        campaign_agent = CampaignAgent()
    if db_service is None:
        db_service = DatabaseService()
    return campaign_agent, db_service


@campaign_bp.route('/campaign/analyze-votes', methods=['POST'])
@jwt_required(optional=True)
def analyze_what_wins_votes():
    """
    Analyze what strategies win votes in a location.
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez"
    }
    
    Returns:
        Analysis with strategies to win votes
    """
    try:
        req_data = request.get_json() or {}
        location = req_data.get('location')
        candidate_name = req_data.get('candidate_name', 'el candidato')
        
        if not location:
            return jsonify({
                'success': False,
                'error': 'Location is required'
            }), 400
        
        if not validate_location(location):
            return jsonify({
                'success': False,
                'error': 'Invalid location format'
            }), 400
        
        user_id = get_jwt_identity() or 'anonymous'
        
        # Get campaign agent
        agent, _ = get_services()
        
        # Analyze what wins votes
        analysis = agent.analyze_what_wins_votes(
            location=location,
            user_id=str(user_id),
            candidate_name=candidate_name
        )
        
        # Save strategies to database if user is authenticated
        if user_id != 'anonymous':
            for strategy in analysis.get('strategies', []):
                strategy_data = {
                    'user_id': user_id,
                    'location': location,
                    'target_demographic': strategy.get('target_demographic', 'General'),
                    'strategy_name': strategy.get('strategy_name'),
                    'strategy_description': strategy.get('description'),
                    'key_messages': strategy.get('key_messages', []),
                    'channels': strategy.get('channels', []),
                    'timing': strategy.get('timing'),
                    'predicted_votes': strategy.get('predicted_votes', 0),
                    'confidence_score': strategy.get('confidence_score', 0.0),
                    'risk_level': strategy.get('risk_level', 'medio'),
                    'based_on_trending_topics': strategy.get('based_on_trending_topics', []),
                    'sentiment_alignment': strategy.get('sentiment_alignment', 0.0)
                }
                db_service.save_vote_strategy(strategy_data)
        
        return jsonify({
            'success': True,
            **analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error in analyze_what_wins_votes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@campaign_bp.route('/campaign/signatures/collect', methods=['POST'])
@jwt_required(optional=True)
def collect_signature():
    """
    Collect a signature for a campaign.
    
    Request body:
    {
        "campaign_id": "campaign-123",
        "signer_name": "María García",
        "signer_email": "maria@example.com",
        "signer_phone": "+573001234567",
        "signer_id_number": "1234567890",
        "location": "Bogotá"
    }
    
    Returns:
        Signature confirmation
    """
    try:
        req_data = request.get_json() or {}
        
        campaign_id = req_data.get('campaign_id')
        signer_name = req_data.get('signer_name')
        signer_email = req_data.get('signer_email')
        
        if not campaign_id or not signer_name or not signer_email:
            return jsonify({
                'success': False,
                'error': 'campaign_id, signer_name, and signer_email are required'
            }), 400
        
        user_id = get_jwt_identity() or 'anonymous'
        
        # Get IP address and user agent
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Add signature
        _, db = get_services()
        signature_id = db.add_signature(
            user_id=str(user_id),
            campaign_id=campaign_id,
            signer_name=signer_name,
            signer_email=signer_email,
            signer_phone=req_data.get('signer_phone'),
            signer_id_number=req_data.get('signer_id_number'),
            location=req_data.get('location'),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not signature_id:
            return jsonify({
                'success': False,
                'error': 'Failed to add signature (may already exist)'
            }), 400
        
        # Get current count
        current_count = db.get_campaign_signatures(campaign_id)
        
        return jsonify({
            'success': True,
            'signature_id': signature_id,
            'current_signatures': current_count,
            'message': 'Signature collected successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error collecting signature: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@campaign_bp.route('/campaign/signatures/<campaign_id>/count', methods=['GET'])
def get_signature_count(campaign_id):
    """
    Get signature count for a campaign.
    
    Returns:
        Signature count
    """
    try:
        _, db = get_services()
        count = db.get_campaign_signatures(campaign_id)
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'signature_count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting signature count: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@campaign_bp.route('/campaign/signatures/strategy', methods=['POST'])
@jwt_required(optional=True)
def get_signature_strategy():
    """
    Get strategy for collecting signatures.
    
    Request body:
    {
        "campaign_id": "campaign-123",
        "location": "Bogotá",
        "target_signatures": 1000
    }
    
    Returns:
        Strategy for signature collection
    """
    try:
        req_data = request.get_json() or {}
        
        campaign_id = req_data.get('campaign_id')
        location = req_data.get('location')
        target_signatures = req_data.get('target_signatures', 1000)
        
        if not campaign_id or not location:
            return jsonify({
                'success': False,
                'error': 'campaign_id and location are required'
            }), 400
        
        agent, _ = get_services()
        
        strategy = agent.generate_signature_collection_strategy(
            campaign_id=campaign_id,
            location=location,
            target_signatures=target_signatures
        )
        
        return jsonify({
            'success': True,
            **strategy
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting signature strategy: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@campaign_bp.route('/campaign/trending', methods=['GET'])
def get_trending_topics():
    """
    Get trending topics for a location.
    
    Query params:
        location: Location to analyze
        limit: Number of topics to return (default: 10)
    
    Returns:
        List of trending topics
    """
    try:
        location = request.args.get('location')
        limit = int(request.args.get('limit', 10))
        
        if not location:
            return jsonify({
                'success': False,
                'error': 'location query parameter is required'
            }), 400
        
        agent, _ = get_services()
        
        trending = agent.trending_service.detect_trending_topics(location)
        
        return jsonify({
            'success': True,
            'location': location,
            'trending_topics': trending[:limit]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

