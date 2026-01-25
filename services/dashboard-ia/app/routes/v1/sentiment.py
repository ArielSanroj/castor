"""
API v1 Sentiment Analysis endpoints.
Versioned endpoints with standardized response format.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

logger = logging.getLogger(__name__)

sentiment_v1_bp = Blueprint('sentiment_v1', __name__, url_prefix='/sentiment')


# ============================================================================
# Pydantic Schemas
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Sentiment analysis request."""
    texts: List[str] = Field(..., min_length=1, max_length=100)
    lang: str = Field("es", pattern="^(es|en)$")


class SentimentResult(BaseModel):
    """Single sentiment result."""
    text: str
    positive: float
    negative: float
    neutral: float
    dominant: str
    confidence: float


# ============================================================================
# Response Helpers
# ============================================================================

def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, status_code: int = 400):
    return jsonify({"ok": False, "error": error}), status_code


# ============================================================================
# Endpoints
# ============================================================================

@sentiment_v1_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    POST /api/v1/sentiment/analyze

    Analyze sentiment of one or more texts.

    Request:
        {
            "texts": ["Excelente propuesta", "Muy mal gobierno"],
            "lang": "es"
        }

    Response:
        {
            "ok": true,
            "data": {
                "results": [
                    {
                        "text": "Excelente propuesta",
                        "positive": 0.92,
                        "negative": 0.03,
                        "neutral": 0.05,
                        "dominant": "positive",
                        "confidence": 0.92
                    },
                    ...
                ],
                "summary": {
                    "total": 2,
                    "positive_count": 1,
                    "negative_count": 1,
                    "neutral_count": 0
                }
            }
        }
    """
    try:
        # Validate request
        try:
            req = AnalyzeRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        # Get sentiment service
        sentiment_service = current_app.extensions.get('sentiment_service')
        if not sentiment_service:
            return error_response("Sentiment service not available", status_code=503)

        # Analyze texts
        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for text in req.texts:
            analysis = sentiment_service.analyze_sentiment(text)

            positive = analysis.get('positive', 0.0)
            negative = analysis.get('negative', 0.0)
            neutral = analysis.get('neutral', 0.0)

            # Determine dominant sentiment
            scores = {'positive': positive, 'negative': negative, 'neutral': neutral}
            dominant = max(scores, key=scores.get)
            confidence = max(positive, negative, neutral)

            if dominant == 'positive':
                positive_count += 1
            elif dominant == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

            results.append({
                "text": text[:100] + "..." if len(text) > 100 else text,
                "positive": round(positive, 4),
                "negative": round(negative, 4),
                "neutral": round(neutral, 4),
                "dominant": dominant,
                "confidence": round(confidence, 4)
            })

        return success_response({
            "results": results,
            "summary": {
                "total": len(results),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count
            }
        })

    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@sentiment_v1_bp.route('/batch', methods=['POST'])
def analyze_batch():
    """
    POST /api/v1/sentiment/batch

    Batch sentiment analysis with IDs.

    Request:
        {
            "items": [
                {"id": "1", "text": "Texto 1"},
                {"id": "2", "text": "Texto 2"}
            ]
        }

    Response:
        {
            "ok": true,
            "data": {
                "results": {
                    "1": { "positive": 0.8, ... },
                    "2": { "positive": 0.2, ... }
                }
            }
        }
    """
    try:
        data = request.get_json()
        items = data.get("items", [])

        if not items or len(items) > 100:
            return error_response("Items required (max 100)")

        sentiment_service = current_app.extensions.get('sentiment_service')
        if not sentiment_service:
            return error_response("Sentiment service not available", status_code=503)

        results = {}
        for item in items:
            item_id = item.get("id", str(len(results)))
            text = item.get("text", "")

            if text:
                analysis = sentiment_service.analyze_sentiment(text)
                results[item_id] = {
                    "positive": round(analysis.get('positive', 0.0), 4),
                    "negative": round(analysis.get('negative', 0.0), 4),
                    "neutral": round(analysis.get('neutral', 0.0), 4)
                }

        return success_response({"results": results})

    except Exception as e:
        logger.error(f"Batch analysis error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)
