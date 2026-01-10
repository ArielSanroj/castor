"""
Forecast endpoints for ICCE, Momentum, and time series projections.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from app.schemas.forecast import (
    ForecastRequest,
    ICCEResponse,
    MomentumResponse,
    ForecastResponse,
    ScenarioRequest,
    ScenarioResponse,
    ForecastDashboardResponse,
)
from app.schemas.narrative import NarrativeMetricsResponse, NarrativeIndices, IVNResult
from app.services.forecast_service import ForecastService
from services.twitter_service import TwitterService
from services.sentiment_service import SentimentService
from services.database_service import DatabaseService
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

forecast_bp = Blueprint("forecast", __name__)


@forecast_bp.route("", methods=["GET"])
def forecast_info():
    """
    Get information about available forecast endpoints.
    """
    return jsonify({
        "service": "CASTOR Forecast API",
        "description": "Forecast endpoints for ICCE, Momentum, and time series projections",
        "endpoints": {
            "/api/forecast/icce": {
                "method": "POST",
                "description": "Calculate Índice Compuesto de Conversación Electoral (ICCE)",
                "required": ["location"],
                "optional": ["candidate_name", "politician", "days_back"]
            },
            "/api/forecast/momentum": {
                "method": "POST",
                "description": "Calculate Momentum Electoral de Conversación (MEC)",
                "required": ["location"],
                "optional": ["candidate_name", "politician", "days_back"]
            },
            "/api/forecast/forecast": {
                "method": "POST",
                "description": "Forecast ICCE values for future days",
                "required": ["location"],
                "optional": ["candidate_name", "politician", "days_back", "forecast_days", "model_type"]
            },
            "/api/forecast/scenario": {
                "method": "POST",
                "description": "Simulate impact of a scenario on ICCE",
                "required": ["location", "scenario_type"],
                "optional": ["candidate_name", "politician", "sentiment_shift"]
            },
            "/api/forecast/narrative-metrics": {
                "method": "POST",
                "description": "Calculate narrative electoral metrics (SVE, SNA, CP, NMI, IVN)",
                "required": ["location", "candidate_name"],
                "optional": ["topic", "days_back"]
            },
            "/api/forecast/dashboard": {
                "method": "POST",
                "description": "Get complete forecast dashboard with ICCE, Momentum, and Forecast",
                "required": ["location"],
                "optional": ["candidate_name", "politician", "days_back", "forecast_days"]
            }
        }
    }), 200


def _get_forecast_service() -> ForecastService:
    """Get forecast service instance."""
    from flask import current_app
    
    twitter_service = current_app.extensions.get("twitter_service")
    sentiment_service = current_app.extensions.get("sentiment_service")
    db_service = current_app.extensions.get("database_service")
    
    if not twitter_service or not sentiment_service:
        logger.error("Forecast service: Required services not available (twitter_service or sentiment_service)")
        raise RuntimeError("Required services not available: twitter_service or sentiment_service missing")
    
    return ForecastService(
        twitter_service=twitter_service,
        sentiment_service=sentiment_service,
        db_service=db_service
    )


@forecast_bp.route("/icce", methods=["POST"])
@limiter.limit("10 per minute")
def get_icce():
    """
    Calculate Índice Compuesto de Conversación Electoral (ICCE).
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "politician": "@juanperez",
        "days_back": 30
    }
    """
    try:
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        days_back = payload.get("days_back", 30)
        candidate_name = payload.get("candidate_name")
        politician = payload.get("politician")
        
        forecast_service = _get_forecast_service()
        icce_values = forecast_service.calculate_icce(
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            days_back=days_back
        )
        
        if not icce_values:
            return jsonify({
                "success": False,
                "error": "No data available for the specified parameters"
            }), 404
        
        current_icce = icce_values[-1].value if icce_values else 0.0
        
        response = ICCEResponse(
            success=True,
            candidate_name=candidate_name,
            location=location,
            current_icce=current_icce,
            historical_values=icce_values,
            metadata={
                "days_back": days_back,
                "data_points": len(icce_values),
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error calculating ICCE: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@forecast_bp.route("/momentum", methods=["POST"])
@limiter.limit("10 per minute")
def get_momentum():
    """
    Calculate Momentum Electoral de Conversación (MEC).
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30
    }
    """
    try:
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        days_back = payload.get("days_back", 30)
        candidate_name = payload.get("candidate_name")
        politician = payload.get("politician")
        
        forecast_service = _get_forecast_service()
        
        # Get ICCE values first
        icce_values = forecast_service.calculate_icce(
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            days_back=days_back
        )
        
        if len(icce_values) < 8:
            return jsonify({
                "success": False,
                "error": "Insufficient data for momentum calculation (need at least 8 days)"
            }), 400
        
        # Calculate momentum
        momentum_values = forecast_service.calculate_momentum(icce_values)
        
        if not momentum_values:
            return jsonify({
                "success": False,
                "error": "Could not calculate momentum"
            }), 500
        
        current_momentum = momentum_values[-1].momentum if momentum_values else 0.0
        current_trend = momentum_values[-1].trend if momentum_values else "stable"
        
        response = MomentumResponse(
            success=True,
            candidate_name=candidate_name,
            location=location,
            current_momentum=current_momentum,
            historical_momentum=momentum_values,
            trend=current_trend,
            metadata={
                "days_back": days_back,
                "data_points": len(momentum_values),
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error calculating momentum: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@forecast_bp.route("/forecast", methods=["POST"])
@limiter.limit("5 per minute")
def get_forecast():
    """
    Forecast ICCE values for future days.
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30,
        "forecast_days": 14,
        "model_type": "holt_winters"
    }
    """
    try:
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        days_back = payload.get("days_back", 30)
        forecast_days = payload.get("forecast_days", 14)
        model_type = payload.get("model_type", "holt_winters")
        candidate_name = payload.get("candidate_name")
        politician = payload.get("politician")
        
        forecast_service = _get_forecast_service()
        
        # Get ICCE values
        icce_values = forecast_service.calculate_icce(
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            days_back=days_back
        )
        
        if len(icce_values) < 7:
            return jsonify({
                "success": False,
                "error": "Insufficient data for forecast (need at least 7 days)"
            }), 400
        
        # Generate forecast
        forecast_points = forecast_service.forecast_icce(
            icce_values=icce_values,
            forecast_days=forecast_days,
            model_type=model_type
        )
        
        if not forecast_points:
            return jsonify({
                "success": False,
                "error": "Could not generate forecast"
            }), 500
        
        response = ForecastResponse(
            success=True,
            candidate_name=candidate_name,
            location=location,
            forecast_points=forecast_points,
            model_type=model_type,
            metadata={
                "days_back": days_back,
                "forecast_days": forecast_days,
                "historical_points": len(icce_values),
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@forecast_bp.route("/scenario", methods=["POST"])
@limiter.limit("5 per minute")
def simulate_scenario():
    """
    Simulate impact of a scenario on ICCE.
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "scenario_type": "debate",
        "sentiment_shift": 0.2
    }
    """
    try:
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        scenario_type = payload.get("scenario_type")
        if not scenario_type:
            return jsonify({
                "success": False,
                "error": "scenario_type is required"
            }), 400
        
        candidate_name = payload.get("candidate_name")
        politician = payload.get("politician")
        sentiment_shift = payload.get("sentiment_shift", 0.0)
        
        forecast_service = _get_forecast_service()
        
        # Get current ICCE
        icce_values = forecast_service.calculate_icce(
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            days_back=30
        )
        
        if not icce_values:
            return jsonify({
                "success": False,
                "error": "No data available for scenario simulation"
            }), 404
        
        baseline_icce = icce_values[-1].value
        
        # Simulate scenario
        simulation = forecast_service.simulate_scenario(
            baseline_icce=baseline_icce,
            scenario_type=scenario_type,
            sentiment_shift=sentiment_shift
        )
        
        # Get baseline forecast
        baseline_forecast = forecast_service.forecast_icce(
            icce_values=icce_values,
            forecast_days=14
        )
        
        # Simulated forecast (adjust based on scenario impact)
        simulated_icce_values = icce_values.copy()
        if simulated_icce_values:
            simulated_icce_values[-1].value = simulation.simulated_icce
        
        simulated_forecast = forecast_service.forecast_icce(
            icce_values=simulated_icce_values,
            forecast_days=14
        )
        
        response = ScenarioResponse(
            success=True,
            simulation=simulation,
            baseline_forecast=baseline_forecast,
            simulated_forecast=simulated_forecast,
            metadata={
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error simulating scenario: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@forecast_bp.route("/narrative-metrics", methods=["POST"])
@limiter.limit("10 per minute")
def get_narrative_metrics():
    """
    Calculate narrative electoral metrics (SVE, SNA, CP, NMI, IVN).
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "topic": "Seguridad",
        "days_back": 7
    }
    """
    try:
        from app.services.analysis_core import AnalysisCorePipeline
        from flask import current_app
        
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        candidate_name = payload.get("candidate_name")
        if not candidate_name:
            return jsonify({
                "success": False,
                "error": "candidate_name is required for narrative metrics"
            }), 400
        
        topic = payload.get("topic")
        days_back = payload.get("days_back", 7)
        
        # Use the core pipeline to get tweets and sentiment
        pipeline = current_app.extensions.get("analysis_core_pipeline")
        if not pipeline:
            return jsonify({
                "success": False,
                "error": "Analysis pipeline not available"
            }), 503
        
        core_result = pipeline.run_core_pipeline(
            location=location,
            topic=topic,
            candidate_name=candidate_name,
            politician=None,
            max_tweets=min(days_back * 10, 200),
            time_window_days=days_back,
            language="es"
        )
        
        if core_result.narrative_metrics:
            metrics = core_result.narrative_metrics
            
            response = NarrativeMetricsResponse(
                success=True,
                narrative_indices=NarrativeIndices(
                    sve=metrics.get("sve", 0.0),
                    sna=metrics.get("sna", 0.0),
                    cp=metrics.get("cp", 0.0),
                    nmi=metrics.get("nmi", 0.0)
                ),
                ivn=IVNResult(**metrics.get("ivn", {})),
                metadata={
                    "location": location,
                    "candidate_name": candidate_name,
                    "topic": topic,
                    "tweets_analyzed": core_result.tweets_analyzed,
                    "calculated_at": datetime.utcnow().isoformat()
                }
            )
            
            return jsonify(response.model_dump()), 200
        else:
            return jsonify({
                "success": False,
                "error": "Could not calculate narrative metrics"
            }), 500
        
    except Exception as e:
        logger.error(f"Error calculating narrative metrics: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@forecast_bp.route("/dashboard", methods=["POST"])
@limiter.limit("5 per minute")
def get_dashboard():
    """
    Get complete forecast dashboard with ICCE, Momentum, and Forecast.
    
    Request body:
    {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30,
        "forecast_days": 14
    }
    """
    try:
        from datetime import datetime
        
        payload = request.get_json() or {}
        
        location = payload.get("location")
        if not location:
            return jsonify({
                "success": False,
                "error": "location is required"
            }), 400
        
        days_back = payload.get("days_back", 30)
        forecast_days = payload.get("forecast_days", 14)
        candidate_name = payload.get("candidate_name")
        politician = payload.get("politician")
        
        try:
            forecast_service = _get_forecast_service()
        except RuntimeError as e:
            logger.error(f"Forecast dashboard: Service initialization failed: {e}")
            return jsonify({
                "success": False,
                "error": "Servicios de forecast no disponibles. Verifica la configuración de Twitter y Sentiment services."
            }), 503
        
        # Get all data
        try:
            icce_values = forecast_service.calculate_icce(
                location=location,
                candidate_name=candidate_name,
                politician=politician,
                days_back=days_back
            )
        except Exception as e:
            logger.error(f"Error calculating ICCE: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Error al calcular ICCE: {str(e)}"
            }), 500
        
        if not icce_values:
            return jsonify({
                "success": False,
                "error": "No se encontraron datos de Twitter para los parámetros proporcionados. Verifica que la ubicación, candidato o tema sean correctos.",
                "message": "No hay suficientes tweets para calcular ICCE. Intenta con una ubicación diferente o un rango de fechas más amplio."
            }), 200
        
        # Calculate momentum and smoothed values
        momentum_values = forecast_service.calculate_momentum(icce_values) if len(icce_values) >= 2 else []
        smoothed_values = forecast_service.calculate_ema_smooth(icce_values) if icce_values else []
        forecast_points = forecast_service.forecast_icce(icce_values, forecast_days) if len(icce_values) >= 7 else []
        
        # Build JSON response matching exact structure from example
        # Structure: { candidate, series: { dates, icce, icce_smooth, momentum }, forecast: { dates, icce_pred, pred_low, pred_high } }
        
        # Prepare series data (convert ICCE from 0-100 scale to 0-1 scale to match example)
        series_dates = [v.date.strftime("%Y-%m-%d") for v in icce_values]
        icce_raw = [v.value / 100.0 for v in icce_values]  # Convert to [0,1] scale
        icce_smooth = smoothed_values if smoothed_values else icce_raw
        # Momentum series - pad with None/0 for first day (momentum starts from day 2)
        momentum_series = [0.0] + [m.momentum for m in momentum_values] if momentum_values else []
        # Ensure all arrays have same length
        if len(momentum_series) < len(icce_raw):
            momentum_series.extend([0.0] * (len(icce_raw) - len(momentum_series)))
        
        # Prepare forecast data
        forecast_dates = [p.date.strftime("%Y-%m-%d") for p in forecast_points]
        icce_pred = [p.projected_value / 100.0 for p in forecast_points]  # Convert to [0,1] scale
        pred_low = [p.lower_bound / 100.0 for p in forecast_points]
        pred_high = [p.upper_bound / 100.0 for p in forecast_points]
        
        # Build response matching example structure
        response_data = {
            "success": True,
            "candidate": politician or candidate_name or "unknown",
            "candidate_name": candidate_name,
            "location": location,
            "series": {
                "dates": series_dates,
                "icce": icce_raw,
                "icce_smooth": icce_smooth,
                "momentum": momentum_series[:len(icce_raw)]  # Ensure same length
            },
            "forecast": {
                "dates": forecast_dates,
                "icce_pred": icce_pred,
                "pred_low": pred_low,
                "pred_high": pred_high
            },
            "metadata": {
                "calculated_at": datetime.utcnow().isoformat(),
                "days_back": days_back,
                "forecast_days": forecast_days,
                "model_type": "holt_winters"
            }
        }
        
        # Also include narrative metrics if available
        if candidate_name:
            try:
                from app.services.analysis_core import AnalysisCorePipeline
                pipeline = current_app.extensions.get("analysis_core_pipeline")
                if pipeline:
                    core_result = pipeline.run_core_pipeline(
                        location=location,
                        topic=None,
                        candidate_name=candidate_name,
                        politician=politician,
                        max_tweets=min(days_back * 10, 200),
                        time_window_days=days_back,
                        language="es"
                    )
                    if core_result.narrative_metrics:
                        response_data["metadata"]["narrative_metrics"] = core_result.narrative_metrics
            except Exception as e:
                logger.warning(f"Could not get narrative metrics for dashboard: {e}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

