"""
Health check endpoints for Core Service.
Implements Kubernetes-compatible liveness and readiness probes.
"""
from flask import Blueprint, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """Legacy health endpoint - returns both liveness and readiness."""
    live = _check_liveness()
    ready = _check_readiness()

    status = "healthy" if live["ok"] and ready["ok"] else "unhealthy"

    return jsonify({
        "status": status,
        "service": "core-service",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "liveness": live,
            "readiness": ready
        }
    }), 200 if status == "healthy" else 503


@health_bp.route('/health/live', methods=['GET'])
def liveness():
    """
    Liveness probe - Is the process running?

    Kubernetes uses this to know if it should RESTART the container.
    Should only fail if the process is deadlocked or unrecoverable.

    Returns:
        200: Process is alive
        503: Process should be restarted
    """
    result = _check_liveness()

    if result["ok"]:
        return jsonify({
            "status": "alive",
            "service": "core-service",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "dead",
            "service": "core-service",
            "error": result.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """
    Readiness probe - Can the service handle requests?

    Kubernetes uses this to know if it should STOP SENDING TRAFFIC.
    Fails if dependencies (DB, Redis, etc.) are unavailable.

    Returns:
        200: Ready to receive traffic
        503: Not ready, stop sending traffic (but don't restart)
    """
    result = _check_readiness()

    if result["ok"]:
        return jsonify({
            "status": "ready",
            "service": "core-service",
            "checks": result["checks"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "service": "core-service",
            "checks": result["checks"],
            "timestamp": datetime.utcnow().isoformat()
        }), 503


def _check_liveness() -> dict:
    """
    Check if process is alive and responsive.
    Should be very fast and simple.
    """
    try:
        # Simple check - can we execute Python code?
        _ = 1 + 1
        return {"ok": True}
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return {"ok": False, "error": str(e)}


def _check_readiness() -> dict:
    """
    Check if all dependencies are available.
    """
    checks = {}

    # Check database connection
    try:
        from app import db
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"status": "connected", "ok": True}
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        checks["database"] = {"status": "disconnected", "ok": False, "error": str(e)}

    # Check Redis (if configured)
    try:
        from config import Config
        if Config.REDIS_URL:
            import redis
            r = redis.from_url(Config.REDIS_URL)
            r.ping()
            checks["redis"] = {"status": "connected", "ok": True}
        else:
            checks["redis"] = {"status": "not_configured", "ok": True}
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
        checks["redis"] = {"status": "disconnected", "ok": False, "error": str(e)}

    # Overall readiness
    all_ok = all(c.get("ok", False) for c in checks.values())

    return {"ok": all_ok, "checks": checks}


@health_bp.route('/health/dependencies', methods=['GET'])
def dependencies():
    """
    Detailed dependency health check.
    Returns status of all external dependencies.
    """
    result = _check_readiness()

    return jsonify({
        "service": "core-service",
        "dependencies": result["checks"],
        "all_healthy": result["ok"],
        "timestamp": datetime.utcnow().isoformat()
    })
