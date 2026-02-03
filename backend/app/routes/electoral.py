"""
Routes para el producto de Control Electoral.
API para procesamiento de E-14 con OCR y validación.

SEGURIDAD:
- Todos los endpoints requieren autenticación JWT
- Rate limiting por requests Y por costo
- Validación de PDFs antes de procesar
- Logging de auditoría

MÉTRICAS (QAS):
- L1: Latencia de ingesta
- L2: Latencia de OCR
- I2: Validaciones
- Sec1: Seguridad
"""
import logging
import time
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app, g
from pydantic import ValidationError

from app.schemas.e14 import (
    E14ProcessRequest,
    E14ProcessResponse,
    E14BatchProcessRequest,
    E14BatchProcessResponse,
)
from services.e14_ocr_service import (
    get_e14_ocr_service,
    save_payload_v2_json,
    convert_v1_to_v2,
    SourceType,
)
from utils.rate_limiter import limiter
from utils.pdf_validator import validate_pdf_file, validate_pdf_url, validate_pdf_bytes
from utils.electoral_security import (
    electoral_auth_required,
    require_electoral_role,
    cost_limit_check,
    log_electoral_action,
    get_cost_tracker,
    get_request_metadata,
    ElectoralRole,
)
from utils.metrics import (
    get_metrics_registry,
    get_metrics_endpoint,
    OCRMetrics,
    ValidationMetrics,
    ElectoralMetrics,
    SecurityMetrics,
    DashboardMetrics,
)

logger = logging.getLogger(__name__)

electoral_bp = Blueprint('electoral', __name__)


# ============================================================
# Health check (público)
# ============================================================

