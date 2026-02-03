"""
Routes para la Cola de Incidentes del War Room.
Gestión de incidentes electorales con priorización y SLA.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import random

from flask import Blueprint, jsonify, request, current_app

from app.schemas.incidents import (
    Incident, IncidentCreate, IncidentListResponse, IncidentStatsResponse,
    IncidentStats, IncidentType, IncidentSeverity, IncidentStatus,
    IncidentAssignRequest, IncidentResolveRequest, IncidentEscalateRequest,
    INCIDENT_CONFIG, WarRoomKPIs, WarRoomKPIsResponse, TimelineProgress
)
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

incidents_bp = Blueprint('incidents', __name__)

# Exempt from rate limiting - dashboard makes many parallel calls
limiter.exempt(incidents_bp)

# In-memory storage for demo (replace with DB in production)
_incidents_store: List[dict] = []
_incident_counter = 0


def _generate_demo_incidents():
    """Generate demo incidents for testing."""
    global _incidents_store, _incident_counter

    if _incidents_store:
        return  # Already initialized

    demo_data = [
        {
            "incident_type": IncidentType.ARITHMETIC_FAIL,
            "severity": IncidentSeverity.P0,
            "mesa_id": "05-001-001-01-003",
            "dept_code": "05",
            "dept_name": "Antioquia",
            "muni_code": "05001",
            "muni_name": "Medellín",
            "puesto": "I.E. San José",
            "description": "Suma de votos no cuadra: 238 vs 240 reportados",
            "ocr_confidence": None,
            "delta_value": 2,
        },
        {
            "incident_type": IncidentType.DISCREPANCY_RNEC,
            "severity": IncidentSeverity.P0,
            "mesa_id": "11-001-023-02-001",
            "dept_code": "11",
            "dept_name": "Bogotá D.C.",
            "muni_code": "11001",
            "muni_name": "Bogotá",
            "puesto": "Colegio Distrital",
            "description": "Diferencia de 15 votos vs publicación RNEC (Candidato #102)",
            "ocr_confidence": 0.92,
            "delta_value": 15,
        },
        {
            "incident_type": IncidentType.OCR_LOW_CONF,
            "severity": IncidentSeverity.P1,
            "mesa_id": "76-001-015-01-002",
            "dept_code": "76",
            "dept_name": "Valle del Cauca",
            "muni_code": "76001",
            "muni_name": "Cali",
            "puesto": "Centro Comunitario",
            "description": "Confianza OCR baja en campo 'Votos Válidos'",
            "ocr_confidence": 0.58,
            "delta_value": None,
        },
        {
            "incident_type": IncidentType.SOURCE_MISMATCH,
            "severity": IncidentSeverity.P1,
            "mesa_id": "05-045-012-03-001",
            "dept_code": "05",
            "dept_name": "Antioquia",
            "muni_code": "05045",
            "muni_name": "Apartadó",
            "puesto": "Escuela Rural",
            "description": "Discrepancia entre testigo y fuente oficial en candidato #105",
            "ocr_confidence": 0.85,
            "delta_value": 8,
        },
        {
            "incident_type": IncidentType.E11_VS_URNA,
            "severity": IncidentSeverity.P1,
            "mesa_id": "25-175-008-01-004",
            "dept_code": "25",
            "dept_name": "Cundinamarca",
            "muni_code": "25175",
            "muni_name": "Chía",
            "puesto": "Centro Comercial",
            "description": "Sufragantes E-11 (312) ≠ Votos en urna (308)",
            "ocr_confidence": 0.89,
            "delta_value": 4,
        },
        {
            "incident_type": IncidentType.RECOUNT_MARKED,
            "severity": IncidentSeverity.P0,
            "mesa_id": "08-001-005-02-003",
            "dept_code": "08",
            "dept_name": "Atlántico",
            "muni_code": "08001",
            "muni_name": "Barranquilla",
            "puesto": "Universidad del Norte",
            "description": "Mesa marcada para recuento por jurados",
            "ocr_confidence": 0.95,
            "delta_value": None,
        },
        {
            "incident_type": IncidentType.RNEC_DELAY,
            "severity": IncidentSeverity.P2,
            "mesa_id": "54-001-010-01-001",
            "dept_code": "54",
            "dept_name": "Norte de Santander",
            "muni_code": "54001",
            "muni_name": "Cúcuta",
            "puesto": "Centro Cívico",
            "description": "Sin publicación RNEC después de 45 minutos",
            "ocr_confidence": None,
            "delta_value": None,
        },
        {
            "incident_type": IncidentType.OCR_LOW_CONF,
            "severity": IncidentSeverity.P1,
            "mesa_id": "13-001-007-03-002",
            "dept_code": "13",
            "dept_name": "Bolívar",
            "muni_code": "13001",
            "muni_name": "Cartagena",
            "puesto": "Centro Histórico",
            "description": "Múltiples campos con confianza OCR < 70%",
            "ocr_confidence": 0.52,
            "delta_value": None,
        },
    ]

    now = datetime.utcnow()
    for i, data in enumerate(demo_data):
        _incident_counter += 1
        config = INCIDENT_CONFIG.get(data["incident_type"], {"sla_minutes": 30})
        created_at = now - timedelta(minutes=random.randint(2, 20))
        sla_deadline = created_at + timedelta(minutes=config["sla_minutes"])

        incident = {
            "id": _incident_counter,
            "incident_type": data["incident_type"].value,
            "severity": data["severity"].value,
            "status": IncidentStatus.OPEN.value,
            "mesa_id": data["mesa_id"],
            "dept_code": data["dept_code"],
            "dept_name": data["dept_name"],
            "muni_code": data["muni_code"],
            "muni_name": data["muni_name"],
            "puesto": data["puesto"],
            "description": data["description"],
            "ocr_confidence": data["ocr_confidence"],
            "delta_value": data["delta_value"],
            "evidence": {},
            "created_at": created_at.isoformat(),
            "sla_deadline": sla_deadline.isoformat(),
            "assigned_to": None,
            "assigned_at": None,
            "resolved_at": None,
            "resolution_notes": None,
            "escalated_to_legal": False,
        }
        _incidents_store.append(incident)


def _calculate_sla_remaining(sla_deadline_str: str) -> int:
    """Calculate remaining SLA time in minutes."""
    sla_deadline = datetime.fromisoformat(sla_deadline_str)
    remaining = (sla_deadline - datetime.utcnow()).total_seconds() / 60
    return max(0, int(remaining))


# ============================================================
# INCIDENTS CRUD ENDPOINTS
# ============================================================

@incidents_bp.route('', methods=['GET'])
def list_incidents():
    """
    List incidents with filters.

    Query params:
        status (optional): Filter by status (OPEN, ASSIGNED, etc.)
        severity (optional): Filter by severity (P0,P1,P2,P3)
        incident_type (optional): Filter by type
        dept_code (optional): Filter by department
        limit (optional): Max results (default 50)
    """
    try:
        _generate_demo_incidents()

        status = request.args.get('status')
        severity = request.args.get('severity')
        incident_type = request.args.get('incident_type')
        dept_code = request.args.get('dept_code')
        limit = request.args.get('limit', 50, type=int)

        # Filter incidents
        filtered = _incidents_store.copy()

        if status:
            statuses = [s.strip() for s in status.split(',')]
            filtered = [i for i in filtered if i['status'] in statuses]

        if severity:
            severities = [s.strip() for s in severity.split(',')]
            filtered = [i for i in filtered if i['severity'] in severities]

        if incident_type:
            types = [t.strip() for t in incident_type.split(',')]
            filtered = [i for i in filtered if i['incident_type'] in types]

        if dept_code:
            filtered = [i for i in filtered if i['dept_code'] == dept_code]

        # Sort by severity (P0 first) then by created_at (oldest first)
        severity_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        filtered.sort(key=lambda x: (severity_order.get(x['severity'], 4), x['created_at']))

        # Add SLA remaining to each incident
        for incident in filtered:
            incident['sla_remaining_minutes'] = _calculate_sla_remaining(incident['sla_deadline'])

        # Count stats
        open_count = len([i for i in _incidents_store if i['status'] == 'OPEN'])
        p0_count = len([i for i in _incidents_store if i['severity'] == 'P0' and i['status'] == 'OPEN'])
        p1_count = len([i for i in _incidents_store if i['severity'] == 'P1' and i['status'] == 'OPEN'])

        return jsonify({
            "success": True,
            "incidents": filtered[:limit],
            "total": len(filtered),
            "open_count": open_count,
            "p0_count": p0_count,
            "p1_count": p1_count
        })

    except Exception as e:
        logger.error(f"Error listing incidents: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('/<int:incident_id>', methods=['GET'])
def get_incident(incident_id: int):
    """Get a single incident by ID."""
    try:
        _generate_demo_incidents()

        incident = next((i for i in _incidents_store if i['id'] == incident_id), None)

        if not incident:
            return jsonify({"success": False, "error": "Incident not found"}), 404

        incident['sla_remaining_minutes'] = _calculate_sla_remaining(incident['sla_deadline'])

        return jsonify({"success": True, "incident": incident})

    except Exception as e:
        logger.error(f"Error getting incident: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('', methods=['POST'])
def create_incident():
    """Create a new incident."""
    global _incident_counter

    try:
        _generate_demo_incidents()
        data = request.get_json() or {}

        # Validate required fields
        required = ['incident_type', 'mesa_id', 'dept_code', 'description']
        for field in required:
            if not data.get(field):
                return jsonify({"success": False, "error": f"{field} is required"}), 400

        incident_type = IncidentType(data['incident_type'])
        config = INCIDENT_CONFIG.get(incident_type, {"default_severity": IncidentSeverity.P2, "sla_minutes": 30})

        severity = data.get('severity') or config['default_severity'].value
        now = datetime.utcnow()
        sla_deadline = now + timedelta(minutes=config['sla_minutes'])

        _incident_counter += 1
        incident = {
            "id": _incident_counter,
            "incident_type": incident_type.value,
            "severity": severity,
            "status": IncidentStatus.OPEN.value,
            "mesa_id": data['mesa_id'],
            "dept_code": data['dept_code'],
            "dept_name": data.get('dept_name'),
            "muni_code": data.get('muni_code'),
            "muni_name": data.get('muni_name'),
            "puesto": data.get('puesto'),
            "description": data['description'],
            "ocr_confidence": data.get('ocr_confidence'),
            "delta_value": data.get('delta_value'),
            "evidence": data.get('evidence', {}),
            "created_at": now.isoformat(),
            "sla_deadline": sla_deadline.isoformat(),
            "assigned_to": None,
            "assigned_at": None,
            "resolved_at": None,
            "resolution_notes": None,
            "escalated_to_legal": False,
        }

        _incidents_store.append(incident)

        return jsonify({"success": True, "incident": incident}), 201

    except ValueError as e:
        return jsonify({"success": False, "error": f"Invalid value: {e}"}), 400
    except Exception as e:
        logger.error(f"Error creating incident: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('/<int:incident_id>/assign', methods=['POST'])
def assign_incident(incident_id: int):
    """Assign an incident to a user."""
    try:
        _generate_demo_incidents()
        data = request.get_json() or {}

        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        incident = next((i for i in _incidents_store if i['id'] == incident_id), None)

        if not incident:
            return jsonify({"success": False, "error": "Incident not found"}), 404

        incident['status'] = IncidentStatus.ASSIGNED.value
        incident['assigned_to'] = user_id
        incident['assigned_at'] = datetime.utcnow().isoformat()

        if data.get('notes'):
            incident['resolution_notes'] = data['notes']

        return jsonify({"success": True, "incident": incident})

    except Exception as e:
        logger.error(f"Error assigning incident: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('/<int:incident_id>/resolve', methods=['POST'])
def resolve_incident(incident_id: int):
    """Resolve an incident."""
    try:
        _generate_demo_incidents()
        data = request.get_json() or {}

        resolution = data.get('resolution', 'RESOLVED')
        notes = data.get('notes')

        if not notes:
            return jsonify({"success": False, "error": "notes are required"}), 400

        incident = next((i for i in _incidents_store if i['id'] == incident_id), None)

        if not incident:
            return jsonify({"success": False, "error": "Incident not found"}), 404

        if resolution == 'FALSE_POSITIVE':
            incident['status'] = IncidentStatus.FALSE_POSITIVE.value
        else:
            incident['status'] = IncidentStatus.RESOLVED.value

        incident['resolved_at'] = datetime.utcnow().isoformat()
        incident['resolution_notes'] = notes

        return jsonify({"success": True, "incident": incident})

    except Exception as e:
        logger.error(f"Error resolving incident: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('/<int:incident_id>/escalate', methods=['POST'])
def escalate_incident(incident_id: int):
    """Escalate an incident."""
    try:
        _generate_demo_incidents()
        data = request.get_json() or {}

        reason = data.get('reason')
        if not reason:
            return jsonify({"success": False, "error": "reason is required"}), 400

        incident = next((i for i in _incidents_store if i['id'] == incident_id), None)

        if not incident:
            return jsonify({"success": False, "error": "Incident not found"}), 404

        incident['status'] = IncidentStatus.ESCALATED.value
        incident['escalated_to_legal'] = data.get('to_legal', False)
        incident['resolution_notes'] = f"ESCALADO: {reason}"

        return jsonify({"success": True, "incident": incident})

    except Exception as e:
        logger.error(f"Error escalating incident: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@incidents_bp.route('/stats', methods=['GET'])
def get_incident_stats():
    """Get incident statistics."""
    try:
        _generate_demo_incidents()

        stats = {
            "total": len(_incidents_store),
            "by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
            "by_status": {
                "OPEN": 0, "ASSIGNED": 0, "INVESTIGATING": 0,
                "RESOLVED": 0, "FALSE_POSITIVE": 0, "ESCALATED": 0
            },
            "by_type": {},
        }

        for incident in _incidents_store:
            stats["by_severity"][incident["severity"]] = stats["by_severity"].get(incident["severity"], 0) + 1
            stats["by_status"][incident["status"]] = stats["by_status"].get(incident["status"], 0) + 1
            stats["by_type"][incident["incident_type"]] = stats["by_type"].get(incident["incident_type"], 0) + 1

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"Error getting incident stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# WAR ROOM KPIs ENDPOINT
# ============================================================

@incidents_bp.route('/war-room/kpis', methods=['GET'])
def get_war_room_kpis():
    """
    Get War Room KPIs and timeline progress.

    Query params:
        contest_id (optional): Contest ID for filtering
    """
    try:
        _generate_demo_incidents()

        # Demo KPIs (replace with real DB queries in production)
        mesas_total = 12450
        mesas_testigo = 5602
        mesas_rnec = 2741
        mesas_reconciliadas = 2245

        p0_count = len([i for i in _incidents_store if i['severity'] == 'P0' and i['status'] == 'OPEN'])

        cobertura = ((mesas_testigo + mesas_rnec) / mesas_total * 100) if mesas_total > 0 else 0

        kpis = {
            "mesas_total": mesas_total,
            "mesas_testigo": mesas_testigo,
            "mesas_rnec": mesas_rnec,
            "mesas_reconciliadas": mesas_reconciliadas,
            "incidentes_p0": p0_count,
            "cobertura_pct": round(cobertura, 1),
            "testigo_pct": round(mesas_testigo / mesas_total * 100, 1) if mesas_total > 0 else 0,
            "rnec_pct": round(mesas_rnec / mesas_total * 100, 1) if mesas_total > 0 else 0,
            "reconciliadas_pct": round(mesas_reconciliadas / mesas_total * 100, 1) if mesas_total > 0 else 0,
            "last_rnec_update": (datetime.utcnow() - timedelta(minutes=3)).isoformat(),
            "last_testigo_update": datetime.utcnow().isoformat(),
        }

        timeline = [
            {
                "source": "WITNESS",
                "label": "Testigo",
                "processed": mesas_testigo,
                "total": mesas_total,
                "percentage": kpis["testigo_pct"],
                "last_update": kpis["last_testigo_update"]
            },
            {
                "source": "OFFICIAL",
                "label": "RNEC",
                "processed": mesas_rnec,
                "total": mesas_total,
                "percentage": kpis["rnec_pct"],
                "last_update": kpis["last_rnec_update"]
            },
            {
                "source": "RECONCILED",
                "label": "Reconciliadas",
                "processed": mesas_reconciliadas,
                "total": mesas_total,
                "percentage": kpis["reconciliadas_pct"],
                "last_update": None
            }
        ]

        return jsonify({
            "success": True,
            "kpis": kpis,
            "timeline": timeline,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting war room KPIs: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@incidents_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for incidents API."""
    return jsonify({
        "success": True,
        "service": "incidents-queue",
        "timestamp": datetime.utcnow().isoformat()
    })
