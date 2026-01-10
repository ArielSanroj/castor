"""
Health check endpoint.
"""
from flask import Blueprint, jsonify, current_app
from datetime import datetime
from typing import Dict, Any
import logging
from sqlalchemy import text

from utils.twitter_rate_tracker import get_twitter_usage_stats
from utils.cache import redis_client
from utils.circuit_breaker import (
    get_openai_circuit_breaker,
    get_twitter_circuit_breaker,
    CircuitState
)

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


def _check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        db_service = current_app.extensions.get("database_service")
        if not db_service:
            return {"status": "unavailable", "error": "Database service not initialized"}
        
        # Try to execute a simple query
        session = db_service.get_session()
        try:
            session.execute(text("SELECT 1"))
            session.commit()
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Database health check exception: {e}")
        return {"status": "error", "error": str(e)}


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        if redis_client is None:
            return {
                "status": "unavailable",
                "message": "Redis not configured, using in-memory cache"
            }
        
        # Try to ping Redis
        redis_client.ping()
        return {"status": "ok"}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "unavailable",
            "error": str(e),
            "message": "Falling back to in-memory cache"
        }


def _check_circuit_breakers() -> Dict[str, Any]:
    """Check circuit breaker states."""
    openai_cb = get_openai_circuit_breaker()
    twitter_cb = get_twitter_circuit_breaker()
    
    return {
        "openai": {
            "state": openai_cb.state.value,
            "failure_count": openai_cb.failure_count,
            "last_failure": openai_cb.last_failure_time.isoformat() if openai_cb.last_failure_time else None
        },
        "twitter": {
            "state": twitter_cb.state.value,
            "failure_count": twitter_cb.failure_count,
            "last_failure": twitter_cb.last_failure_time.isoformat() if twitter_cb.last_failure_time else None
        }
    }


@health_bp.route('/health', methods=['GET'])
def health():
    """
    Comprehensive health check endpoint.
    
    Returns:
        Status, timestamp, and health checks for DB/Redis/Circuit Breakers
    """
    db_check = _check_database()
    redis_check = _check_redis()
    circuit_breakers = _check_circuit_breakers()
    
    # Overall status: ok if DB is ok, warning if Redis is unavailable, degraded if DB fails
    overall_status = "ok"
    if db_check.get("status") != "ok":
        overall_status = "degraded"
    elif redis_check.get("status") == "unavailable":
        overall_status = "degraded"  # Still functional but degraded
    
    # Check if any circuit breakers are open
    if (circuit_breakers["openai"]["state"] == CircuitState.OPEN.value or
        circuit_breakers["twitter"]["state"] == CircuitState.OPEN.value):
        overall_status = "degraded"
    
    response = {
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'CASTOR ELECCIONES API',
        'version': '1.0.0',
        'checks': {
            'database': db_check,
            'redis': redis_check,
            'circuit_breakers': circuit_breakers
        }
    }
    
    # Return 200 for ok/degraded, 503 for critical failures
    status_code = 200 if overall_status in ("ok", "degraded") else 503
    return jsonify(response), status_code


@health_bp.route('/twitter-usage', methods=['GET'])
def twitter_usage():
    """Get Twitter API usage statistics (Free tier monitoring)."""
    try:
        stats = get_twitter_usage_stats()
        return jsonify({
            'success': True,
            'plan': 'Free Tier (100 posts/month)',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@health_bp.route('/health/deep', methods=['GET'])
def deep_health():
    """
    Deep health check that tests external service connectivity.
    WARNING: This endpoint makes actual API calls - use sparingly.
    """
    from config import Config

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check OpenAI API key presence
    results["checks"]["openai"] = {
        "configured": bool(Config.OPENAI_API_KEY),
        "model": Config.OPENAI_MODEL,
        "circuit_breaker": get_openai_circuit_breaker().get_state()
    }

    # Check Twitter API key presence
    results["checks"]["twitter"] = {
        "configured": bool(Config.TWITTER_BEARER_TOKEN),
        "circuit_breaker": get_twitter_circuit_breaker().get_state(),
        "usage": get_twitter_usage_stats()
    }

    # Check Database
    results["checks"]["database"] = _check_database()

    # Check Redis
    results["checks"]["redis"] = _check_redis()

    # Overall status
    all_ok = (
        results["checks"]["database"].get("status") == "ok" and
        results["checks"]["openai"]["configured"] and
        results["checks"]["twitter"]["configured"]
    )

    results["status"] = "ok" if all_ok else "degraded"

    return jsonify(results), 200 if all_ok else 503


@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """Kubernetes-style readiness probe."""
    db_check = _check_database()
    if db_check.get("status") != "ok":
        return jsonify({"ready": False, "reason": "database unavailable"}), 503
    return jsonify({"ready": True}), 200


@health_bp.route('/health/live', methods=['GET'])
def liveness():
    """Kubernetes-style liveness probe."""
    return jsonify({"alive": True, "timestamp": datetime.utcnow().isoformat()}), 200