@electoral_bp.route('/health', methods=['GET'])
def health_check():
    """Health check del servicio electoral."""
    return jsonify({
        "status": "healthy",
        "service": "electoral-control",
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================
# Procesamiento de E-14 (PROTEGIDO)
# ============================================================

@electoral_bp.route('/e14/process', methods=['POST'])
@limiter.limit("20 per hour; 100 per day")  # Rate limit por requests
@electoral_auth_required
@cost_limit_check()  # Verifica límite de costo ($5/día default)
@log_electoral_action('PROCESS_E14')
def process_e14():
    """
    Procesa un E-14 con OCR y extrae datos estructurados.

    REQUIERE: Autenticación JWT

    Request body (JSON):
    {
        "file_url": "https://...",  // URL del PDF
        "election_id": "optional",
        "force_reprocess": false
    }

    O multipart/form-data con archivo PDF.

    LÍMITES:
    - 20 requests/hora
    - 100 requests/día
    - $5 USD/día en costo de API
    """
    start_time = time.time()
    registry = get_metrics_registry()
    copy_type = "UNKNOWN"
    department = "00"
    status_code = 200

    try:
        user_id = g.electoral_user_id

        # Verificar si es upload de archivo o JSON con URL
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Upload de archivo
            if 'file' not in request.files:
                status_code = 400
                registry.inc("castor_ingestion_errors_total", 1, {"error_type": "MISSING_FILE"})
                return jsonify({
                    "success": False,
                    "error": "No se proporcionó archivo PDF",
                    "code": "MISSING_FILE"
                }), 400

            file = request.files['file']

            # VALIDACIÓN DE PDF
            validation = validate_pdf_file(file)
            if not validation.is_valid:
                status_code = 400
                logger.warning(f"PDF validation failed for user {user_id}: {validation.error_message}")
                registry.inc("castor_ingestion_errors_total", 1, {"error_type": "INVALID_PDF"})
                return jsonify({
                    "success": False,
                    "error": validation.error_message,
                    "code": "INVALID_PDF"
                }), 400

            pdf_bytes = validation.pdf_bytes
            file_url = None

            # Métrica de tamaño de archivo
            registry.observe("castor_ingestion_file_size_bytes", len(pdf_bytes), {"copy_type": "upload"})
            logger.info(f"User {user_id} uploading PDF: {validation.page_count} pages, {validation.file_size_mb:.2f}MB")

        else:
            # JSON con URL
            try:
                req = E14ProcessRequest(**request.json)
                file_url = req.file_url
            except ValidationError as e:
                status_code = 400
                registry.inc("castor_ingestion_errors_total", 1, {"error_type": "VALIDATION_ERROR"})
                return jsonify({
                    "success": False,
                    "error": f"Datos inválidos: {e.errors()}",
                    "code": "VALIDATION_ERROR"
                }), 400

            if not file_url:
                status_code = 400
                registry.inc("castor_ingestion_errors_total", 1, {"error_type": "MISSING_INPUT"})
                return jsonify({
                    "success": False,
                    "error": "Debe proporcionar file_url o archivo PDF",
                    "code": "MISSING_INPUT"
                }), 400

            # VALIDACIÓN DE PDF desde URL
            validation = validate_pdf_url(file_url)
            if not validation.is_valid:
                status_code = 400
                logger.warning(f"PDF URL validation failed for user {user_id}: {validation.error_message}")
                registry.inc("castor_ingestion_errors_total", 1, {"error_type": "INVALID_PDF"})
                return jsonify({
                    "success": False,
                    "error": validation.error_message,
                    "code": "INVALID_PDF"
                }), 400

            pdf_bytes = validation.pdf_bytes
            registry.observe("castor_ingestion_file_size_bytes", len(pdf_bytes), {"copy_type": "url"})
            logger.info(f"User {user_id} processing URL: {validation.page_count} pages, {validation.file_size_mb:.2f}MB")

        # Obtener servicio OCR
        ocr_service = get_e14_ocr_service()

        # Medir tiempo de OCR
        ocr_start = time.time()
        extraction = ocr_service.process_pdf(pdf_bytes=pdf_bytes)
        ocr_duration = time.time() - ocr_start

        # Extraer metadata para métricas
        copy_type = extraction.header.copy_type.value
        department = extraction.header.departamento_code
        corporacion = extraction.header.corporacion.value

        # Métricas de OCR
        registry.observe("castor_ocr_duration_seconds", ocr_duration, {
            "template_version": "v1",
            "corporacion": corporacion,
            "status": "success"
        })
        registry.observe("castor_ocr_confidence", extraction.overall_confidence, {
            "field_type": "overall",
            "corporacion": corporacion
        })

        # Métricas de campos que necesitan revisión
        if extraction.fields_needing_review > 0:
            OCRMetrics.track_needs_review("multiple", "low_confidence")

        # Validar extracción
        validation_report = ocr_service.validate_extraction(extraction)

        # Métricas de validación
        for v in validation_report.validations:
            ValidationMetrics.track_validation(
                rule_key=v.rule_id,
                passed=v.passed,
                severity=v.severity.value
            )

        # Métricas electorales
        ElectoralMetrics.track_form_received(
            department=department,
            municipality=extraction.header.municipio_code,
            corporacion=corporacion,
            copy_type=copy_type
        )
        ElectoralMetrics.track_form_processed(
            department=department,
            municipality=extraction.header.municipio_code,
            corporacion=corporacion,
            status="success"
        )

        # Construir respuesta
        response = E14ProcessResponse(
            success=True,
            extraction_id=extraction.extraction_id,
            mesa_id=extraction.header.mesa_id,
            total_sufragantes=extraction.nivelacion.total_sufragantes_e11,
            total_urna=extraction.nivelacion.total_votos_urna,
            total_computado=extraction.total_computado,
            delta=extraction.nivelacion.total_votos_urna - extraction.total_computado,
            validation_passed=validation_report.all_passed,
            alerts_count=len(validation_report.alerts_generated),
            fields_needing_review=extraction.fields_needing_review,
            extraction=extraction,
            validation_report=validation_report
        )

        # =====================================================================
        # INDEXAR E-14 EN RAG AUTOMÁTICAMENTE
        # =====================================================================
        try:
            from services.rag_service import get_rag_service
            rag = get_rag_service()
            if rag:
                # Convertir extraction a dict para indexar
                extraction_dict = extraction.dict() if hasattr(extraction, 'dict') else extraction.model_dump()
                docs_indexed = rag.index_e14_form(
                    extraction_id=extraction.extraction_id,
                    extraction_data=extraction_dict,
                    metadata={
                        "user_id": user_id,
                        "source": "api_process",
                        "validation_passed": validation_report.all_passed
                    }
                )
                logger.info(f"E-14 {extraction.extraction_id} indexed to RAG: {docs_indexed} documents")
        except Exception as rag_error:
            # No fallar el request si RAG falla, solo loggear
            logger.warning(f"Failed to index E-14 to RAG: {rag_error}")

        logger.info(f"E-14 processed successfully by user {user_id}: {extraction.extraction_id}")
        return jsonify(response.dict())

    except Exception as e:
        status_code = 500
        logger.error(f"Error procesando E-14: {e}", exc_info=True)
        registry.inc("castor_ingestion_errors_total", 1, {"error_type": type(e).__name__})
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "PROCESSING_ERROR"
        }), 500

    finally:
        # Métricas de latencia total de ingesta (QAS L1)
        duration = time.time() - start_time
        registry.observe("castor_ingestion_duration_seconds", duration, {
            "status_code": str(status_code),
            "copy_type": copy_type,
            "department": department
        })
        registry.inc("castor_ingestion_requests_total", 1, {
            "status_code": str(status_code),
            "copy_type": copy_type,
            "department": department
        })


