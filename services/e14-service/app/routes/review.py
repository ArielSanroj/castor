"""
API Routes para Human-in-the-Loop (HITL) Review System.

Endpoints para:
- Obtener cola de revisión
- Asignar items de revisión
- Aplicar correcciones
- Ver estadísticas de revisión
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
from utils.metrics import get_metrics_registry, ValidationMetrics
from services.hitl_review import (
    ReviewQueue,
    ReviewItem,
    ReviewStatus,
    ReviewPriority,
    ReviewReason,
    apply_correction,
    generate_audit_log_entry,
    prepare_review_ui_data,
    collect_training_feedback,
)

logger = logging.getLogger(__name__)

review_bp = Blueprint('review', __name__)

# Cola de revisión global (en producción usar Redis o BD)
_review_queue: Optional[ReviewQueue] = None


def get_review_queue() -> ReviewQueue:
    """Obtiene la cola de revisión global."""
    global _review_queue
    if _review_queue is None:
        _review_queue = ReviewQueue()
    return _review_queue


# ============================================================
# Endpoints de Cola de Revisión
# ============================================================

@review_bp.route('/queue', methods=['GET'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
def get_queue():
    """
    Obtiene el estado de la cola de revisión.

    Query params:
        - priority: Filtrar por prioridad (CRITICAL, HIGH, MEDIUM, LOW)
        - status: Filtrar por estado (PENDING, IN_PROGRESS, COMPLETED)
        - limit: Máximo de items (default 50)
    """
    queue = get_review_queue()

    priority_filter = request.args.get('priority')
    status_filter = request.args.get('status')
    limit = int(request.args.get('limit', 50))

    items = queue.items

    # Aplicar filtros
    if priority_filter:
        try:
            priority = ReviewPriority[priority_filter.upper()]
            items = [i for i in items if i.priority == priority]
        except KeyError:
            pass

    if status_filter:
        try:
            status = ReviewStatus[status_filter.upper()]
            items = [i for i in items if i.status == status]
        except KeyError:
            pass

    # Limitar resultados
    items = items[:limit]

    return jsonify({
        'success': True,
        'stats': queue.get_stats(),
        'items': [
            {
                'review_id': item.review_id,
                'mesa_id': item.mesa_id,
                'priority': item.priority.name,
                'reason': item.reason.name,
                'reason_details': item.reason_details,
                'status': item.status.name,
                'cells_count': len(item.cells),
                'department': item.department,
                'municipality': item.municipality,
                'corporacion': item.corporacion,
                'created_at': item.created_at.isoformat(),
                'assigned_to': item.assigned_to
            }
            for item in items
        ]
    })


@review_bp.route('/queue/stats', methods=['GET'])
@electoral_auth_required
def get_queue_stats():
    """Obtiene estadísticas de la cola de revisión."""
    queue = get_review_queue()
    registry = get_metrics_registry()

    stats = queue.get_stats()

    # Agregar métricas de tiempo promedio
    stats['metrics'] = {
        'review_duration_avg': registry.get_histogram_percentile(
            'castor_review_duration_seconds', 50
        ),
        'corrections_total': registry.get_counter('castor_corrections_total')
    }

    return jsonify({
        'success': True,
        'stats': stats
    })


@review_bp.route('/queue/next', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
@log_electoral_action('CLAIM_REVIEW')
def claim_next_review():
    """
    Reclama el siguiente item de revisión pendiente.

    El item se asigna al usuario actual y cambia a IN_PROGRESS.
    """
    queue = get_review_queue()
    user_id = g.electoral_user_id

    item = queue.get_next(reviewer_id=user_id)

    if not item:
        return jsonify({
            'success': False,
            'error': 'No hay items pendientes de revisión',
            'code': 'QUEUE_EMPTY'
        }), 404

    return jsonify({
        'success': True,
        'review': prepare_review_ui_data(item)
    })


# ============================================================
# Endpoints de Items Individuales
# ============================================================

@review_bp.route('/item/<review_id>', methods=['GET'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
def get_review_item(review_id: str):
    """Obtiene los detalles de un item de revisión específico."""
    queue = get_review_queue()

    item = next((i for i in queue.items if i.review_id == review_id), None)

    if not item:
        return jsonify({
            'success': False,
            'error': 'Item de revisión no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    return jsonify({
        'success': True,
        'review': prepare_review_ui_data(item)
    })


@review_bp.route('/item/<review_id>/assign', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
@log_electoral_action('ASSIGN_REVIEW')
def assign_review(review_id: str):
    """
    Asigna un item de revisión a un usuario.

    Body:
    {
        "user_id": "usuario a asignar" (opcional, default: usuario actual)
    }
    """
    queue = get_review_queue()
    data = request.json or {}

    item = next((i for i in queue.items if i.review_id == review_id), None)

    if not item:
        return jsonify({
            'success': False,
            'error': 'Item de revisión no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    if item.status != ReviewStatus.PENDING:
        return jsonify({
            'success': False,
            'error': f'Item no está pendiente (estado: {item.status.name})',
            'code': 'INVALID_STATUS'
        }), 400

    assignee = data.get('user_id', g.electoral_user_id)
    item.assigned_to = assignee
    item.assigned_at = datetime.utcnow()
    item.status = ReviewStatus.IN_PROGRESS
    item.updated_at = datetime.utcnow()

    logger.info(f"Review {review_id} assigned to {assignee}")

    return jsonify({
        'success': True,
        'review_id': review_id,
        'assigned_to': assignee
    })


@review_bp.route('/item/<review_id>/correct', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
@log_electoral_action('APPLY_CORRECTION')
def apply_corrections(review_id: str):
    """
    Aplica correcciones a un item de revisión.

    Body:
    {
        "corrections": [
            {
                "cell_id": "id de la celda",
                "new_value": 123,
                "notes": "razón de la corrección"
            }
        ],
        "resolution_notes": "notas generales de resolución"
    }
    """
    queue = get_review_queue()
    registry = get_metrics_registry()
    data = request.json or {}

    item = next((i for i in queue.items if i.review_id == review_id), None)

    if not item:
        return jsonify({
            'success': False,
            'error': 'Item de revisión no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    if item.status not in [ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS]:
        return jsonify({
            'success': False,
            'error': f'Item no puede ser corregido (estado: {item.status.name})',
            'code': 'INVALID_STATUS'
        }), 400

    corrections_data = data.get('corrections', [])
    if not corrections_data:
        return jsonify({
            'success': False,
            'error': 'No se proporcionaron correcciones',
            'code': 'NO_CORRECTIONS'
        }), 400

    # Aplicar correcciones
    reviewer_id = g.electoral_user_id
    reviewer_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    applied_corrections = apply_correction(
        review_item=item,
        corrections=corrections_data,
        reviewer_id=reviewer_id,
        reviewer_ip=reviewer_ip
    )

    # Generar audit log entries
    audit_entries = [generate_audit_log_entry(c) for c in applied_corrections]

    # Actualizar resolución
    item.resolution = "CORRECTED"
    item.resolution_notes = data.get('resolution_notes', '')

    # Registrar métricas
    registry.inc('castor_corrections_total', len(applied_corrections))
    for corr in applied_corrections:
        ValidationMetrics.track_validation(
            rule_key='MANUAL_CORRECTION',
            passed=True,
            severity='INFO'
        )

    # Recolectar feedback para training
    training_feedback = collect_training_feedback(applied_corrections, item.cells)

    logger.info(f"Applied {len(applied_corrections)} corrections to review {review_id}")

    return jsonify({
        'success': True,
        'review_id': review_id,
        'corrections_applied': len(applied_corrections),
        'audit_entries': audit_entries,
        'training_feedback_count': len(training_feedback)
    })


@review_bp.route('/item/<review_id>/escalate', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
@log_electoral_action('ESCALATE_REVIEW')
def escalate_review(review_id: str):
    """
    Escala un item de revisión a un nivel superior.

    Body:
    {
        "reason": "razón de la escalación"
    }
    """
    queue = get_review_queue()
    data = request.json or {}

    item = next((i for i in queue.items if i.review_id == review_id), None)

    if not item:
        return jsonify({
            'success': False,
            'error': 'Item de revisión no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    item.status = ReviewStatus.ESCALATED
    item.updated_at = datetime.utcnow()
    item.resolution = "ESCALATED"
    item.resolution_notes = data.get('reason', 'Escalado por el revisor')

    # Aumentar prioridad
    if item.priority.value > ReviewPriority.CRITICAL.value:
        new_priority = ReviewPriority(item.priority.value - 1)
        item.priority = new_priority

    logger.info(f"Review {review_id} escalated by {g.electoral_user_id}")

    return jsonify({
        'success': True,
        'review_id': review_id,
        'new_status': item.status.name,
        'new_priority': item.priority.name
    })


@review_bp.route('/item/<review_id>/reject', methods=['POST'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
@log_electoral_action('REJECT_REVIEW')
def reject_review(review_id: str):
    """
    Rechaza un item de revisión (formulario inválido/ilegible).

    Body:
    {
        "reason": "razón del rechazo"
    }
    """
    queue = get_review_queue()
    data = request.json or {}

    item = next((i for i in queue.items if i.review_id == review_id), None)

    if not item:
        return jsonify({
            'success': False,
            'error': 'Item de revisión no encontrado',
            'code': 'NOT_FOUND'
        }), 404

    item.status = ReviewStatus.REJECTED
    item.completed_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    item.resolution = "REJECTED"
    item.resolution_notes = data.get('reason', 'Rechazado por el revisor')

    logger.info(f"Review {review_id} rejected by {g.electoral_user_id}")

    return jsonify({
        'success': True,
        'review_id': review_id,
        'status': 'REJECTED'
    })


# ============================================================
# Endpoints de Búsqueda
# ============================================================

@review_bp.route('/search', methods=['GET'])
@electoral_auth_required
@require_electoral_role([ElectoralRole.OPERATOR, ElectoralRole.VALIDATOR, ElectoralRole.ADMIN])
def search_reviews():
    """
    Busca items de revisión.

    Query params:
        - mesa_id: Buscar por mesa
        - department: Buscar por departamento
        - municipality: Buscar por municipio
        - form_instance_id: Buscar por ID de formulario
    """
    queue = get_review_queue()

    mesa_id = request.args.get('mesa_id')
    department = request.args.get('department')
    municipality = request.args.get('municipality')
    form_instance_id = request.args.get('form_instance_id')

    items = queue.items

    if mesa_id:
        items = [i for i in items if i.mesa_id == mesa_id]
    if department:
        items = [i for i in items if i.department == department]
    if municipality:
        items = [i for i in items if i.municipality == municipality]
    if form_instance_id:
        items = [i for i in items if i.form_instance_id == form_instance_id]

    return jsonify({
        'success': True,
        'count': len(items),
        'items': [
            {
                'review_id': item.review_id,
                'mesa_id': item.mesa_id,
                'priority': item.priority.name,
                'reason': item.reason.name,
                'status': item.status.name,
                'created_at': item.created_at.isoformat()
            }
            for item in items
        ]
    })


# ============================================================
# Endpoints de Métricas
# ============================================================

@review_bp.route('/metrics', methods=['GET'])
@electoral_auth_required
def get_review_metrics():
    """Obtiene métricas del sistema de revisión."""
    queue = get_review_queue()
    registry = get_metrics_registry()

    return jsonify({
        'success': True,
        'queue_stats': queue.get_stats(),
        'metrics': {
            'corrections_total': registry.get_counter('castor_corrections_total'),
            'review_duration_p50': registry.get_histogram_percentile('castor_review_duration_seconds', 50),
            'review_duration_p95': registry.get_histogram_percentile('castor_review_duration_seconds', 95),
            'by_reason': queue._count_by_reason()
        }
    })
