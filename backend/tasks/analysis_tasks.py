"""
Background tasks for analysis operations.
These tasks run asynchronously to avoid blocking the API.
"""
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from typing import Optional, Dict, Any
from services.twitter_service import TwitterService
from services.sentiment_service import SentimentService
from services.openai_service import OpenAIService
from services.database_service import DatabaseService
from services.trending_service import TrendingService
from utils.chart_generator import ChartGenerator
from utils.formatters import format_location
from models.schemas import AnalysisResponse, PNDTopicAnalysis, SentimentData

logger = logging.getLogger(__name__)


def run_analysis_task(
    location: str,
    theme: str,
    candidate_name: Optional[str] = None,
    politician: Optional[str] = None,
    max_tweets: int = 100,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run full analysis task in background.
    
    This function runs the complete analysis pipeline:
    1. Detect trending topics
    2. Search tweets
    3. Analyze sentiment
    4. Classify by PND topics
    5. Generate content with OpenAI
    6. Generate charts
    7. Save to database
    
    Args:
        location: Location to analyze
        theme: PND theme
        candidate_name: Optional candidate name
        politician: Optional politician handle
        max_tweets: Maximum tweets
        user_id: Optional user ID
        
    Returns:
        Analysis result dictionary
    """
    try:
        logger.info(f"Starting background analysis for {location}, theme: {theme}")
        
        # Initialize services
        twitter_svc = TwitterService()
        sentiment_svc = SentimentService()
        openai_svc = OpenAIService()
        trending_svc = TrendingService()
        db_svc = DatabaseService()
        
        # Step 0: Detect trending topics
        trending_topic = trending_svc.get_trending_for_speech(
            location=location,
            candidate_name=candidate_name or "el candidato"
        )
        
        # Step 1: Search tweets
        if theme.lower() in ['todos los temas', 'todos']:
            all_tweets = []
            topics_to_analyze = ['Seguridad', 'Educación', 'Salud', 'Economía y Empleo', 'Infraestructura']
            
            for topic in topics_to_analyze:
                tweets = twitter_svc.search_by_pnd_topic(
                    topic=topic,
                    location=format_location(location),
                    candidate_name=candidate_name,
                    politician=politician,
                    max_results=max_tweets // len(topics_to_analyze)
                )
                all_tweets.extend(tweets)
        else:
            all_tweets = twitter_svc.search_by_pnd_topic(
                topic=theme,
                location=format_location(location),
                candidate_name=candidate_name,
                politician=politician,
                max_results=max_tweets
            )
        
        if not all_tweets:
            return {
                'success': False,
                'error': 'No tweets found for the specified location and theme'
            }
        
        logger.info(f"Found {len(all_tweets)} tweets")
        
        # Step 2: Analyze sentiment
        tweets_with_sentiment = sentiment_svc.analyze_tweets(all_tweets)
        
        # Step 3: Classify by PND topics
        topic_analyses = _classify_tweets_by_topic(tweets_with_sentiment, theme)
        
        # Step 4: Generate content with OpenAI
        executive_summary = openai_svc.generate_executive_summary(
            location=location,
            topic_analyses=topic_analyses,
            candidate_name=candidate_name
        )
        
        strategic_plan = openai_svc.generate_strategic_plan(
            location=location,
            topic_analyses=topic_analyses,
            candidate_name=candidate_name
        )
        
        speech = openai_svc.generate_speech(
            location=location,
            topic_analyses=topic_analyses,
            candidate_name=candidate_name or "el candidato",
            trending_topic=trending_topic
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
                'location': location,
                'theme': theme
            }
        )
        
        # Step 7: Save to database (if user authenticated)
        if user_id:
            try:
                db_svc.save_analysis(
                    user_id=str(user_id),
                    location=location,
                    theme=theme,
                    candidate_name=candidate_name,
                    analysis_data=response.dict()
                )
            except Exception as e:
                logger.warning(f"Could not save analysis to database: {e}")
        
        # Add trending topic info
        if trending_topic:
            response.metadata['trending_topic'] = trending_topic.get('topic')
            response.metadata['trending_engagement'] = trending_topic.get('engagement_score', 0)
        
        logger.info(f"Analysis completed successfully for {location}")
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in background analysis task: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def _classify_tweets_by_topic(tweets: list, theme: str) -> list:
    """Classify tweets by PND topics (helper function)."""
    from services.sentiment_service import SentimentService
    
    sentiment_svc = SentimentService()
    
    if theme.lower() in ['todos los temas', 'todos']:
        topics = ['Seguridad', 'Educación', 'Salud', 'Economía y Empleo', 'Infraestructura']
    else:
        topics = [theme]
    
    topic_analyses = []
    
    for topic in topics:
        topic_keywords = _get_topic_keywords(topic)
        topic_tweets = [
            t for t in tweets
            if any(keyword.lower() in t.get('text', '').lower() for keyword in topic_keywords.split(' OR '))
        ]
        
        if not topic_tweets:
            topic_analyses.append(PNDTopicAnalysis(
                topic=topic,
                sentiment=SentimentData(positive=0.33, negative=0.33, neutral=0.34),
                tweet_count=0,
                key_insights=[],
                sample_tweets=[]
            ))
            continue
        
        sentiments = [
            SentimentData(**t['sentiment'])
            for t in topic_tweets
            if 'sentiment' in t
        ]
        
        if sentiments:
            aggregated = sentiment_svc.aggregate_sentiment(sentiments)
        else:
            aggregated = SentimentData(positive=0.33, negative=0.33, neutral=0.34)
        
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

