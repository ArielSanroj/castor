"""
Background tasks for trending topic detection.
"""
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from services.trending_service import TrendingService

logger = logging.getLogger(__name__)


def detect_trending_topics_task(location: str) -> dict:
    """
    Detect trending topics in background.
    
    Args:
        location: Location to analyze
        
    Returns:
        Dictionary with trending topics
    """
    try:
        logger.info(f"Detecting trending topics for {location}")
        trending_svc = TrendingService()
        topics = trending_svc.detect_trending_topics(location)
        
        return {
            'success': True,
            'location': location,
            'topics': topics
        }
    except Exception as e:
        logger.error(f"Error detecting trending topics: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

