"""
Analysis endpoint routes.
Main endpoint for generating political analysis reports.
"""
import logging
from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
import tweepy
from sqlalchemy.exc import SQLAlchemyError

from models.schemas import AnalysisRequest, AnalysisResponse
from services import TwitterService, SentimentService, OpenAIService, TwilioService
from services.database_service import DatabaseService
from services.trending_service import TrendingService
from services.background_jobs import enqueue_analysis_task, get_job_status
from utils.chart_generator import ChartGenerator
from utils.validators import validate_location, validate_candidate_name
from utils.formatters import format_location
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)

# Thread-safe service initialization using factory pattern
from utils.response_helpers import service_factory


def get_services():
    """Thread-safe lazy initialization of services using factory pattern."""
    twitter_svc = service_factory.get_or_create('twitter', TwitterService)
    sentiment_svc = service_factory.get_or_create('sentiment', SentimentService)
    openai_svc = service_factory.get_or_create('openai', OpenAIService)
    twilio_svc = service_factory.get_or_create('twilio', TwilioService)
    db_svc = service_factory.get_or_create('database', DatabaseService)
    trending_svc = service_factory.get_or_create('trending', TrendingService)

    return twitter_svc, sentiment_svc, openai_svc, twilio_svc, db_svc, trending_svc


def _parse_analysis_request(req_data: dict) -> tuple:
    """Validate and normalize incoming analysis request."""
    try:
        analysis_req = AnalysisRequest(**req_data)
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return None, (jsonify({
            'success': False,
            'error': 'Invalid request data',
            'details': e.errors()
        }), 400)
    
    if not validate_location(analysis_req.location):
        return None, (jsonify({
            'success': False,
            'error': 'Invalid location format'
        }), 400)
    
    if analysis_req.candidate_name and not validate_candidate_name(analysis_req.candidate_name):
        return None, (jsonify({
            'success': False,
            'error': 'Invalid candidate name format'
        }), 400)
    
    return analysis_req, None


def _get_initialized_services():
    """Return initialized services or a JSON error response if config is missing."""
    try:
        return get_services(), None
    except ValueError as e:
        logger.error(f"Service configuration error: {e}")
        return None, (jsonify({
            'success': False,
            'error': 'Service configuration error',
            'details': str(e)
        }), 503)


