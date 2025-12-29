"""
Advisor endpoints.
Generates human-in-the-loop draft suggestions (no auto-posting).
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from app.schemas.advisor import AdvisorRequest, AdvisorResponse, AdvisorDraft
from services.openai_service import OpenAIService
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

advisor_bp = Blueprint("advisor", __name__)


def _get_openai_service() -> OpenAIService:
    return current_app.extensions.get("openai_service")


@advisor_bp.route("/advisor/recommendations", methods=["POST"])
@limiter.limit("6 per minute")
def get_recommendations():
    """
    Generate draft suggestions for human review.
    """
    try:
        payload = request.get_json(force=True, silent=False) or {}
        req = AdvisorRequest.model_validate(payload)
    except (TypeError, ValidationError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    openai_svc = _get_openai_service()
    if not openai_svc:
        return jsonify({"success": False, "error": "Servicio de recomendaciones no disponible"}), 503

    try:
        response = openai_svc.generate_advisor_recommendations(req)
        return jsonify(response.model_dump()), 200
    except Exception as exc:
        logger.error("Error generating advisor recommendations: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500
