"""
API Routes para E-14 Ingestion Pipeline.

Endpoints para:
- Control del pipeline (start, stop, pause)
- Encolar trabajos de descarga
- Monitorear progreso
- Ver estadísticas
"""
import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, g

from utils.electoral_security import (
    electoral_auth_required,
    require_electoral_role,
    log_electoral_action,
    ElectoralRole,
)
from utils.metrics import get_metrics_registry
from services.e14_ingestion_pipeline import (
    get_ingestion_pipeline,
    E14IngestionPipeline,
    PipelineConfig,
    PipelineStatus,
)
from services.e14_scraper import ElectionType, CopyType
from services.parallel_ocr import JobPriority

logger = logging.getLogger(__name__)

ingestion_bp = Blueprint('ingestion', __name__)


# ============================================================
# Control del Pipeline
# ============================================================

@ingestion_bp.route('/pipeline/status', methods=['GET'])
@electoral_auth_required
def get_pipeline_status():
    """Obtiene el estado actual del pipeline."""
    pipeline = get_ingestion_pipeline()
    return jsonify({
        'success': True,
        'status': pipeline.status.value,
        'stats': pipeline.get_stats()
    })


@ingestion_bp.route('/pipeline/start', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('START_PIPELINE')
def start_pipeline():
    """
    Inicia el pipeline de ingesta.

    Body (opcional):
    {
        "election_type": "PRESIDENCIA_1V_2022",
        "copy_type": "CLAVEROS",
        "download_workers": 2,
        "ocr_workers": 4
    }
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status == PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline ya está corriendo',
            'code': 'ALREADY_RUNNING'
        }), 400

    # Configurar si se proporcionaron opciones
    data = request.json or {}

    if data:
        election_type_str = data.get('election_type', 'PRESIDENCIA_1V_2022')
        try:
            election_type = ElectionType[election_type_str]
        except KeyError:
            election_type = ElectionType.PRESIDENCIA_1V_2022

        copy_type_str = data.get('copy_type', 'CLAVEROS')
        try:
            copy_type = CopyType[copy_type_str.upper()]
        except KeyError:
            copy_type = CopyType.CLAVEROS

        pipeline.config.election_type = election_type
        pipeline.config.copy_type = copy_type
        pipeline.config.download_workers = data.get('download_workers', 2)
        pipeline.config.ocr_workers = data.get('ocr_workers', 4)

    try:
        pipeline.start()
        return jsonify({
            'success': True,
            'message': 'Pipeline iniciado',
            'status': pipeline.status.value
        })
    except Exception as e:
        logger.error(f"Error starting pipeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'START_FAILED'
        }), 500


@ingestion_bp.route('/pipeline/stop', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('STOP_PIPELINE')
def stop_pipeline():
    """Detiene el pipeline de ingesta."""
    pipeline = get_ingestion_pipeline()
    pipeline.stop()

    return jsonify({
        'success': True,
        'message': 'Pipeline detenido',
        'status': pipeline.status.value
    })


@ingestion_bp.route('/pipeline/pause', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('PAUSE_PIPELINE')
def pause_pipeline():
    """Pausa el pipeline de ingesta."""
    pipeline = get_ingestion_pipeline()
    pipeline.pause()

    return jsonify({
        'success': True,
        'message': 'Pipeline pausado',
        'status': pipeline.status.value
    })


@ingestion_bp.route('/pipeline/resume', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('RESUME_PIPELINE')
def resume_pipeline():
    """Reanuda el pipeline de ingesta."""
    pipeline = get_ingestion_pipeline()
    pipeline.resume()

    return jsonify({
        'success': True,
        'message': 'Pipeline reanudado',
        'status': pipeline.status.value
    })


# ============================================================
# Encolar trabajos
# ============================================================

@ingestion_bp.route('/queue/table', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.ADMIN])
@log_electoral_action('QUEUE_TABLE')
def queue_table():
    """
    Encola una mesa específica para procesamiento.

    Body:
    {
        "dept_code": "11",
        "muni_code": "001",
        "zone_code": "01",
        "station_code": "0001",
        "table_number": 1,
        "priority": "NORMAL"  // URGENT, HIGH, NORMAL, LOW
    }
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline no está corriendo',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    data = request.json or {}

    required_fields = ['dept_code', 'muni_code', 'zone_code', 'station_code', 'table_number']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'Campo requerido: {field}',
                'code': 'MISSING_FIELD'
            }), 400

    # Parsear prioridad
    priority_str = data.get('priority', 'NORMAL')
    try:
        priority = JobPriority[priority_str.upper()]
    except KeyError:
        priority = JobPriority.NORMAL

    job_id = pipeline.queue_table(
        dept_code=data['dept_code'],
        muni_code=data['muni_code'],
        zone_code=data['zone_code'],
        station_code=data['station_code'],
        table_number=int(data['table_number']),
        priority=priority
    )

    return jsonify({
        'success': True,
        'job_id': job_id,
        'mesa_id': f"{data['dept_code']}-{data['muni_code']}-{data['zone_code']}-{data['station_code']}-{int(data['table_number']):03d}"
    })


