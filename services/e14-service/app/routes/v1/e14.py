"""
API v1 E-14 Processing endpoints.
Versioned endpoints with standardized response format.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

e14_v1_bp = Blueprint('e14_v1', __name__, url_prefix='/e14')


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ProcessE14Request(BaseModel):
    """E-14 processing request."""
    url: HttpUrl
    options: Optional[Dict[str, Any]] = None
    copy_type: Optional[str] = Field(None, pattern="^(claveros|delegados|transmision)$")


class ProcessE14UrlRequest(BaseModel):
    """Simple URL-based processing request."""
    url: HttpUrl


# ============================================================================
# Response Helpers
# ============================================================================

def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, details: Optional[dict] = None, status_code: int = 400):
    response = {"ok": False, "error": error}
    if details:
        response["details"] = details
    return jsonify(response), status_code


# ============================================================================
# Endpoints
# ============================================================================

@e14_v1_bp.route('/process', methods=['POST'])
def process_e14():
    """
    POST /api/v1/e14/process

    Process E-14 form with OCR.

    Request:
        {
            "url": "https://example.com/e14.pdf",
            "options": {
                "validate": true,
                "extract_cells": true
            },
            "copy_type": "claveros"
        }

    Response:
        {
            "ok": true,
            "data": {
                "extraction": { ... },
                "validation": { ... },
                "confidence": 0.95
            }
        }
    """
    try:
        # Validate request
        try:
            req = ProcessE14Request(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", {"fields": e.errors()})

        # Get OCR service
        ocr_service = current_app.extensions.get('e14_ocr_service')
        if not ocr_service:
            return error_response("OCR service not available", status_code=503)

        # Process E-14
        result = ocr_service.process_url(
            str(req.url),
            options=req.options,
            copy_type=req.copy_type
        )

        if result.get("error"):
            return error_response(result["error"], status_code=422)

        return success_response({
            "extraction": result.get("extraction"),
            "validation": result.get("validation"),
            "confidence": result.get("confidence", 0.0),
            "needs_review": result.get("needs_review", [])
        })

    except Exception as e:
        logger.error(f"E-14 processing error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@e14_v1_bp.route('/process-url', methods=['POST'])
def process_e14_simple():
    """
    POST /api/v1/e14/process-url

    Simple URL-based E-14 processing.

    Request:
        {
            "url": "https://example.com/e14.pdf"
        }
    """
    try:
        try:
            req = ProcessE14UrlRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", {"fields": e.errors()})

        ocr_service = current_app.extensions.get('e14_ocr_service')
        if not ocr_service:
            return error_response("OCR service not available", status_code=503)

        result = ocr_service.process_url(str(req.url))

        return success_response(result)

    except Exception as e:
        logger.error(f"E-14 processing error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@e14_v1_bp.route('/validate', methods=['POST'])
def validate_e14():
    """
    POST /api/v1/e14/validate

    Validate pre-extracted E-14 data.

    Request:
        {
            "extraction": { ... }
        }

    Response:
        {
            "ok": true,
            "data": {
                "valid": true,
                "errors": [],
                "warnings": []
            }
        }
    """
    try:
        data = request.get_json()
        if not data or "extraction" not in data:
            return error_response("Missing extraction data")

        ocr_service = current_app.extensions.get('e14_ocr_service')
        if not ocr_service:
            return error_response("OCR service not available", status_code=503)

        validation = ocr_service.validate(data["extraction"])

        return success_response({
            "valid": validation.get("valid", False),
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", [])
        })

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@e14_v1_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    GET /api/v1/e14/stats

    Get E-14 processing statistics.
    """
    try:
        # TODO: Implement stats from database
        return success_response({
            "total_processed": 0,
            "success_rate": 0.0,
            "avg_confidence": 0.0,
            "needs_review_count": 0
        })

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return error_response("Internal server error", status_code=500)
