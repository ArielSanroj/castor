"""
Media product endpoints.
Provides neutral analysis for press dashboards.
"""
import logging
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from app.schemas.media import (
    MediaAnalysisRequest,
    MediaAnalysisResponse,
    MediaAnalysisSummary,
    MediaAnalysisMetadata,
    TweetSummary,
)
from app.services.analysis_core import AnalysisCorePipeline
from services.openai_service import OpenAIService
from services.database_service import DatabaseService
from services.rag_service import get_rag_service
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

media_bp = Blueprint("media_product", __name__)


def _get_db_service() -> DatabaseService:
    """Get or create database service."""
    if not hasattr(current_app, '_db_service'):
        current_app._db_service = DatabaseService()
    return current_app._db_service


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

    if not pipeline:
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

    # Generate summary with OpenAI if available, otherwise use fallback
    if openai_svc:
        try:
            media_summary_dict = openai_svc.generate_media_summary(core_result=core_result)
            summary = MediaAnalysisSummary(**media_summary_dict)
        except Exception as e:
            logger.warning(f"OpenAI summary generation failed: {e}, using fallback")
            # Fallback summary without OpenAI
            summary = MediaAnalysisSummary(
                overview=f"Análisis de conversación en {req.location}" + (f" sobre {req.topic}" if req.topic else ""),
                key_stats=[],
                key_findings=[f"Se analizaron {core_result.tweets_analyzed} tweets" if core_result.tweets_analyzed > 0 else "No se encontraron tweets"]
            )
    else:
        # Fallback summary without OpenAI
        summary = MediaAnalysisSummary(
            overview=f"Análisis de conversación en {req.location}" + (f" sobre {req.topic}" if req.topic else ""),
            key_stats=[],
            key_findings=[f"Se analizaron {core_result.tweets_analyzed} tweets" if core_result.tweets_analyzed > 0 else "No se encontraron tweets"]
        )

    metadata = MediaAnalysisMetadata(
        tweets_analyzed=core_result.tweets_analyzed,
        location=core_result.location,
        topic=core_result.topic,
        time_window_from=core_result.time_window_from,
        time_window_to=core_result.time_window_to,
        trending_topic=core_result.trending_topic,
        raw_query=core_result.raw_query,
        from_cache=core_result.from_cache,
        cached_at=core_result.cached_at,
    )

    # Convert tweets_data to TweetSummary for the response
    tweets = [
        TweetSummary(
            tweet_id=t.tweet_id,
            author_username=t.author_username,
            author_name=t.author_name,
            content=t.content,
            sentiment_label=t.sentiment_label,
            pnd_topic=t.pnd_topic,
            retweet_count=t.retweet_count,
            like_count=t.like_count,
            reply_count=t.reply_count,
        )
        for t in core_result.tweets_data
    ]

    response_model = MediaAnalysisResponse(
        success=True,
        summary=summary,
        sentiment_overview=core_result.sentiment_overview,
        topics=core_result.topics,
        peaks=core_result.peaks,
        chart_data=core_result.chart_data,
        metadata=metadata,
        tweets=tweets,
    )

    # Index into RAG (best-effort)
    try:
        rag = get_rag_service()
        analysis_payload = {
            "executive_summary": {
                "overview": summary.overview,
                "key_findings": summary.key_findings,
                "recommendations": [],
            },
            "topics": [t.model_dump() if hasattr(t, "model_dump") else t for t in core_result.topics],
            "sentiment_overview": core_result.sentiment_overview,
            "metadata": metadata.model_dump() if hasattr(metadata, "model_dump") else metadata,
        }
        rag.index_analysis(
            analysis_id=f"media_{uuid.uuid4().hex}",
            analysis_data=analysis_payload,
            metadata={
                "location": metadata.location,
                "candidate": req.candidate_name,
                "created_at": metadata.time_window_to,
                "topic_name": metadata.topic,
            },
        )
    except Exception as e:
        logger.warning(f"RAG indexing skipped (media): {e}")

    return jsonify(response_model.model_dump()), 200