@electoral_bp.route('/e14/process-url', methods=['POST'])
@limiter.limit("20 per hour; 100 per day")
@electoral_auth_required
@cost_limit_check()
@log_electoral_action('PROCESS_E14_URL')
def process_e14_url():
    """
    Procesa un E-14 desde URL (endpoint simplificado).

    REQUIERE: Autenticación JWT

    Request body:
    {
        "url": "https://..."
    }
    """
    start_time = time.time()
    registry = get_metrics_registry()
    status_code = 200
    department = "00"
    corporacion = "UNKNOWN"

    try:
        user_id = g.electoral_user_id
        data = request.json or {}
        url = data.get('url')

        if not url:
            status_code = 400
            registry.inc("castor_ingestion_errors_total", 1, {"error_type": "MISSING_URL"})
            return jsonify({
                "success": False,
                "error": "Se requiere 'url' en el body",
                "code": "MISSING_URL"
            }), 400

        # VALIDACIÓN DE PDF
        validation = validate_pdf_url(url)
        if not validation.is_valid:
            status_code = 400
            logger.warning(f"PDF validation failed for user {user_id}: {validation.error_message}")
            registry.inc("castor_ingestion_errors_total", 1, {"error_type": "INVALID_PDF"})
            return jsonify({
                "success": False,
                "error": validation.error_message,
                "code": "INVALID_PDF"
            }), 400

        # Procesar con métricas de OCR
        ocr_start = time.time()
        ocr_service = get_e14_ocr_service()
        extraction = ocr_service.process_pdf(pdf_bytes=validation.pdf_bytes)
        ocr_duration = time.time() - ocr_start

        # Extraer metadata
        department = extraction.header.departamento_code
        corporacion = extraction.header.corporacion.value

        # Métricas OCR
        registry.observe("castor_ocr_duration_seconds", ocr_duration, {
            "template_version": "v1",
            "corporacion": corporacion,
            "status": "success"
        })

        validation_report = ocr_service.validate_extraction(extraction)

        # Métricas electorales
        ElectoralMetrics.track_form_received(
            department=department,
            municipality=extraction.header.municipio_code,
            corporacion=corporacion,
            copy_type=extraction.header.copy_type.value
        )
        ElectoralMetrics.track_form_processed(
            department=department,
            municipality=extraction.header.municipio_code,
            corporacion=corporacion,
            status="success"
        )

        # =====================================================================
        # INDEXAR E-14 EN RAG AUTOMÁTICAMENTE
        # =====================================================================
        rag_docs_indexed = 0
        try:
            from services.rag_service import get_rag_service
            rag = get_rag_service()
            if rag:
                extraction_dict = extraction.dict() if hasattr(extraction, 'dict') else extraction.model_dump()
                rag_docs_indexed = rag.index_e14_form(
                    extraction_id=extraction.extraction_id,
                    extraction_data=extraction_dict,
                    metadata={
                        "user_id": user_id,
                        "source": "api_process_url",
                        "validation_passed": validation_report.all_passed
                    }
                )
                logger.info(f"E-14 {extraction.extraction_id} indexed to RAG: {rag_docs_indexed} documents")
        except Exception as rag_error:
            logger.warning(f"Failed to index E-14 to RAG: {rag_error}")

        # Respuesta simplificada
        return jsonify({
            "success": True,
            "extraction_id": extraction.extraction_id,
            "mesa_id": extraction.header.mesa_id,
            "header": {
                "corporacion": extraction.header.corporacion.value,
                "departamento": f"{extraction.header.departamento_code} - {extraction.header.departamento_name}",
                "municipio": f"{extraction.header.municipio_code} - {extraction.header.municipio_name}",
                "zona": extraction.header.zona,
                "puesto": extraction.header.puesto,
                "mesa": extraction.header.mesa,
                "copy_type": extraction.header.copy_type.value
            },
            "nivelacion": {
                "sufragantes_e11": extraction.nivelacion.total_sufragantes_e11,
                "votos_urna": extraction.nivelacion.total_votos_urna,
                "votos_incinerados": extraction.nivelacion.total_votos_incinerados
            },
            "resultados": {
                "total_partidos": extraction.total_votos_partidos,
                "votos_blanco": extraction.votos_especiales.votos_blanco,
                "votos_nulos": extraction.votos_especiales.votos_nulos,
                "votos_no_marcados": extraction.votos_especiales.votos_no_marcados,
                "total_computado": extraction.total_computado
            },
            "partidos": [
                {
                    "codigo": p.party_code,
                    "nombre": p.party_name,
                    "tipo_lista": p.list_type.value,
                    "votos_total": p.total_votos,
                    "votos_agrupacion": p.votos_agrupacion,
                    "votos_candidatos": len(p.votos_candidatos)
                }
                for p in extraction.partidos
            ],
            "validacion": {
                "passed": validation_report.all_passed,
                "critical": validation_report.critical_failures,
                "high": validation_report.high_failures,
                "medium": validation_report.medium_failures,
                "delta": extraction.nivelacion.total_votos_urna - extraction.total_computado,
                "alertas": validation_report.alerts_generated
            },
            "metadata": {
                "confidence": extraction.overall_confidence,
                "fields_needing_review": extraction.fields_needing_review,
                "pages": extraction.total_pages,
                "processing_time_ms": extraction.processing_time_ms,
                "processed_by": user_id
            }
        })

    except Exception as e:
        status_code = 500
        logger.error(f"Error procesando E-14 desde URL: {e}", exc_info=True)
        registry.inc("castor_ingestion_errors_total", 1, {"error_type": type(e).__name__})
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "PROCESSING_ERROR"
        }), 500

    finally:
        # Métricas de latencia (QAS L1)
        duration = time.time() - start_time
        registry.observe("castor_ingestion_duration_seconds", duration, {
            "status_code": str(status_code),
            "department": department
        })
        registry.inc("castor_ingestion_requests_total", 1, {
            "status_code": str(status_code),
            "department": department
        })