@ingestion_bp.route('/queue/station', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.ADMIN])
@log_electoral_action('QUEUE_STATION')
def queue_station():
    """
    Encola todas las mesas de un puesto de votación.

    Body:
    {
        "dept_code": "11",
        "muni_code": "001",
        "zone_code": "01",
        "station_code": "0001"
    }
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline no está corriendo',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    data = request.json or {}

    required_fields = ['dept_code', 'muni_code', 'zone_code', 'station_code']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'Campo requerido: {field}',
                'code': 'MISSING_FIELD'
            }), 400

    try:
        job_ids = pipeline.queue_station(
            dept_code=data['dept_code'],
            muni_code=data['muni_code'],
            zone_code=data['zone_code'],
            station_code=data['station_code']
        )

        return jsonify({
            'success': True,
            'jobs_queued': len(job_ids),
            'job_ids': job_ids[:10],  # Primeros 10 para no sobrecargar respuesta
            'message': f'Encoladas {len(job_ids)} mesas'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'QUEUE_FAILED'
        }), 500


@ingestion_bp.route('/queue/zone', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.ADMIN])
@log_electoral_action('QUEUE_ZONE')
def queue_zone():
    """
    Encola todas las mesas de una zona.

    Body:
    {
        "dept_code": "11",
        "muni_code": "001",
        "zone_code": "01"
    }
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline no está corriendo',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    data = request.json or {}

    try:
        job_ids = pipeline.queue_zone(
            dept_code=data['dept_code'],
            muni_code=data['muni_code'],
            zone_code=data['zone_code']
        )

        return jsonify({
            'success': True,
            'jobs_queued': len(job_ids),
            'message': f'Encoladas {len(job_ids)} mesas de zona {data["zone_code"]}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'QUEUE_FAILED'
        }), 500