@media_bp.route("/latest", methods=["GET"])
def get_latest_analysis():
    """
    Get the latest analysis data from database.
    Returns real data from stored tweets and analysis.
    """
    try:
        db_service = _get_db_service()

        # Get latest successful API call
        api_calls = db_service.get_api_calls(limit=1)
        if not api_calls:
            return jsonify({"success": False, "error": "No hay análisis guardados"}), 404

        api_call = api_calls[0]
        api_call_id = api_call['id']

        # Get full data
        full_data = db_service.get_api_call_with_data(api_call_id)
        if not full_data:
            return jsonify({"success": False, "error": "Error obteniendo datos"}), 500

        # Get tweets sample
        tweets = db_service.get_tweets_by_api_call(api_call_id, limit=50)

        # Build response with all dashboard data
        analysis = full_data.get('analysis_snapshot')
        pnd_metrics = full_data.get('pnd_metrics', [])

        # Build topics array from PND metrics
        topics = []
        for metric in pnd_metrics:
            topics.append({
                "topic": metric.pnd_axis_display,
                "tweet_count": metric.tweet_count,
                "sentiment": {
                    "positive": metric.sentiment_positive,
                    "neutral": 1 - metric.sentiment_positive - metric.sentiment_negative,
                    "negative": metric.sentiment_negative
                },
                "icce": metric.icce,
                "sov": metric.sov,
                "sna": metric.sna,
                "trend": metric.trend
            })

        # Sort topics by tweet_count descending
        topics.sort(key=lambda x: x['tweet_count'], reverse=True)

        # Build response
        response = {
            "success": True,
            "api_call_id": api_call_id,
            "candidate_name": api_call.get('candidate_name', ''),
            "location": api_call.get('location', ''),
            "politician": api_call.get('politician', ''),
            "fetched_at": api_call.get('fetched_at'),

            # Media data
            "mediaData": {
                "success": True,
                "candidate_name": api_call.get('candidate_name', ''),
                "location": api_call.get('location', ''),
                "summary": {
                    "key_findings": analysis.key_findings if analysis else [],
                    "executive_summary": analysis.executive_summary if analysis else "",
                    "key_stats": analysis.key_stats if analysis else [],
                    "recommendations": analysis.recommendations if analysis else []
                },
                "topics": topics,
                "sentiment_overview": {
                    "positive": analysis.sentiment_positive if analysis else 0.33,
                    "negative": analysis.sentiment_negative if analysis else 0.33,
                    "neutral": analysis.sentiment_neutral if analysis else 0.34
                },
                "metadata": {
                    "tweets_analyzed": full_data.get('tweets_count', 0),
                    "time_window_from": api_call.get('fetched_at'),
                    "time_window_to": api_call.get('fetched_at'),
                    "geo_distribution": analysis.geo_distribution if analysis else []
                }
            },

            # Analysis metrics
            "analysisSnapshot": {
                "icce": analysis.icce if analysis else 50,
                "sov": analysis.sov if analysis else 0,
                "sna": analysis.sna if analysis else 0,
                "momentum": analysis.momentum if analysis else 0,
                "sentiment_positive": analysis.sentiment_positive if analysis else 0.33,
                "sentiment_negative": analysis.sentiment_negative if analysis else 0.33,
                "sentiment_neutral": analysis.sentiment_neutral if analysis else 0.34,
                "trending_topics": analysis.trending_topics if analysis else []
            },

            # PND metrics for table
            "pndMetrics": [
                {
                    "pnd_axis": m.pnd_axis,
                    "pnd_axis_display": m.pnd_axis_display,
                    "icce": m.icce,
                    "sov": m.sov,
                    "sna": m.sna,
                    "tweet_count": m.tweet_count,
                    "trend": m.trend
                }
                for m in pnd_metrics
            ],

            # Sample tweets
            "tweets": tweets,

            # Tweets count
            "tweetsCount": full_data.get('tweets_count', 0)
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting latest analysis: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@media_bp.route("/analysis/<api_call_id>", methods=["GET"])
def get_analysis_by_id(api_call_id: str):
    """
    Get a specific analysis by API call ID.
    Returns full data for rendering dashboard.
    """
    try:
        db_service = _get_db_service()

        # Get full data for this specific API call
        full_data = db_service.get_api_call_with_data(api_call_id)
        if not full_data:
            return jsonify({"success": False, "error": "Análisis no encontrado"}), 404

        api_call = full_data.get('api_call')
        if not api_call:
            return jsonify({"success": False, "error": "Datos de llamada no encontrados"}), 404

        # Get tweets sample
        tweets = db_service.get_tweets_by_api_call(api_call_id, limit=50)

        # Build response with all dashboard data
        analysis = full_data.get('analysis_snapshot')
        pnd_metrics = full_data.get('pnd_metrics', [])

        # Build topics array from PND metrics
        topics = []
        for metric in pnd_metrics:
            topics.append({
                "topic": metric.pnd_axis_display,
                "tweet_count": metric.tweet_count,
                "sentiment": {
                    "positive": metric.sentiment_positive,
                    "neutral": 1 - metric.sentiment_positive - metric.sentiment_negative,
                    "negative": metric.sentiment_negative
                },
                "icce": metric.icce,
                "sov": metric.sov,
                "sna": metric.sna,
                "trend": metric.trend
            })

        # Sort topics by tweet_count descending
        topics.sort(key=lambda x: x['tweet_count'], reverse=True)

        # Build response (api_call is a dict from get_api_call_with_data)
        response = {
            "success": True,
            "api_call_id": api_call_id,
            "candidate_name": api_call.get('candidate_name') or '',
            "location": api_call.get('location') or '',
            "politician": api_call.get('politician') or '',
            "fetched_at": api_call.get('fetched_at'),

            # Media data
            "mediaData": {
                "success": True,
                "candidate_name": api_call.get('candidate_name') or '',
                "location": api_call.get('location') or '',
                "fetched_at": api_call.get('fetched_at'),
                "summary": {
                    "key_findings": analysis.key_findings if analysis else [],
                    "executive_summary": analysis.executive_summary if analysis else "",
                    "key_stats": analysis.key_stats if analysis else [],
                    "recommendations": analysis.recommendations if analysis else []
                },
                "topics": topics,
                "sentiment_overview": {
                    "positive": analysis.sentiment_positive if analysis else 0.33,
                    "negative": analysis.sentiment_negative if analysis else 0.33,
                    "neutral": analysis.sentiment_neutral if analysis else 0.34
                },
                "metadata": {
                    "tweets_analyzed": full_data.get('tweets_count', 0),
                    "time_window_from": api_call.get('fetched_at'),
                    "time_window_to": api_call.get('fetched_at'),
                    "geo_distribution": analysis.geo_distribution if analysis else []
                }
            },

            # Analysis metrics
            "analysisSnapshot": {
                "icce": analysis.icce if analysis else 50,
                "sov": analysis.sov if analysis else 0,
                "sna": analysis.sna if analysis else 0,
                "momentum": analysis.momentum if analysis else 0,
                "sentiment_positive": analysis.sentiment_positive if analysis else 0.33,
                "sentiment_negative": analysis.sentiment_negative if analysis else 0.33,
                "sentiment_neutral": analysis.sentiment_neutral if analysis else 0.34,
                "trending_topics": analysis.trending_topics if analysis else []
            },

            # PND metrics for table
            "pndMetrics": [
                {
                    "pnd_axis": m.pnd_axis,
                    "pnd_axis_display": m.pnd_axis_display,
                    "icce": m.icce,
                    "sov": m.sov,
                    "sna": m.sna,
                    "tweet_count": m.tweet_count,
                    "trend": m.trend
                }
                for m in pnd_metrics
            ],

            # Sample tweets
            "tweets": tweets,

            # Tweets count
            "tweetsCount": full_data.get('tweets_count', 0)
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting analysis {api_call_id}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@media_bp.route("/history", methods=["GET"])
def get_analysis_history():
    """Get list of all stored analyses with complete data (tweets + PND metrics)."""
    try:
        db_service = _get_db_service()

        candidate = request.args.get('candidate')
        location = request.args.get('location')
        requested_limit = int(request.args.get('limit', 20))

        # Buscar más registros para asegurar que encontramos los completos
        # ya que muchos pueden estar en estado "processing"
        api_calls = db_service.get_api_calls(
            candidate_name=candidate,
            location=location,
            limit=200  # Buscar suficientes para filtrar
        )

        # Filtrar solo análisis completos: completados + tweets + métricas PND
        complete_analyses = []
        for call in api_calls:
            if call.get('status') != 'completed' or call.get('tweets_retrieved', 0) == 0:
                continue

            # Verificar si tiene métricas PND
            full_data = db_service.get_api_call_with_data(call['id'])
            if full_data and len(full_data.get('pnd_metrics', [])) > 0:
                call['pnd_metrics_count'] = len(full_data.get('pnd_metrics', []))
                complete_analyses.append(call)

                # Aplicar el límite solicitado después de filtrar
                if len(complete_analyses) >= requested_limit:
                    break

        return jsonify({
            "success": True,
            "count": len(complete_analyses),
            "api_calls": complete_analyses
        }), 200

    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@media_bp.route("/tweets/<api_call_id>", methods=["GET"])
def get_tweets_for_analysis(api_call_id: str):
    """Get all tweets for a specific API call."""
    try:
        db_service = _get_db_service()

        limit = int(request.args.get('limit', 500))
        offset = int(request.args.get('offset', 0))

        tweets = db_service.get_tweets_by_api_call(api_call_id, limit=limit, offset=offset)

        return jsonify({
            "success": True,
            "api_call_id": api_call_id,
            "count": len(tweets),
            "tweets": tweets
        }), 200

    except Exception as e:
        logger.error(f"Error getting tweets: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