# ============================================================
# Procesamiento V2 - Payload estructurado para BD v2
# ============================================================

@electoral_bp.route('/e14/process-v2', methods=['POST'])
@limiter.limit("20 per hour; 100 per day")
@electoral_auth_required
@cost_limit_check()
@log_electoral_action('PROCESS_E14_V2')
def process_e14_v2():
    """
    Procesa un E-14 y genera payload v2 estructurado.

    REQUIERE: Autenticación JWT

    Request body (JSON):
    {
        "url": "https://...",           // URL del PDF
        "source_type": "WITNESS_UPLOAD" // WITNESS_UPLOAD|REGISTRADURIA|MANUAL_ENTRY
    }

    O multipart/form-data con archivo PDF.

    Response: E14PayloadV2 completo con:
    - pipeline_context
    - input_document con páginas
    - ocr_fields con raw_mark
    - normalized_tallies
    - validations
    - db_write_plan
    """
    start_time = time.time()
    registry = get_metrics_registry()
    copy_type = "UNKNOWN"
    department = "00"
    municipality = "000"
    corporacion = "CONSULTA"
    status_code = 200

    try:
        user_id = g.electoral_user_id
        pdf_bytes = None
        source_type_str = "WITNESS_UPLOAD"

        # Verificar si es upload de archivo o JSON con URL
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Upload de archivo
            if 'file' not in request.files:
                return jsonify({
                    "success": False,
                    "error": "No se proporcionó archivo PDF",
                    "code": "MISSING_FILE"
                }), 400

            file = request.files['file']
            source_type_str = request.form.get('source_type', 'WITNESS_UPLOAD')

            # VALIDACIÓN DE PDF
            validation = validate_pdf_file(file)
            if not validation.is_valid:
                return jsonify({
                    "success": False,
                    "error": validation.error_message,
                    "code": "INVALID_PDF"
                }), 400

            pdf_bytes = validation.pdf_bytes
            logger.info(f"User {user_id} uploading PDF v2: {validation.page_count} pages")

        else:
            # JSON con URL
            data = request.json or {}
            url = data.get('url')
            source_type_str = data.get('source_type', 'WITNESS_UPLOAD')

            if not url:
                return jsonify({
                    "success": False,
                    "error": "Se requiere 'url' en el body",
                    "code": "MISSING_URL"
                }), 400

            # VALIDACIÓN DE PDF desde URL
            validation = validate_pdf_url(url)
            if not validation.is_valid:
                return jsonify({
                    "success": False,
                    "error": validation.error_message,
                    "code": "INVALID_PDF"
                }), 400

            pdf_bytes = validation.pdf_bytes
            logger.info(f"User {user_id} processing URL v2: {validation.page_count} pages")

        # Parsear source_type
        try:
            source_type = SourceType[source_type_str.upper()]
        except KeyError:
            source_type = SourceType.WITNESS_UPLOAD

        # Obtener servicio OCR y procesar con v2
        ocr_service = get_e14_ocr_service()
        payload_v2 = ocr_service.process_pdf_v2(
            pdf_bytes=pdf_bytes,
            source_type=source_type
        )

        # Extraer información para métricas
        header = payload_v2.document_header_extracted
        department = header.dept_code
        municipality = header.muni_code
        corporacion = header.corporacion.value
        copy_type = payload_v2.input_document.copy_type.value

        # Registrar métricas electorales
        ElectoralMetrics.track_form_received(
            department=department,
            municipality=municipality,
            corporacion=corporacion,
            copy_type=copy_type
        )
        ElectoralMetrics.track_form_processed(
            department=department,
            municipality=municipality,
            corporacion=corporacion,
            status="OCR_COMPLETED"
        )

        # Retornar payload v2 completo
        return jsonify({
            "success": True,
            "payload": payload_v2.dict(by_alias=True, exclude_none=True),
            "summary": {
                "mesa_id": payload_v2.document_header_extracted.mesa_id,
                "corporacion": payload_v2.document_header_extracted.corporacion.value,
                "total_pages": payload_v2.input_document.total_pages,
                "ocr_fields_count": len(payload_v2.ocr_fields),
                "fields_needing_review": sum(1 for f in payload_v2.ocr_fields if f.needs_review),
                "validations_passed": all(v.passed for v in payload_v2.validations)
            }
        })

    except Exception as e:
        status_code = 500
        logger.error(f"Error procesando E-14 v2: {e}", exc_info=True)
        registry.inc("castor_ingestion_errors_total", 1, {"error_type": type(e).__name__})
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "PROCESSING_ERROR"
        }), 500

    finally:
        # Registrar métricas de ingesta
        duration = time.time() - start_time
        labels = {
            "copy_type": copy_type,
            "department": department,
            "corporacion": corporacion,
            "status_code": str(status_code)
        }
        registry.observe("castor_ingestion_duration_seconds", duration, labels)
        registry.inc("castor_ingestion_requests_total", 1, labels)


