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


@e14_v1_bp.route('/process-enhanced', methods=['POST'])
def process_e14_enhanced():
    """
    POST /api/v1/e14/process-enhanced

    Enhanced E-14 processing with:
    - QR as primary key (polling_table_id)
    - Image preprocessing (contrast, brightness, sharpening)
    - Cell-by-cell detection
    - QR vs OCR validation

    Request:
        {
            "url": "https://example.com/e14.pdf"
        }
        OR
        multipart/form-data with 'file' field

    Response:
        {
            "ok": true,
            "data": {
                "polling_table_id": "27-001-01-01-006",
                "qr_confidence": 0.95,
                "qr_ocr_match": true,
                "header": {...},
                "candidates": [...],
                "specials": {...},
                "total_mesa": 217,
                "sum_validation": true,
                "needs_review_count": 0,
                "alerts": []
            }
        }
    """
    try:
        ocr_service = current_app.extensions.get('e14_ocr_service')
        if not ocr_service:
            return error_response("OCR service not available", status_code=503)

        # Handle file upload or URL
        pdf_data = None
        source = None

        if request.content_type and 'multipart/form-data' in request.content_type:
            # File upload
            if 'file' not in request.files:
                return error_response("No file provided")
            file = request.files['file']
            if file.filename == '':
                return error_response("Empty filename")
            pdf_data = file.read()
            source = file.filename
        else:
            # JSON with URL
            data = request.get_json()
            if not data or 'url' not in data:
                return error_response("Missing 'url' or file upload")
            # Download PDF from URL
            import httpx
            try:
                with httpx.Client(timeout=60) as client:
                    response = client.get(data['url'])
                    response.raise_for_status()
                    pdf_data = response.content
                    source = data['url']
            except Exception as e:
                return error_response(f"Failed to download PDF: {str(e)}", status_code=422)

        # Process with enhanced pipeline
        result = ocr_service.process_pdf_v2(pdf_bytes=pdf_data)

        # Extract key data for response
        header = result.document_header_extracted
        polling_table_id = header.mesa_id if header else None

        # Check QR vs OCR match
        qr_ocr_match = True
        alerts = []
        if result.meta:
            if result.meta.get('qr_ocr_mismatches'):
                qr_ocr_match = False
                alerts.append({
                    "type": "QR_OCR_MISMATCH",
                    "severity": "HIGH",
                    "details": result.meta.get('qr_ocr_mismatches')
                })

        # Build candidates list
        candidates = []
        for tally in result.normalized_tallies:
            if hasattr(tally, 'political_group_code'):
                for entry in tally.tallies:
                    candidates.append({
                        "party_code": tally.political_group_code,
                        "votes": entry.votes,
                        "type": entry.subject_type.value if hasattr(entry.subject_type, 'value') else str(entry.subject_type)
                    })

        # Build specials
        specials = {"blank": 0, "null": 0, "unmarked": 0}
        for tally in result.normalized_tallies:
            if hasattr(tally, 'specials'):
                for entry in tally.specials:
                    stype = entry.subject_type.value if hasattr(entry.subject_type, 'value') else str(entry.subject_type)
                    if stype == 'BLANK':
                        specials['blank'] = entry.votes
                    elif stype == 'NULL':
                        specials['null'] = entry.votes
                    elif stype == 'UNMARKED':
                        specials['unmarked'] = entry.votes

        # Sum validation
        sum_valid = any(v.passed for v in result.validations if v.rule_key == 'SUM_EQUALS_TOTAL')

        # Needs review count
        needs_review = sum(1 for f in result.ocr_fields if f.needs_review)

        return success_response({
            "polling_table_id": polling_table_id,
            "qr_confidence": result.meta.get('qr_confidence', 0.0) if result.meta else 0.0,
            "qr_ocr_match": qr_ocr_match,
            "header": {
                "dept_code": header.dept_code if header else None,
                "dept_name": header.dept_name if header else None,
                "muni_code": header.muni_code if header else None,
                "muni_name": header.muni_name if header else None,
                "zone_code": header.zone_code if header else None,
                "station_code": header.station_code if header else None,
                "table_number": header.table_number if header else None,
                "copy_type": result.input_document.copy_type.value if result.input_document else None,
                "corporacion": header.corporacion.value if header and header.corporacion else None
            },
            "nivelacion": {
                "sufragantes_e11": next((f.value_int for f in result.ocr_fields if f.field_key == 'TOTAL_SUFRAGANTES_E11'), 0),
                "votos_urna": next((f.value_int for f in result.ocr_fields if f.field_key == 'TOTAL_VOTOS_URNA'), 0)
            },
            "candidates": candidates,
            "specials": specials,
            "total_mesa": next((f.value_int for f in result.ocr_fields if f.field_key == 'TOTAL_VOTOS_MESA'), 0),
            "sum_validation": sum_valid,
            "needs_review_count": needs_review,
            "processing_time_ms": result.meta.get('processing_time_ms', 0) if result.meta else 0,
            "alerts": alerts,
            "source": source
        })

    except Exception as e:
        logger.error(f"Enhanced E-14 processing error: {e}", exc_info=True)
        return error_response(f"Processing error: {str(e)}", status_code=500)


@e14_v1_bp.route('/upload', methods=['POST'])
def upload_e14():
    """
    POST /api/v1/e14/upload

    Upload and process E-14 PDF file directly.

    Request: multipart/form-data with 'file' field

    Response: Same as /process-enhanced
    """
    # Redirect to enhanced processing
    return process_e14_enhanced()
