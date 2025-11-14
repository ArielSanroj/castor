"""
Analysis endpoint routes.
Main endpoint for generating political analysis reports.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

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

# Initialize services (singleton pattern)
twitter_service = None
sentiment_service = None
openai_service = None
twilio_service = None
db_service = None
trending_service = None


def get_services():
    """Lazy initialization of services."""
    global twitter_service, sentiment_service, openai_service, twilio_service, db_service, trending_service
    
    if twitter_service is None:
        twitter_service = TwitterService()
    if sentiment_service is None:
        sentiment_service = SentimentService()
    if openai_service is None:
        openai_service = OpenAIService()
    if twilio_service is None:
        twilio_service = TwilioService()
    if db_service is None:
        db_service = DatabaseService()
    if trending_service is None:
        trending_service = TrendingService()
    
    return twitter_service, sentiment_service, openai_service, twilio_service, db_service, trending_service


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
        # Get services
        twitter_svc, sentiment_svc, openai_svc, twilio_svc, db_svc, trending_svc = get_services()
        
        # Validate request
        try:
            req_data = request.get_json() or {}
            analysis_req = AnalysisRequest(**req_data)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({
                'success': False,
                'error': 'Invalid request data',
                'details': e.errors()
            }), 400
        
        # Additional validations
        if not validate_location(analysis_req.location):
            return jsonify({
                'success': False,
                'error': 'Invalid location format'
            }), 400
        
        if analysis_req.candidate_name and not validate_candidate_name(analysis_req.candidate_name):
            return jsonify({
                'success': False,
                'error': 'Invalid candidate name format'
            }), 400
        
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
        try:
            user_id = get_jwt_identity()
            if user_id and db_svc:
                db_svc.save_analysis(
                    user_id=str(user_id),
                    location=analysis_req.location,
                    theme=analysis_req.theme,
                    candidate_name=analysis_req.candidate_name,
                    analysis_data=response.dict()
                )
        except Exception as e:
            logger.warning(f"Could not save analysis to database: {e}")
        
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
        if trending_topic:
            response.metadata['trending_topic'] = trending_topic.get('topic')
            response.metadata['trending_engagement'] = trending_topic.get('engagement_score', 0)
        
        return jsonify(response.dict()), 200
        
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
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

