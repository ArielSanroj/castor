"""
Media product endpoints.
Provides neutral analysis for press dashboards.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from app.schemas.media import (
    MediaAnalysisRequest,
    MediaAnalysisResponse,
    MediaAnalysisSummary,
    MediaAnalysisMetadata,
)
from app.services.analysis_core import AnalysisCorePipeline
from services.openai_service import OpenAIService
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

media_bp = Blueprint("media_product", __name__)


def _get_pipeline() -> AnalysisCorePipeline:
    return current_app.extensions.get("analysis_core_pipeline")


def _get_openai_service() -> OpenAIService:
    return current_app.extensions.get("openai_service")


@media_bp.route("/analyze", methods=["POST"])
@limiter.limit("5 per minute")  # Rate limit for expensive operations
def media_analyze():
    try:
        payload = request.get_json(force=True, silent=False)
        req = MediaAnalysisRequest.model_validate(payload)
    except (TypeError, ValidationError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    pipeline = _get_pipeline()
    openai_svc = _get_openai_service()

    if not pipeline or not openai_svc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Servicios de análisis no disponibles",
                }
            ),
            503,
        )

    core_result = pipeline.run_core_pipeline(
        location=req.location,
        topic=req.topic,
        candidate_name=req.candidate_name,
        politician=req.politician,
        max_tweets=req.max_tweets,
        time_window_days=req.time_window_days,
        language=req.language,
    )

    media_summary_dict = openai_svc.generate_media_summary(core_result=core_result)
    summary = MediaAnalysisSummary(**media_summary_dict)

    metadata = MediaAnalysisMetadata(
        tweets_analyzed=core_result.tweets_analyzed,
        location=core_result.location,
        topic=core_result.topic,
        time_window_from=core_result.time_window_from,
        time_window_to=core_result.time_window_to,
        trending_topic=core_result.trending_topic,
        raw_query=core_result.raw_query,
    )

    response_model = MediaAnalysisResponse(
        success=True,
        summary=summary,
        sentiment_overview=core_result.sentiment_overview,
        topics=core_result.topics,
        peaks=core_result.peaks,
        chart_data=core_result.chart_data,
        metadata=metadata,
    )

    return jsonify(response_model.model_dump()), 200
