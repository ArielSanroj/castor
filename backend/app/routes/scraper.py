"""
API routes for E-14 Scraper control, batch processing, and dashboard integration.

Integrates with:
- E14IngestionPipeline (existing scraper pipeline)
- E14OCRService (OCR processing)
- HITL Review System (low-confidence results)
- Dashboard metrics
"""
import asyncio
import glob
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, g, current_app

from utils.electoral_security import (
    electoral_auth_required,
    require_electoral_role,
    log_electoral_action,
    ElectoralRole,
)
from utils.metrics import (
    get_metrics_registry,
    OCRMetrics,
    ElectoralMetrics,
)

logger = logging.getLogger(__name__)

scraper_bp = Blueprint("scraper", __name__, url_prefix="/api/scraper")

# Default paths
DEFAULT_PDF_DIR = os.path.expanduser("~/actas_e14_masivo/pdfs_congreso_2022")
BATCH_OUTPUT_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/batch_ocr_results")


# ============================================================
# Health Check (Public)
# ============================================================

@scraper_bp.route("/health", methods=["GET"])
def scraper_health():
    """Public health check for scraper module."""
    return jsonify({
        "success": True,
        "service": "scraper",
        "status": "ok",
        "pdf_dir_exists": os.path.isdir(DEFAULT_PDF_DIR),
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================
# Dashboard Status - Main Overview
# ============================================================

@scraper_bp.route("/dashboard", methods=["GET"])
@electoral_auth_required
def get_dashboard():
    """
    Get comprehensive dashboard data for E-14 scraping/processing.

    Returns combined stats from:
    - Scraper task queue (if using distributed scraper)
    - Ingestion pipeline status
    - OCR processing metrics
    - Review queue status
    """
    try:
        registry = get_metrics_registry()

        # Get ingestion pipeline status
        pipeline_stats = _get_pipeline_stats()

        # Get review queue stats
        review_stats = _get_review_stats()

        # Get OCR metrics
        ocr_metrics = {
            "total_processed": registry.get_counter("castor_ocr_requests_total") or 0,
            "errors": registry.get_counter("castor_ocr_errors_total") or 0,
            "avg_confidence": registry.get_histogram_percentile("castor_ocr_confidence", 50) or 0,
            "avg_duration_seconds": registry.get_histogram_percentile("castor_ocr_duration_seconds", 50) or 0,
        }

        # Get scraper task queue stats (if available)
        scraper_stats = _get_scraper_task_stats()

        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "pipeline": pipeline_stats,
                "scraper_queue": scraper_stats,
                "ocr": ocr_metrics,
                "review": review_stats,
            }
        })

    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scraper_bp.route("/status", methods=["GET"])
@electoral_auth_required
def get_status():
    """Get overall scraper/pipeline status."""
    try:
        # Get pipeline status
        from services.e14_ingestion_pipeline import get_ingestion_pipeline
        pipeline = get_ingestion_pipeline()

        # Get scraper queue stats
        scraper_stats = _get_scraper_task_stats()

        return jsonify({
            "success": True,
            "data": {
                "pipeline_status": pipeline.status.value,
                "pipeline_stats": pipeline.get_stats(),
                "scraper_queue": scraper_stats,
            }
        })

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Batch Processing - Process existing PDFs
# ============================================================

