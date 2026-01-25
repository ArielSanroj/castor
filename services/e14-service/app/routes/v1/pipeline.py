"""
API v1 Ingestion Pipeline endpoints.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List

logger = logging.getLogger(__name__)

pipeline_v1_bp = Blueprint('pipeline_v1', __name__, url_prefix='/pipeline')


# ============================================================================
# Pydantic Schemas
# ============================================================================

class QueueTableRequest(BaseModel):
    """Queue single table request."""
    department_code: str = Field(..., min_length=2, max_length=2)
    municipality_code: str = Field(..., min_length=3, max_length=5)
    zone_code: str = Field(..., min_length=1, max_length=3)
    station_code: str = Field(..., min_length=1, max_length=4)
    table_code: str = Field(..., min_length=1, max_length=3)
    priority: Optional[str] = Field("normal", pattern="^(urgent|high|normal|low|background)$")


class QueueBulkRequest(BaseModel):
    """Queue multiple items request."""
    department_code: str
    municipality_code: Optional[str] = None
    zone_code: Optional[str] = None
    priority: Optional[str] = "normal"
    confirm: bool = False


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

@pipeline_v1_bp.route('/status', methods=['GET'])
def get_status():
    """
    GET /api/v1/pipeline/status

    Get current pipeline status.

    Response:
        {
            "ok": true,
            "data": {
                "status": "running",
                "workers": { "download": 4, "ocr": 2, "validation": 4 },
                "queues": { "download": 10, "ocr": 5, "validation": 2 },
                "stats": { "processed": 100, "failed": 2 }
            }
        }
    """
    try:
        pipeline = current_app.extensions.get('e14_pipeline')

        if not pipeline:
            return success_response({
                "status": "not_initialized",
                "workers": {},
                "queues": {},
                "stats": {}
            })

        status = pipeline.get_status()

        return success_response({
            "status": status.get("status", "unknown"),
            "workers": status.get("workers", {}),
            "queues": status.get("queues", {}),
            "stats": status.get("stats", {})
        })

    except Exception as e:
        logger.error(f"Status error: {e}")
        return error_response("Internal server error", status_code=500)


@pipeline_v1_bp.route('/start', methods=['POST'])
def start_pipeline():
    """
    POST /api/v1/pipeline/start

    Start the ingestion pipeline.
    """
    try:
        pipeline = current_app.extensions.get('e14_pipeline')

        if not pipeline:
            return error_response("Pipeline not initialized", status_code=503)

        pipeline.start()

        return success_response({
            "status": "started",
            "message": "Pipeline started successfully"
        })

    except Exception as e:
        logger.error(f"Start error: {e}")
        return error_response("Internal server error", status_code=500)


@pipeline_v1_bp.route('/stop', methods=['POST'])
def stop_pipeline():
    """
    POST /api/v1/pipeline/stop

    Stop the ingestion pipeline.
    """
    try:
        pipeline = current_app.extensions.get('e14_pipeline')

        if not pipeline:
            return error_response("Pipeline not initialized", status_code=503)

        pipeline.stop()

        return success_response({
            "status": "stopped",
            "message": "Pipeline stopped successfully"
        })

    except Exception as e:
        logger.error(f"Stop error: {e}")
        return error_response("Internal server error", status_code=500)


@pipeline_v1_bp.route('/queue/table', methods=['POST'])
def queue_table():
    """
    POST /api/v1/pipeline/queue/table

    Queue a single table for processing.

    Request:
        {
            "department_code": "11",
            "municipality_code": "001",
            "zone_code": "01",
            "station_code": "0001",
            "table_code": "001",
            "priority": "normal"
        }
    """
    try:
        try:
            req = QueueTableRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", status_code=400)

        pipeline = current_app.extensions.get('e14_pipeline')
        if not pipeline:
            return error_response("Pipeline not initialized", status_code=503)

        job_id = pipeline.queue_table(
            department=req.department_code,
            municipality=req.municipality_code,
            zone=req.zone_code,
            station=req.station_code,
            table=req.table_code,
            priority=req.priority
        )

        return success_response({
            "job_id": job_id,
            "status": "queued",
            "message": "Table queued for processing"
        }, status_code=202)

    except Exception as e:
        logger.error(f"Queue error: {e}")
        return error_response("Internal server error", status_code=500)


@pipeline_v1_bp.route('/queue/department', methods=['POST'])
def queue_department():
    """
    POST /api/v1/pipeline/queue/department

    Queue all tables in a department.
    Requires confirm=true for large operations.
    """
    try:
        try:
            req = QueueBulkRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error", status_code=400)

        if not req.confirm:
            return error_response(
                "This will queue many tables. Set confirm=true to proceed.",
                status_code=400
            )

        pipeline = current_app.extensions.get('e14_pipeline')
        if not pipeline:
            return error_response("Pipeline not initialized", status_code=503)

        job_ids = pipeline.queue_department(
            department=req.department_code,
            priority=req.priority
        )

        return success_response({
            "jobs_queued": len(job_ids),
            "status": "queued",
            "message": f"Department {req.department_code} queued for processing"
        }, status_code=202)

    except Exception as e:
        logger.error(f"Queue department error: {e}")
        return error_response("Internal server error", status_code=500)


@pipeline_v1_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """
    GET /api/v1/pipeline/jobs/<job_id>

    Get job status.
    """
    try:
        pipeline = current_app.extensions.get('e14_pipeline')
        if not pipeline:
            return error_response("Pipeline not initialized", status_code=503)

        job = pipeline.get_job(job_id)

        if not job:
            return error_response("Job not found", status_code=404)

        return success_response({
            "job_id": job_id,
            "status": job.get("status"),
            "stage": job.get("stage"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "result": job.get("result")
        })

    except Exception as e:
        logger.error(f"Get job error: {e}")
        return error_response("Internal server error", status_code=500)
