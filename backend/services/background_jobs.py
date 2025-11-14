"""
Background job system using RQ (Redis Queue).
Handles long-running tasks asynchronously.
"""
import logging
from typing import Dict, Any, Optional
from rq import Queue, Connection, Worker
from rq.job import Job
import redis
from config import Config

logger = logging.getLogger(__name__)

# Redis connection for RQ
redis_conn = None
task_queue = None


def init_background_jobs():
    """Initialize background job system."""
    global redis_conn, task_queue
    
    redis_url = Config.REDIS_URL or 'redis://localhost:6379/1'  # Use DB 1 for jobs
    
    try:
        redis_conn = redis.from_url(redis_url)
        redis_conn.ping()
        task_queue = Queue('castor_tasks', connection=redis_conn)
        logger.info("Background job system initialized")
    except Exception as e:
        logger.warning(f"Background jobs not available (Redis required): {e}")
        redis_conn = None
        task_queue = None


def enqueue_analysis_task(
    location: str,
    theme: str,
    candidate_name: Optional[str] = None,
    politician: Optional[str] = None,
    max_tweets: int = 100,
    user_id: Optional[str] = None
) -> Optional[str]:
    """
    Enqueue an analysis task to background queue.
    
    Args:
        location: Location to analyze
        theme: PND theme
        candidate_name: Optional candidate name
        politician: Optional politician handle
        max_tweets: Maximum tweets to analyze
        user_id: Optional user ID
        
    Returns:
        Job ID or None if queue unavailable
    """
    if not task_queue:
        logger.warning("Background queue not available, task will run synchronously")
        return None
    
    try:
        from tasks.analysis_tasks import run_analysis_task
        
        job = task_queue.enqueue(
            run_analysis_task,
            location,
            theme,
            candidate_name,
            politician,
            max_tweets,
            user_id,
            job_timeout='10m',  # 10 minute timeout
            result_ttl=3600  # Keep result for 1 hour
        )
        
        logger.info(f"Analysis task enqueued: {job.id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueueing analysis task: {e}", exc_info=True)
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a background job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job status dictionary or None
    """
    if not redis_conn:
        return None
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            'id': job.id,
            'status': job.get_status(),
            'result': job.result if job.is_finished else None,
            'error': str(job.exc_info) if job.is_failed else None,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None
        }
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return None


def enqueue_trending_detection(location: str) -> Optional[str]:
    """
    Enqueue trending topic detection task.
    
    Args:
        location: Location to analyze
        
    Returns:
        Job ID or None
    """
    if not task_queue:
        return None
    
    try:
        from tasks.trending_tasks import detect_trending_topics_task
        
        job = task_queue.enqueue(
            detect_trending_topics_task,
            location,
            job_timeout='5m',
            result_ttl=1800  # 30 minutes
        )
        
        logger.info(f"Trending detection task enqueued: {job.id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueueing trending task: {e}", exc_info=True)
        return None