@scraper_bp.route("/batch/info", methods=["GET"])
@electoral_auth_required
def get_batch_info():
    """
    Get info about PDFs available for batch processing.

    Query params:
        pdf_dir: Custom PDF directory (default: ~/actas_e14_masivo/pdfs_congreso_2022)
    """
    try:
        pdf_dir = request.args.get("pdf_dir", DEFAULT_PDF_DIR)

        if not os.path.isdir(pdf_dir):
            return jsonify({
                "success": False,
                "error": f"Directory not found: {pdf_dir}",
                "code": "DIR_NOT_FOUND"
            }), 404

        # Count PDFs
        pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
        total_size = sum(os.path.getsize(f) for f in pdf_files)

        # Get sample filenames
        sample_files = [os.path.basename(f) for f in pdf_files[:5]]

        # Estimate cost
        estimated_cost = len(pdf_files) * 0.10  # $0.10 per PDF

        return jsonify({
            "success": True,
            "data": {
                "pdf_dir": pdf_dir,
                "total_pdfs": len(pdf_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "estimated_cost_usd": estimated_cost,
                "sample_files": sample_files,
            }
        })

    except Exception as e:
        logger.error(f"Error getting batch info: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scraper_bp.route("/batch/process", methods=["POST"])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN, ElectoralRole.OPERATOR])
@log_electoral_action("BATCH_PROCESS_E14")
def start_batch_process():
    """
    Start batch processing of E-14 PDFs.

    Request body:
    {
        "pdf_dir": "/path/to/pdfs",  // Optional, defaults to actas_e14_masivo
        "limit": 10,                 // Optional, max PDFs to process
        "dry_run": false,            // Optional, test without processing
        "corporacion_hint": "SENADO" // Optional, hint for OCR
    }

    NOTE: This starts processing in a background thread.
    Use /batch/status to monitor progress.
    """
    try:
        user_id = g.electoral_user_id
        data = request.json or {}

        pdf_dir = data.get("pdf_dir", DEFAULT_PDF_DIR)
        limit = data.get("limit")
        dry_run = data.get("dry_run", False)
        corporacion_hint = data.get("corporacion_hint")

        if not os.path.isdir(pdf_dir):
            return jsonify({
                "success": False,
                "error": f"Directory not found: {pdf_dir}",
                "code": "DIR_NOT_FOUND"
            }), 404

        # Get PDF files
        pdf_files = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
        if limit:
            pdf_files = pdf_files[:limit]

        if not pdf_files:
            return jsonify({
                "success": False,
                "error": "No PDF files found",
                "code": "NO_FILES"
            }), 404

        # Store batch job info
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Start processing in background thread
        import threading

        def process_batch():
            _run_batch_processing(
                batch_id=batch_id,
                pdf_files=pdf_files,
                dry_run=dry_run,
                corporacion_hint=corporacion_hint,
                user_id=user_id,
            )

        if not dry_run:
            thread = threading.Thread(target=process_batch, daemon=True)
            thread.start()

        return jsonify({
            "success": True,
            "data": {
                "batch_id": batch_id,
                "total_pdfs": len(pdf_files),
                "dry_run": dry_run,
                "estimated_cost_usd": len(pdf_files) * 0.10,
                "message": "Batch processing started" if not dry_run else "Dry run - no processing",
                "status_endpoint": f"/api/scraper/batch/status/{batch_id}",
            }
        })

    except Exception as e:
        logger.error(f"Error starting batch process: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scraper_bp.route("/batch/status/<batch_id>", methods=["GET"])
@electoral_auth_required
def get_batch_status(batch_id: str):
    """Get status of a batch processing job."""
    try:
        # Check for progress file
        progress_file = os.path.join(BATCH_OUTPUT_DIR, f"{batch_id}_progress.json")

        if not os.path.exists(progress_file):
            return jsonify({
                "success": False,
                "error": "Batch not found",
                "code": "NOT_FOUND"
            }), 404

        import json
        with open(progress_file, 'r') as f:
            progress = json.load(f)

        return jsonify({
            "success": True,
            "data": progress
        })

    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scraper_bp.route("/batch/results", methods=["GET"])
@electoral_auth_required
def get_batch_results():
    """
    Get list of batch processing results.

    Query params:
        limit: Max results (default 50)
    """
    try:
        limit = request.args.get("limit", 50, type=int)

        if not os.path.isdir(BATCH_OUTPUT_DIR):
            return jsonify({
                "success": True,
                "data": {"results": [], "total": 0}
            })

        # Find all result files
        result_files = glob.glob(os.path.join(BATCH_OUTPUT_DIR, "*_result.json"))
        result_files = sorted(result_files, key=os.path.getmtime, reverse=True)[:limit]

        results = []
        for rf in result_files:
            try:
                import json
                with open(rf, 'r') as f:
                    data = json.load(f)
                results.append({
                    "filename": os.path.basename(rf),
                    "extraction_id": data.get("context", {}).get("extraction_id"),
                    "confidence": data.get("meta", {}).get("overall_confidence"),
                    "processed_at": datetime.fromtimestamp(os.path.getmtime(rf)).isoformat(),
                })
            except Exception:
                pass

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "total": len(result_files),
            }
        })

    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Process Single PDF
