"""
Health check endpoints for E-14 Service.
Implements Kubernetes-compatible liveness and readiness probes.
"""
from flask import Blueprint, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """Legacy health endpoint."""
    live = _check_liveness()
    ready = _check_readiness()

    status = "healthy" if live["ok"] and ready["ok"] else "unhealthy"

    return jsonify({
        "status": status,
        "service": "e14-service",
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

    Returns:
        200: Process is alive
        503: Process should be restarted
    """
    result = _check_liveness()

    if result["ok"]:
        return jsonify({
            "status": "alive",
            "service": "e14-service",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "dead",
            "service": "e14-service",
            "error": result.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """
    Readiness probe - Can the service handle requests?

    Returns:
        200: Ready to receive traffic
        503: Not ready
    """
    result = _check_readiness()

    if result["ok"]:
        return jsonify({
            "status": "ready",
            "service": "e14-service",
            "checks": result["checks"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "service": "e14-service",
            "checks": result["checks"],
            "timestamp": datetime.utcnow().isoformat()
        }), 503


def _check_liveness() -> dict:
    """Check if process is alive."""
    try:
        _ = 1 + 1
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_readiness() -> dict:
    """Check if all dependencies are available."""
    checks = {}

    # Check database connection
    try:
        from app import db
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"status": "connected", "ok": True}
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        checks["database"] = {"status": "disconnected", "ok": False, "error": str(e)}

    # Check OCR service (Anthropic API)
    try:
        from config import Config
        if Config.ANTHROPIC_API_KEY:
            checks["anthropic_api"] = {"status": "configured", "ok": True}
        else:
            checks["anthropic_api"] = {"status": "not_configured", "ok": False}
    except Exception as e:
        checks["anthropic_api"] = {"status": "error", "ok": False, "error": str(e)}

    # Check Core Service connectivity
    try:
        from utils.service_clients import get_core_client
        client = get_core_client()
        health = client.health_check()
        checks["core_service"] = {
            "status": health.get("status", "unknown"),
            "ok": health.get("status") == "healthy",
            "circuit_breaker": health.get("circuit_breaker", {}).get("state", "unknown")
        }
    except Exception as e:
        logger.warning(f"Core service check failed: {e}")
        checks["core_service"] = {"status": "unreachable", "ok": False, "error": str(e)}

    # Check pipeline status
    try:
        pipeline = current_app.extensions.get('e14_pipeline')
        if pipeline:
            checks["pipeline"] = {"status": "ready", "ok": True}
        else:
            checks["pipeline"] = {"status": "not_initialized", "ok": True}
    except Exception as e:
        checks["pipeline"] = {"status": "error", "ok": False, "error": str(e)}

    # Overall readiness - database and anthropic are critical
    critical_ok = checks.get("database", {}).get("ok", False) and \
                  checks.get("anthropic_api", {}).get("ok", False)

    return {"ok": critical_ok, "checks": checks}


@health_bp.route('/health/dependencies', methods=['GET'])
def dependencies():
    """Detailed dependency health check."""
    result = _check_readiness()

    return jsonify({
        "service": "e14-service",
        "dependencies": result["checks"],
        "all_healthy": result["ok"],
        "timestamp": datetime.utcnow().isoformat()
    })
