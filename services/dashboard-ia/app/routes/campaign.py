"""
Campaign agent endpoints.
Endpoints for vote-winning strategies and signature collection.
"""
import logging
import uuid
from typing import Optional
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from datetime import datetime

from services.campaign_agent import CampaignAgent
from services.database_service import DatabaseService
from services.openai_service import OpenAIService
from services.rag_service import get_rag_service
from utils.validators import validate_location
from utils.rate_limiter import limiter
from app.schemas.campaign import (
    CampaignAnalysisRequest,
    CampaignAnalysisResponse,
    CampaignMetadata,
)
from app.services.analysis_core import AnalysisCorePipeline
from models.schemas import PNDTopicAnalysis, SentimentData

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


def _get_pipeline() -> Optional[AnalysisCorePipeline]:
    from flask import current_app
    return current_app.extensions.get("analysis_core_pipeline")


def _get_openai_service() -> Optional[OpenAIService]:
    from flask import current_app
    return current_app.extensions.get("openai_service")


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
        
        try:
            agent, _ = get_services()
            trending = agent.trending_service.detect_trending_topics(location)
        except Exception as e:
            logger.warning(f"Error getting trending topics: {e}, returning empty list")
            # Return empty list instead of error to allow dashboard to work
            trending = []
        
        return jsonify({
            'success': True,
            'location': location,
            'trending_topics': trending[:limit] if trending else []
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}", exc_info=True)
        return jsonify({
            'success': True,  # Return success with empty list
            'location': request.args.get('location', 'unknown'),
            'trending_topics': []
        }), 200


@campaign_bp.route('/campaign/analyze', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit for expensive operations
@jwt_required(optional=True)
def campaign_analyze_product():
    """
    Product B: full campaign analysis (exec summary + plan + speech).
    """
    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception as e:
        logger.warning(f"Invalid JSON in campaign analyze: {e}")
        return jsonify({"success": False, "error": "Invalid JSON payload"}), 400
    
    try:
        req = CampaignAnalysisRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Validation error in campaign analyze: {e}")
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": e.errors() if hasattr(e, 'errors') else str(e)
        }), 400

    pipeline = _get_pipeline()
    openai_svc = _get_openai_service()

    if not pipeline or not openai_svc:
        return jsonify({
            "success": False,
            "error": "Servicios de análisis no disponibles",
        }), 503

    core_result = pipeline.run_core_pipeline(
        location=req.location,
        topic=req.theme,
        candidate_name=req.candidate_name,
        politician=req.politician,
        max_tweets=req.max_tweets,
        time_window_days=7,
        language=req.language,
    )

    # Adapt new topics to legacy schema expected by existing OpenAI prompts
    legacy_topics = []
    for topic in core_result.topics:
        legacy_topics.append(
            PNDTopicAnalysis(
                topic=topic.topic,
                sentiment=SentimentData(
                    positive=topic.sentiment.positive,
                    negative=topic.sentiment.negative,
                    neutral=topic.sentiment.neutral,
                ),
                tweet_count=topic.tweet_count,
                key_insights=[],
                sample_tweets=[],
            )
        )

    executive_summary = openai_svc.generate_executive_summary(
        location=req.location,
        topic_analyses=legacy_topics,
        candidate_name=req.candidate_name,
    )

    strategic_plan = openai_svc.generate_strategic_plan(
        location=req.location,
        topic_analyses=legacy_topics,
        candidate_name=req.candidate_name,
    )

    speech = openai_svc.generate_speech(
        location=req.location,
        topic_analyses=legacy_topics,
        candidate_name=req.candidate_name or "el candidato",
        trending_topic={"topic": core_result.trending_topic} if core_result.trending_topic else None,
    )

    metadata = CampaignMetadata(
        tweets_analyzed=core_result.tweets_analyzed,
        location=req.location,
        theme=req.theme,
        candidate_name=req.candidate_name,
        politician=req.politician,
        generated_at=datetime.utcnow(),
        trending_topic=core_result.trending_topic,
        raw_query=core_result.raw_query,
    )

    response_model = CampaignAnalysisResponse(
        success=True,
        executive_summary=executive_summary,
        topic_analyses=core_result.topics,
        strategic_plan=strategic_plan,
        speech=speech,
        chart_data=core_result.chart_data,
        metadata=metadata,
    )

    # Index into RAG (best-effort)
    try:
        rag = get_rag_service()
        analysis_payload = {
            "executive_summary": executive_summary.model_dump() if hasattr(executive_summary, "model_dump") else executive_summary,
            "topics": [t.model_dump() if hasattr(t, "model_dump") else t for t in core_result.topics],
            "strategic_plan": strategic_plan.model_dump() if hasattr(strategic_plan, "model_dump") else strategic_plan,
            "speech": speech.model_dump() if hasattr(speech, "model_dump") else speech,
            "metadata": metadata.model_dump() if hasattr(metadata, "model_dump") else metadata,
        }
        rag.index_analysis(
            analysis_id=f"campaign_{uuid.uuid4().hex}",
            analysis_data=analysis_payload,
            metadata={
                "location": metadata.location,
                "candidate": metadata.candidate_name,
                "created_at": metadata.generated_at,
                "topic_name": metadata.theme,
            },
        )
    except Exception as e:
        logger.warning(f"RAG indexing skipped (campaign): {e}")

    return jsonify(response_model.model_dump()), 200