@ingestion_bp.route('/queue/municipality', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('QUEUE_MUNICIPALITY')
def queue_municipality():
    """
    Encola todas las mesas de un municipio.

    Body:
    {
        "dept_code": "11",
        "muni_code": "001"
    }
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline no está corriendo',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    data = request.json or {}

    try:
        job_ids = pipeline.queue_municipality(
            dept_code=data['dept_code'],
            muni_code=data['muni_code']
        )

        return jsonify({
            'success': True,
            'jobs_queued': len(job_ids),
            'message': f'Encoladas {len(job_ids)} mesas del municipio {data["muni_code"]}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'QUEUE_FAILED'
        }), 500


@ingestion_bp.route('/queue/department', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.ADMIN])
@log_electoral_action('QUEUE_DEPARTMENT')
def queue_department():
    """
    Encola todas las mesas de un departamento.

    Body:
    {
        "dept_code": "11"
    }

    ADVERTENCIA: Esto puede encolar miles de mesas.
    """
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline no está corriendo',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    data = request.json or {}

    if 'dept_code' not in data:
        return jsonify({
            'success': False,
            'error': 'Campo requerido: dept_code',
            'code': 'MISSING_FIELD'
        }), 400

    # Confirmar operación masiva
    if not data.get('confirm', False):
        return jsonify({
            'success': False,
            'error': 'Esta operación puede encolar miles de mesas. Agrega "confirm": true para proceder.',
            'code': 'CONFIRMATION_REQUIRED'
        }), 400

    try:
        job_ids = pipeline.queue_department(dept_code=data['dept_code'])

        return jsonify({
            'success': True,
            'jobs_queued': len(job_ids),
            'message': f'Encoladas {len(job_ids)} mesas del departamento {data["dept_code"]}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'QUEUE_FAILED'
        }), 500


# ============================================================
# Consulta de jobs
# ============================================================

@ingestion_bp.route('/job/<job_id>', methods=['GET'])
@electoral_auth_required
def get_job_status(job_id: str):
    """Obtiene el estado de un job específico."""
    pipeline = get_ingestion_pipeline()
    job_status = pipeline.get_job_status(job_id)

    if not job_status:
        return jsonify({
            'success': False,
            'error': 'Job no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    return jsonify({
        'success': True,
        'job': job_status
    })


@ingestion_bp.route('/jobs', methods=['GET'])
@electoral_auth_required
def list_jobs():
    """
    Lista jobs del pipeline.

    Query params:
        - status: Filtrar por estado
        - stage: Filtrar por etapa
        - dept: Filtrar por departamento
        - limit: Máximo de resultados (default 100)
    """
    pipeline = get_ingestion_pipeline()

    status_filter = request.args.get('status')
    stage_filter = request.args.get('stage')
    dept_filter = request.args.get('dept')
    limit = int(request.args.get('limit', 100))

    jobs = list(pipeline.jobs.values())

    # Aplicar filtros
    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]
    if stage_filter:
        jobs = [j for j in jobs if j.stage.value == stage_filter]
    if dept_filter:
        jobs = [j for j in jobs if j.dept_code == dept_filter]

    # Limitar
    jobs = jobs[:limit]

    return jsonify({
        'success': True,
        'total': len(pipeline.jobs),
        'returned': len(jobs),
        'jobs': [
            {
                'job_id': j.job_id,
                'mesa_id': j.mesa_id,
                'stage': j.stage.value,
                'status': j.status,
                'created_at': j.created_at.isoformat(),
                'error': j.error
            }
            for j in jobs
        ]
    })


# ============================================================
# Datos de referencia
# ============================================================

@ingestion_bp.route('/departments', methods=['GET'])
@electoral_auth_required
def list_departments():
    """Lista los departamentos disponibles."""
    pipeline = get_ingestion_pipeline()

    if pipeline.scraper:
        departments = pipeline.scraper.get_departments()
    else:
        # Lista estática si el scraper no está inicializado
        from services.e14_scraper import E14Scraper, ElectionType
        temp_scraper = E14Scraper(ElectionType.PRESIDENCIA_1V_2022)
        departments = temp_scraper.get_departments()

    return jsonify({
        'success': True,
        'departments': departments
    })


@ingestion_bp.route('/municipalities/<dept_code>', methods=['GET'])
@electoral_auth_required
def list_municipalities(dept_code: str):
    """Lista los municipios de un departamento."""
    pipeline = get_ingestion_pipeline()

    if pipeline.status != PipelineStatus.RUNNING:
        return jsonify({
            'success': False,
            'error': 'Pipeline debe estar corriendo para consultar municipios',
            'code': 'PIPELINE_NOT_RUNNING'
        }), 400

    municipalities = pipeline.scraper.get_municipalities(dept_code)

    return jsonify({
        'success': True,
        'dept_code': dept_code,
        'municipalities': municipalities
    })


# ============================================================
# Métricas
# ============================================================

@ingestion_bp.route('/metrics', methods=['GET'])
@electoral_auth_required
def get_ingestion_metrics():
    """Obtiene métricas del pipeline de ingesta."""
    pipeline = get_ingestion_pipeline()
    registry = get_metrics_registry()

    stats = pipeline.get_stats()

    # Agregar métricas de Prometheus
    stats['metrics'] = {
        'ocr_duration_p50': registry.get_histogram_percentile('castor_ocr_duration_seconds', 50),
        'ocr_duration_p95': registry.get_histogram_percentile('castor_ocr_duration_seconds', 95),
        'anthropic_cost_total': registry.get_counter('castor_anthropic_cost_usd'),
        'forms_processed_total': registry.get_counter('castor_forms_processed_total'),
    }

    return jsonify({
        'success': True,
        'stats': stats
    })
