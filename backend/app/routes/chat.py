"""
Chat endpoint routes.
AI assistant for campaign advice.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from models.schemas import ChatRequest, ChatResponse
from services import OpenAIService

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize service
openai_service = None


def get_openai_service():
    """Lazy initialization of OpenAI service."""
    global openai_service
    if openai_service is None:
        openai_service = OpenAIService()
    return openai_service


@chat_bp.route('/chat', methods=['POST'])
@jwt_required(optional=True)
def chat():
    """
    Chat endpoint for AI campaign assistant.
    
    Request body:
    {
        "message": "¿Cómo puedo mejorar mi campaña?",
        "context": {...},
        "conversation_id": "optional-id"
    }
    
    Returns:
        ChatResponse with AI response
    """
    try:
        req_data = request.get_json() or {}
        
        # Validate request
        try:
            chat_req = ChatRequest(**req_data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Invalid request data',
                'details': str(e)
            }), 400
        
        # Get OpenAI service
        openai_svc = get_openai_service()
        
        # Generate response
        response_text = openai_svc.chat(
            message=chat_req.message,
            context=chat_req.context
        )
        
        # Build response
        response = ChatResponse(
            success=True,
            response=response_text,
            conversation_id=chat_req.conversation_id
        )
        
        return jsonify(response.dict()), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