@campaign_bp.route('/campaign/rivals/compare', methods=['POST'])
@limiter.limit("2 per minute")
@jwt_required(optional=True)
def compare_rivals():
    """
    Compare rival candidates using the same Twitter-backed analysis pipeline.

    Request body:
    {
        "location": "Colombia",
        "topic": "Seguridad",
        "candidate_names": ["Paloma Valencia", "Vicky Dávila", ...],
        "days_back": 30,
        "max_tweets": 30
    }
    """
    try:
        payload = request.get_json() or {}
        location = (payload.get("location") or "").strip()
        if not location:
            return jsonify({"success": False, "error": "location is required"}), 400

        candidate_names = payload.get("candidate_names") or []
        if not candidate_names:
            return jsonify({"success": False, "error": "candidate_names is required"}), 400

        topic = payload.get("topic")
        days_back = int(payload.get("days_back") or 30)
        max_tweets = int(payload.get("max_tweets") or 30)

        pipeline = _get_pipeline()
        if not pipeline:
            return jsonify({
                "success": False,
                "error": "Servicios de análisis no disponibles",
            }), 503

        results = []
        for name in candidate_names:
            if not name:
                continue
            try:
                core_result = pipeline.run_core_pipeline(
                    location=location,
                    topic=topic,
                    candidate_name=name,
                    politician=None,
                    max_tweets=max_tweets,
                    time_window_days=days_back,
                    language="es",
                )
                results.append({
                    "candidate_name": name,
                    "tweets_analyzed": core_result.tweets_analyzed,
                    "sentiment_overview": core_result.sentiment_overview.model_dump() if hasattr(core_result.sentiment_overview, "model_dump") else core_result.sentiment_overview,
                    "topics": [t.model_dump() if hasattr(t, "model_dump") else t for t in core_result.topics],
                    "time_window_from": core_result.time_window_from.isoformat() if core_result.time_window_from else None,
                    "time_window_to": core_result.time_window_to.isoformat() if core_result.time_window_to else None,
                })

                # Index into RAG (best-effort)
                try:
                    rag = get_rag_service()
                    rag.index_analysis(
                        analysis_id=f"rival_{uuid.uuid4().hex}",
                        analysis_data={
                            "executive_summary": {
                                "overview": f"Comparación de rival {name} en {location}.",
                                "key_findings": [
                                    f"Tweets analizados: {core_result.tweets_analyzed}",
                                ],
                                "recommendations": []
                            },
                            "topics": [t.model_dump() if hasattr(t, "model_dump") else t for t in core_result.topics],
                            "sentiment_overview": core_result.sentiment_overview.model_dump() if hasattr(core_result.sentiment_overview, "model_dump") else core_result.sentiment_overview,
                            "metadata": {
                                "location": location,
                                "theme": topic,
                                "candidate_name": name,
                                "time_window_from": core_result.time_window_from.isoformat() if core_result.time_window_from else None,
                                "time_window_to": core_result.time_window_to.isoformat() if core_result.time_window_to else None,
                            }
                        },
                        metadata={
                            "location": location,
                            "candidate": name,
                            "topic_name": topic,
                            "created_at": core_result.time_window_to.isoformat() if core_result.time_window_to else None,
                        },
                    )
                except Exception as e:
                    logger.warning(f"RAG indexing skipped (rival compare): {e}")
            except Exception as e:
                logger.warning(f"Rival compare failed for {name}: {e}")

        return jsonify({
            "success": True,
            "location": location,
            "topic": topic,
            "candidates": results
        }), 200
    except Exception as e:
        logger.error(f"Error in rival compare: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Error processing rivals"}), 500