@electoral_bp.route('/e14/convert-to-v2', methods=['POST'])
@limiter.limit("50 per hour")
@electoral_auth_required
@log_electoral_action('CONVERT_TO_V2')
def convert_to_v2():
    """
    Convierte un resultado de extracción v1 a payload v2.

    REQUIERE: Autenticación JWT

    Request body:
    {
        "extraction_v1": { ... }  // E14ExtractionResult completo
    }

    Útil para migrar datos existentes al nuevo formato.
    """
    try:
        from app.schemas.e14 import E14ExtractionResult

        data = request.json or {}
        extraction_data = data.get('extraction_v1')

        if not extraction_data:
            return jsonify({
                "success": False,
                "error": "Se requiere 'extraction_v1' con el resultado de extracción",
                "code": "MISSING_INPUT"
            }), 400

        # Parsear el resultado v1
        extraction_v1 = E14ExtractionResult(**extraction_data)

        # Convertir a v2
        payload_v2 = convert_v1_to_v2(extraction_v1)

        return jsonify({
            "success": True,
            "payload": payload_v2.dict(by_alias=True, exclude_none=True),
            "converted_from": "v1"
        })

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": f"Datos de extracción inválidos: {e.errors()}",
            "code": "VALIDATION_ERROR"
        }), 400
    except Exception as e:
        logger.error(f"Error convirtiendo a v2: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "CONVERSION_ERROR"
        }), 500