@analysis_bp.route('/analyze', methods=['POST'])
@limiter.limit("5 per minute")  # Stricter limit for expensive operations
@jwt_required(optional=True)  # Optional auth for MVP
def analyze():
    """
    Main analysis endpoint.
    
    Request body:
    {
        "location": "Bogotá",
        "theme": "Seguridad",
        "candidate_name": "Juan Pérez",
        "politician": "@juanperez",
        "max_tweets": 100
    }
    
    Returns:
        AnalysisResponse with full report
    """
    try:
        # Validate request first to avoid hitting external services for bad input
        analysis_req, error_response = _parse_analysis_request(request.get_json() or {})
        if error_response:
            return error_response
        
        services, error_response = _get_initialized_services()
        if error_response:
            return error_response
        twitter_svc, sentiment_svc, openai_svc, twilio_svc, db_svc, trending_svc = services
        
        logger.info(f"Starting analysis for {analysis_req.location}, theme: {analysis_req.theme}")
        
        # Step 0: Detect trending topics (what's hot RIGHT NOW)
        trending_topic = trending_svc.get_trending_for_speech(
            location=analysis_req.location,
            candidate_name=analysis_req.candidate_name or "el candidato"
        )
        
        # Step 1: Search tweets
        if analysis_req.theme.lower() in ['todos los temas', 'todos']:
            # Search for all PND topics
            all_tweets = []
            topics_to_analyze = ['Seguridad', 'Educación', 'Salud', 'Economía y Empleo', 'Infraestructura']
            
            for topic in topics_to_analyze:
                tweets = twitter_svc.search_by_pnd_topic(
                    topic=topic,
                    location=format_location(analysis_req.location),
                    candidate_name=analysis_req.candidate_name,
                    politician=analysis_req.politician,
                    max_results=analysis_req.max_tweets // len(topics_to_analyze)
                )
                all_tweets.extend(tweets)
        else:
            all_tweets = twitter_svc.search_by_pnd_topic(
                topic=analysis_req.theme,
                location=format_location(analysis_req.location),
                candidate_name=analysis_req.candidate_name,
                politician=analysis_req.politician,
                max_results=analysis_req.max_tweets
            )
        
        if not all_tweets:
            logger.warning(f"No tweets found for {analysis_req.location}")
            return jsonify({
                'success': False,
                'error': 'No tweets found for the specified location and theme'
            }), 404
        
        logger.info(f"Found {len(all_tweets)} tweets")
        
        # Step 2: Analyze sentiment
        tweets_with_sentiment = sentiment_svc.analyze_tweets(all_tweets)
        
        # Step 3: Classify by PND topics
        topic_analyses = _classify_tweets_by_topic(tweets_with_sentiment, analysis_req.theme)
        
        # Step 4: Generate content with OpenAI
        executive_summary = openai_svc.generate_executive_summary(
            location=analysis_req.location,
            topic_analyses=topic_analyses,
            candidate_name=analysis_req.candidate_name
        )
        
        strategic_plan = openai_svc.generate_strategic_plan(
            location=analysis_req.location,
            topic_analyses=topic_analyses,
            candidate_name=analysis_req.candidate_name
        )
        
        speech = openai_svc.generate_speech(
            location=analysis_req.location,
            topic_analyses=topic_analyses,
            candidate_name=analysis_req.candidate_name or "el candidato",
            trending_topic=trending_topic  # Pass trending topic to align speech
        )
        
        # Step 5: Generate chart
        chart_data = ChartGenerator.generate_sentiment_chart(topic_analyses)
        
        # Step 6: Build response
        response = AnalysisResponse(
            success=True,
            executive_summary=executive_summary,
            topic_analyses=topic_analyses,
            strategic_plan=strategic_plan,
            speech=speech,
            chart_data=chart_data,
            metadata={
                'tweets_analyzed': len(tweets_with_sentiment),
                'location': analysis_req.location,
                'theme': analysis_req.theme
            }
        )
        
        # Step 7: Save to database (if user authenticated)
        analysis_id = None
        try:
            user_id = get_jwt_identity()
            if user_id and db_svc:
                saved = db_svc.save_analysis(
                    user_id=str(user_id),
                    location=analysis_req.location,
                    theme=analysis_req.theme,
                    candidate_name=analysis_req.candidate_name,
                    analysis_data=response.dict()
                )
                if saved:
                    analysis_id = saved.get('id') if isinstance(saved, dict) else getattr(saved, 'id', None)
        except Exception as e:
            logger.warning(f"Could not save analysis to database: {e}")

        # Step 7b: Index to RAG for AI assistant (async, non-blocking)
        try:
            from services.rag_service import get_rag_service
            rag = get_rag_service()
            rag.index_analysis(
                analysis_id=analysis_id or f"analysis_{analysis_req.location}_{analysis_req.theme}",
                analysis_data=response.dict(),
                metadata={
                    "location": analysis_req.location,
                    "theme": analysis_req.theme,
                    "candidate": analysis_req.candidate_name
                }
            )
            logger.info(f"Indexed analysis to RAG for {analysis_req.location}")
        except Exception as e:
            logger.warning(f"Could not index to RAG (non-critical): {e}")
        
        # Step 8: Send WhatsApp if requested and user opted in
        try:
            user_id = get_jwt_identity()
            if user_id and db_svc:
                user = db_svc.get_user(str(user_id))
                if user and user.whatsapp_opt_in and user.whatsapp_number:
                    whatsapp_result = twilio_svc.send_whatsapp_report(
                        phone_number=user.whatsapp_number,
                        recipient_name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
                        candidate_name=analysis_req.candidate_name or "el candidato",
                        speech=speech,
                        strategic_plan=strategic_plan,
                        location=analysis_req.location
                    )
                    response.metadata['whatsapp_sent'] = whatsapp_result.get('success', False)
        except Exception as e:
            logger.warning(f"Could not send WhatsApp: {e}")
        
        # Add trending topic info to response
        if trending_topic and isinstance(trending_topic, dict):
            response.metadata['trending_topic'] = trending_topic.get('topic')
            response.metadata['trending_engagement'] = trending_topic.get('engagement_score', 0)
        
        return jsonify(response.dict()), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error in analyze endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Invalid request data',
            'details': e.errors() if hasattr(e, 'errors') else [{'msg': str(e)}]
        }), 400
    except ValueError as e:
        logger.error(f"Configuration error in analyze endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Service configuration error',
            'message': str(e)
        }), 503
    except tweepy.TooManyRequests:
        logger.warning("Twitter rate limit exceeded in analyze endpoint")
        return jsonify({
            'success': False,
            'error': 'Twitter API rate limit exceeded. Please try again later.'
        }), 429
    except SQLAlchemyError as e:
        logger.error(f"Database error in analyze endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Database error'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@analysis_bp.route('/analyze/async', methods=['POST'])
@limiter.limit("3 per minute")
@jwt_required(optional=True)
def analyze_async():
    """Kick off analysis as a background job."""
    try:
        analysis_req, error_response = _parse_analysis_request(request.get_json() or {})
        if error_response:
            return error_response
        
        job_id = enqueue_analysis_task(
            location=analysis_req.location,
            theme=analysis_req.theme,
            candidate_name=analysis_req.candidate_name,
            politician=analysis_req.politician,
            max_tweets=analysis_req.max_tweets,
            user_id=get_jwt_identity()
        )
        
        if not job_id:
            return jsonify({
                'success': False,
                'error': 'Background queue unavailable'
            }), 503
        
        status_url = url_for('analysis.get_analysis_status', job_id=job_id, _external=False)
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status_url': status_url
        }), 202
    except Exception as e:
        logger.error(f"Error enqueueing async analysis: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@analysis_bp.route('/analyze/status/<job_id>', methods=['GET'])
def get_analysis_status(job_id):
    """Return status of an async analysis job."""
    try:
        status = get_job_status(job_id)
        if not status:
            return jsonify({
                'success': False,
                'error': 'Job not found or background jobs disabled'
            }), 404
        
        return jsonify({
            'success': True,
            **status
        }), 200
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


def _classify_tweets_by_topic(tweets: list, theme: str) -> list:
    """
    Classify tweets by PND topics.
    
    Args:
        tweets: List of tweets with sentiment
        theme: Selected theme
        
    Returns:
        List of PNDTopicAnalysis objects
    """
    from models.schemas import PNDTopicAnalysis, SentimentData
    from services.sentiment_service import SentimentService
    
    sentiment_svc = SentimentService()
    
    # If "Todos los temas", analyze all topics
    if theme.lower() in ['todos los temas', 'todos']:
        topics = ['Seguridad', 'Educación', 'Salud', 'Economía y Empleo', 'Infraestructura']
    else:
        topics = [theme]
    
    topic_analyses = []
    
    for topic in topics:
        # Filter tweets by topic keywords
        topic_keywords = _get_topic_keywords(topic)
        topic_tweets = [
            t for t in tweets
            if any(keyword.lower() in t.get('text', '').lower() for keyword in topic_keywords.split(' OR '))
        ]
        
        if not topic_tweets:
            # Create empty analysis
            topic_analyses.append(PNDTopicAnalysis(
                topic=topic,
                sentiment=SentimentData(positive=0.33, negative=0.33, neutral=0.34),
                tweet_count=0,
                key_insights=[],
                sample_tweets=[]
            ))
            continue
        
        # Aggregate sentiment
        sentiments = [
            SentimentData(**t['sentiment'])
            for t in topic_tweets
            if 'sentiment' in t
        ]
        
        if sentiments:
            aggregated = sentiment_svc.aggregate_sentiment(sentiments)
        else:
            aggregated = SentimentData(positive=0.33, negative=0.33, neutral=0.34)
        
        # Extract key insights (simple: most retweeted/liked)
        sorted_tweets = sorted(
            topic_tweets,
            key=lambda x: x.get('public_metrics', {}).get('retweet_count', 0) +
                         x.get('public_metrics', {}).get('like_count', 0),
            reverse=True
        )
        
        sample_tweets = [t['text'][:200] for t in sorted_tweets[:5]]
        key_insights = [
            f"Tema {topic} mencionado en {len(topic_tweets)} tweets",
            f"Sentimiento predominante: {aggregated.get_dominant_sentiment().value}"
        ]
        
        topic_analyses.append(PNDTopicAnalysis(
            topic=topic,
            sentiment=aggregated,
            tweet_count=len(topic_tweets),
            key_insights=key_insights,
            sample_tweets=sample_tweets
        ))
    
    return topic_analyses


def _get_topic_keywords(topic: str) -> str:
    """Get keywords for topic classification."""
    keywords_map = {
        'Seguridad': 'seguridad OR delincuencia OR crimen OR policía',
        'Educación': 'educación OR colegios OR universidad OR estudiantes',
        'Salud': 'salud OR hospitales OR médicos OR EPS',
        'Economía y Empleo': 'economía OR empleo OR trabajo OR desempleo',
        'Infraestructura': 'infraestructura OR vías OR carreteras OR transporte'
    }
    return keywords_map.get(topic, topic)