# ============================================================

@scraper_bp.route("/process-single", methods=["POST"])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.ADMIN])
@log_electoral_action("PROCESS_SINGLE_E14")
def process_single_pdf():
    """
    Process a single PDF file from the filesystem.

    Request body:
    {
        "file_path": "/path/to/file.pdf",
        "corporacion_hint": "SENADO"  // Optional
    }
    """
    try:
        user_id = g.electoral_user_id
        data = request.json or {}

        file_path = data.get("file_path")
        corporacion_hint = data.get("corporacion_hint")

        if not file_path:
            return jsonify({
                "success": False,
                "error": "file_path is required",
                "code": "MISSING_FILE_PATH"
            }), 400

        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "error": f"File not found: {file_path}",
                "code": "FILE_NOT_FOUND"
            }), 404

        # Process with OCR
        from services.e14_ocr_service import get_e14_ocr_service

        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()

        ocr_service = get_e14_ocr_service()
        start_time = time.time()

        payload = ocr_service.process_pdf_v2(
            pdf_bytes=pdf_bytes,
            corporacion_hint=corporacion_hint,
        )

        processing_time = time.time() - start_time

        # Check if needs review
        needs_review_count = sum(1 for f in payload.ocr_fields if f.needs_review)
        overall_confidence = payload.meta.get('overall_confidence', 0.0) if payload.meta else 0.0

        # Create HITL review item if low confidence
        review_item_id = None
        if overall_confidence < 0.7 or needs_review_count > 0:
            review_item_id = _create_review_item(payload, file_path)

        # Index to RAG
        _index_to_rag(payload, user_id)

        return jsonify({
            "success": True,
            "data": {
                "extraction_id": payload.context.extraction_id if payload.context else None,
                "confidence": overall_confidence,
                "needs_review_count": needs_review_count,
                "review_item_id": review_item_id,
                "processing_time_seconds": round(processing_time, 2),
                "header": {
                    "corporacion": payload.header.corporacion if payload.header else None,
                    "dept_code": payload.header.dept_code if payload.header else None,
                    "muni_code": payload.header.muni_code if payload.header else None,
                }
            }
        })

    except Exception as e:
        logger.error(f"Error processing single PDF: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Integration with Existing Pipeline
# ============================================================

@scraper_bp.route("/pipeline/queue-from-folder", methods=["POST"])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action("QUEUE_FOLDER_TO_PIPELINE")
def queue_folder_to_pipeline():
    """
    Queue PDFs from a folder to the existing ingestion pipeline.

    Request body:
    {
        "pdf_dir": "/path/to/pdfs",
        "limit": 100,
        "priority": "NORMAL"  // URGENT, HIGH, NORMAL, LOW
    }
    """
    try:
        from services.e14_ingestion_pipeline import get_ingestion_pipeline, PipelineStatus
        from services.parallel_ocr import JobPriority

        data = request.json or {}
        pdf_dir = data.get("pdf_dir", DEFAULT_PDF_DIR)
        limit = data.get("limit", 100)
        priority_str = data.get("priority", "NORMAL")

        try:
            priority = JobPriority[priority_str.upper()]
        except KeyError:
            priority = JobPriority.NORMAL

        if not os.path.isdir(pdf_dir):
            return jsonify({
                "success": False,
                "error": f"Directory not found: {pdf_dir}",
            }), 404

        pipeline = get_ingestion_pipeline()

        if pipeline.status != PipelineStatus.RUNNING:
            return jsonify({
                "success": False,
                "error": "Pipeline is not running. Start it first via /api/electoral/ingestion/pipeline/start",
                "code": "PIPELINE_NOT_RUNNING"
            }), 400

        # Get PDFs and queue them
        pdf_files = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))[:limit]
        queued = 0

        for pdf_path in pdf_files:
            try:
                # Parse metadata from filename
                metadata = _parse_pdf_filename(os.path.basename(pdf_path))
                if metadata:
                    pipeline.queue_pdf_file(
                        pdf_path=pdf_path,
                        dept_code=metadata.get("dept_code", "00"),
                        muni_code=metadata.get("muni_code", "000"),
                        priority=priority,
                    )
                    queued += 1
            except Exception as e:
                logger.warning(f"Failed to queue {pdf_path}: {e}")

        return jsonify({
            "success": True,
            "data": {
                "queued": queued,
                "total_files": len(pdf_files),
                "pipeline_status": pipeline.status.value,
            }
        })

    except Exception as e:
        logger.error(f"Error queuing folder: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# CAPTCHA Management
# ============================================================

@scraper_bp.route("/captcha/balance", methods=["GET"])
@electoral_auth_required
def get_captcha_balance():
    """Get 2Captcha account balance."""
    try:
        from services.scraper.captcha_solver import CaptchaSolver

        solver = CaptchaSolver()
        if not solver.api_key:
            return jsonify({
                "success": True,
                "data": {
                    "configured": False,
                    "balance": 0.0,
                    "message": "2Captcha API key not configured"
                }
            })

        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        balance = loop.run_until_complete(solver.get_balance())
        loop.close()

        return jsonify({
            "success": True,
            "data": {
                "configured": True,
                "balance": balance,
                "low_balance_warning": balance < 2.0,
            }
        })

    except Exception as e:
        logger.error(f"Error getting captcha balance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Metrics for Dashboard
# ============================================================

@scraper_bp.route("/metrics", methods=["GET"])
@electoral_auth_required
def get_metrics():
    """Get scraper/OCR metrics for dashboard charts."""
    try:
        registry = get_metrics_registry()

        return jsonify({
            "success": True,
            "data": {
                "ocr": {
                    "total_processed": registry.get_counter("castor_ocr_requests_total") or 0,
                    "total_errors": registry.get_counter("castor_ocr_errors_total") or 0,
                    "avg_duration_seconds": registry.get_histogram_percentile("castor_ocr_duration_seconds", 50) or 0,
                    "p95_duration_seconds": registry.get_histogram_percentile("castor_ocr_duration_seconds", 95) or 0,
                    "avg_confidence": registry.get_histogram_percentile("castor_ocr_confidence", 50) or 0,
                },
                "ingestion": {
                    "total_received": registry.get_counter("castor_ingestion_requests_total") or 0,
                    "total_errors": registry.get_counter("castor_ingestion_errors_total") or 0,
                    "avg_duration_seconds": registry.get_histogram_percentile("castor_ingestion_duration_seconds", 50) or 0,
                },
                "validation": {
                    "total_validations": registry.get_counter("castor_validations_total") or 0,
                    "total_failures": registry.get_counter("castor_validation_failures_total") or 0,
                },
                "review": _get_review_stats(),
            }
        })

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Helper Functions
# ============================================================

def _get_pipeline_stats() -> Dict[str, Any]:
    """Get stats from the ingestion pipeline."""
    try:
        from services.e14_ingestion_pipeline import get_ingestion_pipeline
        pipeline = get_ingestion_pipeline()
        return {
            "status": pipeline.status.value,
            **pipeline.get_stats()
        }
    except Exception as e:
        logger.warning(f"Could not get pipeline stats: {e}")
        return {"status": "unavailable", "error": str(e)}


def _get_review_stats() -> Dict[str, Any]:
    """Get stats from the HITL review queue."""
    try:
        from services.hitl_review import ReviewQueue
        queue = ReviewQueue()
        return queue.get_stats()
    except Exception as e:
        logger.warning(f"Could not get review stats: {e}")
        return {"status": "unavailable", "error": str(e)}


def _get_scraper_task_stats() -> Dict[str, Any]:
    """Get stats from the scraper task queue (if using SQLAlchemy models)."""
    try:
        # Try to get from database if models exist
        from models.scraper import ScraperTask
        from sqlalchemy import func

        # This would need a session - simplified version
        return {
            "available": True,
            "note": "Use /api/scraper/tasks for detailed task info"
        }
    except ImportError:
        return {"available": False}
    except Exception as e:
        return {"available": False, "error": str(e)}


def _parse_pdf_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Parse E-14 metadata from filename.

    Format: {MESA_ID}_E14_{CORP}_X_{DEPT}_{MUNI}_{...}.pdf
    Example: 2043318_E14_SEN_X_01_001_003_XX_02_026_X_XXX.pdf
    """
    try:
        parts = filename.replace('.pdf', '').split('_')
        if len(parts) < 6:
            return None

        return {
            "mesa_id": parts[0],
            "corporacion": parts[2],  # SEN or CAM
            "dept_code": parts[4],
            "muni_code": parts[5],
            "zone_code": parts[6] if len(parts) > 6 else "",
        }
    except Exception:
        return None


def _run_batch_processing(
    batch_id: str,
    pdf_files: List[str],
    dry_run: bool,
    corporacion_hint: Optional[str],
    user_id: str,
):
    """Run batch processing in background thread."""
    import json

    progress_file = os.path.join(BATCH_OUTPUT_DIR, f"{batch_id}_progress.json")
    Path(BATCH_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    progress = {
        "batch_id": batch_id,
        "status": "running",
        "total": len(pdf_files),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "errors": [],
    }

    def save_progress():
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

    save_progress()

    if dry_run:
        progress["status"] = "completed_dry_run"
        progress["completed_at"] = datetime.utcnow().isoformat()
        save_progress()
        return

    from services.e14_ocr_service import get_e14_ocr_service
    ocr_service = get_e14_ocr_service()

    for i, pdf_path in enumerate(pdf_files):
        try:
            filename = os.path.basename(pdf_path)
            metadata = _parse_pdf_filename(filename)

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # Determine corporacion hint
            corp_hint = corporacion_hint
            if not corp_hint and metadata:
                corp_hint = "SENADO" if metadata.get("corporacion") == "SEN" else "CAMARA"

            # Process
            payload = ocr_service.process_pdf_v2(
                pdf_bytes=pdf_bytes,
                corporacion_hint=corp_hint,
            )

            # Save result
            result_file = os.path.join(BATCH_OUTPUT_DIR, f"{filename.replace('.pdf', '')}_result.json")
            with open(result_file, 'w') as f:
                json.dump(payload.dict(by_alias=True, exclude_none=True), f, ensure_ascii=False, indent=2, default=str)

            # Index to RAG
            _index_to_rag(payload, user_id)

            progress["success"] += 1

        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            progress["failed"] += 1
            progress["errors"].append({
                "file": os.path.basename(pdf_path),
                "error": str(e),
            })

        progress["processed"] += 1
        save_progress()

        # Rate limiting
        time.sleep(1)

    progress["status"] = "completed"
    progress["completed_at"] = datetime.utcnow().isoformat()
    save_progress()


def _create_review_item(payload, file_path: str) -> Optional[str]:
    """Create HITL review item for low-confidence extraction."""
    try:
        from services.hitl_review import (
            ReviewQueue,
            create_review_item_for_low_confidence,
        )

        queue = ReviewQueue()
        review_item = create_review_item_for_low_confidence(
            extraction_id=payload.context.extraction_id if payload.context else "unknown",
            mesa_id=payload.header.table_number if payload.header else "unknown",
            cells=[f for f in payload.ocr_fields if f.needs_review],
            overall_confidence=payload.meta.get('overall_confidence', 0.0) if payload.meta else 0.0,
        )

        if review_item:
            queue.add_item(review_item)
            return review_item.review_id

    except Exception as e:
        logger.warning(f"Could not create review item: {e}")

    return None


def _index_to_rag(payload, user_id: str):
    """Index E-14 extraction to RAG."""
    try:
        from services.rag_service import get_rag_service

        rag = get_rag_service()
        if rag and payload.context:
            extraction_dict = payload.dict(by_alias=True, exclude_none=True)
            rag.index_e14_form(
                extraction_id=payload.context.extraction_id,
                extraction_data=extraction_dict,
                metadata={
                    "user_id": user_id,
                    "source": "scraper_batch",
                }
            )
    except Exception as e:
        logger.warning(f"Could not index to RAG: {e}")