@electoral_bp.route('/e14/extract-fields', methods=['POST'])
@limiter.limit("30 per hour")
@electoral_auth_required
@cost_limit_check()
@log_electoral_action('EXTRACT_FIELDS')
def extract_e14_fields():
    """
    Extrae solo los campos específicos de un E-14 (útil para debugging).

    REQUIERE: Autenticación JWT

    Request body:
    {
        "url": "https://...",
        "fields": ["header", "nivelacion", "partidos", "votos_especiales"]
    }
    """
    try:
        user_id = g.electoral_user_id
        data = request.json or {}
        url = data.get('url')
        fields = data.get('fields', ['header', 'nivelacion', 'partidos', 'votos_especiales'])

        if not url:
            return jsonify({
                "success": False,
                "error": "Se requiere 'url'",
                "code": "MISSING_URL"
            }), 400

        # Validar PDF
        validation = validate_pdf_url(url)
        if not validation.is_valid:
            return jsonify({
                "success": False,
                "error": validation.error_message,
                "code": "INVALID_PDF"
            }), 400

        ocr_service = get_e14_ocr_service()
        extraction = ocr_service.process_pdf(pdf_bytes=validation.pdf_bytes)

        result = {
            "success": True,
            "extraction_id": extraction.extraction_id,
            "processed_by": user_id
        }

        if 'header' in fields:
            result['header'] = extraction.header.dict()

        if 'nivelacion' in fields:
            result['nivelacion'] = extraction.nivelacion.dict()

        if 'partidos' in fields:
            result['partidos'] = [p.dict() for p in extraction.partidos]

        if 'votos_especiales' in fields:
            result['votos_especiales'] = extraction.votos_especiales.dict()

        if 'constancias' in fields and extraction.constancias:
            result['constancias'] = extraction.constancias.dict()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error extrayendo campos E-14: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "PROCESSING_ERROR"
        }), 500


# ============================================================
# Validación (PROTEGIDO)
# ============================================================

@electoral_bp.route('/e14/validate', methods=['POST'])
@limiter.limit("60 per hour")  # Sin costo de API, más permisivo
@electoral_auth_required
@log_electoral_action('VALIDATE_E14')
def validate_e14():
    """
    Valida un E-14 ya extraído.

    REQUIERE: Autenticación JWT

    Request body: E14ExtractionResult JSON
    """
    try:
        from app.schemas.e14 import E14ExtractionResult

        data = request.json
        extraction = E14ExtractionResult(**data)

        ocr_service = get_e14_ocr_service()
        validation = ocr_service.validate_extraction(extraction)

        return jsonify(validation.dict())

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": f"Datos inválidos: {e.errors()}",
            "code": "VALIDATION_ERROR"
        }), 400
    except Exception as e:
        logger.error(f"Error validando E-14: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "PROCESSING_ERROR"
        }), 500


# ============================================================
# Estadísticas y uso (PROTEGIDO)
# ============================================================

@electoral_bp.route('/stats', methods=['GET'])
@electoral_auth_required
def get_stats():
    """
    Obtiene estadísticas generales del procesamiento.

    REQUIERE: Autenticación JWT
    """
    user_id = g.electoral_user_id
    tracker = get_cost_tracker()

    # Uso del usuario actual
    user_usage_24h = tracker.get_usage(user_id, hours=24)
    user_usage_1h = tracker.get_usage(user_id, hours=1)

    return jsonify({
        "success": True,
        "user_usage": {
            "last_hour": {
                "cost": f"${user_usage_1h['cost']:.2f}",
                "operations": user_usage_1h['operations'],
                "limit": "$2.00"
            },
            "last_24h": {
                "cost": f"${user_usage_24h['cost']:.2f}",
                "operations": user_usage_24h['operations'],
                "limit": "$5.00"
            }
        },
        "global_stats": tracker.get_all_stats(),
        "message": "Estadísticas de BD no implementadas aún"
    })


