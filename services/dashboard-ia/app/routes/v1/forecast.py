"""
API v1 Forecast endpoints.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

logger = logging.getLogger(__name__)

forecast_v1_bp = Blueprint('forecast_v1', __name__, url_prefix='/forecast')


class ForecastRequest(BaseModel):
    """Forecast request."""
    location: str = Field("Colombia", min_length=1)
    candidate_name: Optional[str] = None
    days_back: int = Field(30, ge=7, le=90)
    forecast_days: int = Field(14, ge=7, le=30)


def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, status_code: int = 400):
    return jsonify({"ok": False, "error": error}), status_code


@forecast_v1_bp.route('/icce', methods=['POST'])
def get_icce():
    """
    POST /api/v1/forecast/icce

    Calculate ICCE (Indice Compuesto de Capacidad Electoral).

    Request:
        {
            "location": "Bogota",
            "candidate_name": "Candidato X",
            "days_back": 30
        }

    Response:
        {
            "ok": true,
            "data": {
                "icce": 68.5,
                "components": {
                    "sov": 25.3,
                    "sna": 15.2,
                    "engagement": 28.0
                },
                "trend": "up",
                "change_7d": 2.3
            }
        }
    """
    try:
        try:
            req = ForecastRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        # Get forecast service
        # Note: This would need to be properly initialized
        from app.services.forecast_service import ForecastService
        forecast_service = ForecastService()

        result = forecast_service.calculate_icce(
            location=req.location,
            candidate_name=req.candidate_name,
            days_back=req.days_back
        )

        return success_response(result)

    except Exception as e:
        logger.error(f"ICCE error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@forecast_v1_bp.route('/momentum', methods=['POST'])
def get_momentum():
    """
    POST /api/v1/forecast/momentum

    Calculate electoral momentum (rate of change).

    Response:
        {
            "ok": true,
            "data": {
                "momentum": 0.018,
                "direction": "positive",
                "strength": "moderate"
            }
        }
    """
    try:
        try:
            req = ForecastRequest(**request.get_json())
        except ValidationError:
            req = ForecastRequest()

        from app.services.forecast_service import ForecastService
        forecast_service = ForecastService()

        result = forecast_service.calculate_momentum(
            location=req.location,
            candidate_name=req.candidate_name,
            days_back=req.days_back
        )

        return success_response(result)

    except Exception as e:
        logger.error(f"Momentum error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@forecast_v1_bp.route('/predict', methods=['POST'])
def predict():
    """
    POST /api/v1/forecast/predict

    Generate ICCE forecast.

    Response:
        {
            "ok": true,
            "data": {
                "current_icce": 68.5,
                "predicted_icce": 72.1,
                "forecast": [
                    { "date": "2024-01-15", "value": 69.0, "low": 67.0, "high": 71.0 },
                    ...
                ],
                "confidence": 0.85
            }
        }
    """
    try:
        try:
            req = ForecastRequest(**request.get_json())
        except ValidationError:
            req = ForecastRequest()

        from app.services.forecast_service import ForecastService
        forecast_service = ForecastService()

        result = forecast_service.forecast_icce(
            location=req.location,
            candidate_name=req.candidate_name,
            days_back=req.days_back,
            forecast_days=req.forecast_days
        )

        return success_response(result)

    except Exception as e:
        logger.error(f"Forecast error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@forecast_v1_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """
    GET /api/v1/forecast/dashboard

    Get complete forecast dashboard data.

    Query params:
        - location: Location filter
        - candidate: Candidate name
    """
    try:
        location = request.args.get('location', 'Colombia')
        candidate = request.args.get('candidate')

        from app.services.forecast_service import ForecastService
        forecast_service = ForecastService()

        # Get all metrics
        icce = forecast_service.calculate_icce(location=location, candidate_name=candidate)
        momentum = forecast_service.calculate_momentum(location=location, candidate_name=candidate)
        forecast = forecast_service.forecast_icce(location=location, candidate_name=candidate)

        return success_response({
            "icce": icce,
            "momentum": momentum,
            "forecast": forecast,
            "location": location,
            "candidate": candidate
        })

    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)