@electoral_bp.route('/usage', methods=['GET'])
@electoral_auth_required
def get_usage():
    """
    Obtiene el uso de API del usuario actual.

    REQUIERE: Autenticación JWT
    """
    user_id = g.electoral_user_id
    tracker = get_cost_tracker()

    usage_24h = tracker.get_usage(user_id, hours=24)
    usage_1h = tracker.get_usage(user_id, hours=1)

    # Calcular cuántas operaciones más puede hacer
    remaining_hourly = max(0, 2.00 - usage_1h['cost']) / 0.10
    remaining_daily = max(0, 5.00 - usage_24h['cost']) / 0.10

    return jsonify({
        "success": True,
        "user_id": user_id,
        "usage": {
            "hourly": {
                "cost": usage_1h['cost'],
                "operations": usage_1h['operations'],
                "limit": 2.00,
                "remaining_operations": int(remaining_hourly)
            },
            "daily": {
                "cost": usage_24h['cost'],
                "operations": usage_24h['operations'],
                "limit": 5.00,
                "remaining_operations": int(remaining_daily)
            }
        },
        "cost_per_operation": 0.10
    })


# ============================================================
# Test endpoint (público para verificación)
# ============================================================

@electoral_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba para verificar que el servicio está funcionando."""
    try:
        # Verificar que el servicio OCR se puede inicializar
        ocr_service = get_e14_ocr_service()

        return jsonify({
            "success": True,
            "message": "Servicio Electoral Control funcionando",
            "ocr_model": ocr_service.model,
            "security": {
                "authentication": "JWT required for processing",
                "rate_limit": "20/hour, 100/day",
                "cost_limit": "$5/day per user"
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Error inicializando servicio OCR - verificar ANTHROPIC_API_KEY"
        }), 500


# ============================================================
# Admin endpoints (solo ADMIN)
# ============================================================

@electoral_bp.route('/admin/usage-stats', methods=['GET'])
@require_electoral_role([ElectoralRole.ADMIN])
def admin_usage_stats():
    """
    Estadísticas de uso global (solo admin).

    REQUIERE: Rol ADMIN
    """
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "global_stats": tracker.get_all_stats(),
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================
# Métricas (público para Prometheus/monitoreo)
# ============================================================

@electoral_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Endpoint de métricas para Prometheus/monitoreo.

    Retorna métricas en formato texto compatible con Prometheus.

    Métricas incluidas (según QAS):
    - castor_ingestion_duration_seconds (L1)
    - castor_ingestion_requests_total
    - castor_ingestion_errors_total
    - castor_ocr_duration_seconds (L2)
    - castor_ocr_confidence
    - castor_validation_executions_total (I2)
    - castor_forms_received_total
    - castor_forms_processed_total
    """
    handler = get_metrics_endpoint()
    return handler()


@electoral_bp.route('/metrics/json', methods=['GET'])
def metrics_json():
    """
    Endpoint de métricas en formato JSON (para dashboards custom).
    """
    registry = get_metrics_registry()
    return jsonify(registry.export_all())


@electoral_bp.route('/metrics/slo', methods=['GET'])
def metrics_slo():
    """
    Endpoint de SLOs actuales.

    Retorna estado de SLOs según las métricas recolectadas.
    """
    registry = get_metrics_registry()

    # Calcular SLOs
    ingestion_p95 = registry.get_histogram_percentile("castor_ingestion_duration_seconds", 95)
    ocr_p95 = registry.get_histogram_percentile("castor_ocr_duration_seconds", 95)

    total_requests = sum(
        v for k, v in registry._counters.items()
        if k.startswith("castor_ingestion_requests_total")
    )
    total_errors = sum(
        v for k, v in registry._counters.items()
        if k.startswith("castor_ingestion_errors_total")
    )
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

    return jsonify({
        "success": True,
        "slos": {
            "ingestion_latency_p95": {
                "current": f"{ingestion_p95:.3f}s" if ingestion_p95 else "N/A",
                "target": "2.0s",
                "status": "OK" if ingestion_p95 and ingestion_p95 <= 2.0 else "BREACH" if ingestion_p95 else "NO_DATA"
            },
            "ocr_latency_p95": {
                "current": f"{ocr_p95:.1f}s" if ocr_p95 else "N/A",
                "target": "45.0s",
                "status": "OK" if ocr_p95 and ocr_p95 <= 45.0 else "BREACH" if ocr_p95 else "NO_DATA"
            },
            "ingestion_error_rate": {
                "current": f"{error_rate:.2f}%",
                "target": "0.5%",
                "status": "OK" if error_rate <= 0.5 else "BREACH"
            }
        },
        "totals": {
            "requests": total_requests,
            "errors": total_errors
        },
        "timestamp": datetime.utcnow().isoformat()
    })
