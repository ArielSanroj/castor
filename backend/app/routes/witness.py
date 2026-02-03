"""
API Routes para el sistema de Testigos Electorales.
QR registration, push notifications, assignments.
"""
import json
import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, jsonify, request, current_app
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64

# Web Push
try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    logging.warning("pywebpush not installed. Push notifications disabled.")

from app.schemas.witness import (
    WitnessStatus, AssignmentStatus, NotificationType,
    QRCodeGenerateRequest, QRCodeResponse, QRCodeInfo,
    WitnessRegisterRequest, WitnessRegisterResponse,
    PushSubscribeRequest, PushSubscribeResponse,
    WitnessResponse, WitnessListResponse, WitnessLocationUpdate,
    AssignmentCreateRequest, AssignmentResponse, AssignmentUpdateRequest, AssignmentListResponse,
    NotificationSendRequest, NotificationSendResponse,
    NearbyWitnessRequest, NearbyWitness, NearbyWitnessResponse,
    VAPIDConfigResponse, WitnessStats
)
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

witness_bp = Blueprint('witness', __name__)

# Exempt from rate limiting - dashboard makes many parallel calls
limiter.exempt(witness_bp)

# ============================================================
# MOCK DATA (Replace with real database in production)
# ============================================================

# In-memory storage for demo
_witnesses = {}
_qr_codes = {}
_assignments = {}
_notifications = {}
_witness_id_counter = 1
_qr_id_counter = 1
_assignment_id_counter = 1
_notification_id_counter = 1

# VAPID keys (generate real ones for production)
# Generate with: vapid --gen
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '***REMOVED***')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '***REMOVED***')
VAPID_SUBJECT = os.getenv('VAPID_SUBJECT', 'mailto:castor@example.com')


# ============================================================
# QR CODE ENDPOINTS
# ============================================================

@witness_bp.route('/qr/generate', methods=['POST'])
def generate_qr_code():
    """
    Genera un código QR para registro de testigos.

    El QR contiene una URL única que el testigo escanea
    para registrarse en el sistema.
    """
    global _qr_id_counter

    try:
        data = request.get_json() or {}
        req = QRCodeGenerateRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    # Generar código único
    code = str(uuid.uuid4())

    # Calcular expiración
    expires_at = None
    if req.expires_hours:
        expires_at = datetime.utcnow() + timedelta(hours=req.expires_hours)

    # Guardar en storage
    qr_data = {
        'id': _qr_id_counter,
        'code': code,
        'dept_code': req.dept_code,
        'muni_code': req.muni_code,
        'station_id': req.station_id,
        'is_active': True,
        'max_uses': req.max_uses,
        'current_uses': 0,
        'expires_at': expires_at,
        'created_at': datetime.utcnow(),
        'created_by': None
    }
    _qr_codes[code] = qr_data
    _qr_id_counter += 1

    # Generar URL de registro
    base_url = os.getenv('APP_BASE_URL', request.host_url.rstrip('/'))
    registration_url = f"{base_url}/testigo/registro?code={code}"

    # Generar imagen QR como base64
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(registration_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_url = f"data:image/png;base64,{qr_base64}"

    return jsonify(QRCodeResponse(
        code=code,
        qr_url=qr_url,
        registration_url=registration_url,
        expires_at=expires_at,
        max_uses=req.max_uses
    ).model_dump(mode='json'))


@witness_bp.route('/qr/<code>', methods=['GET'])
def get_qr_info(code: str):
    """Obtiene información de un código QR."""
    qr_data = _qr_codes.get(code)

    if not qr_data:
        return jsonify({'success': False, 'error': 'Código QR no encontrado'}), 404

    return jsonify({
        'success': True,
        'qr': QRCodeInfo(**qr_data).model_dump(mode='json')
    })


@witness_bp.route('/qr/list', methods=['GET'])
def list_qr_codes():
    """Lista todos los códigos QR."""
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    qr_list = list(_qr_codes.values())

    if active_only:
        now = datetime.utcnow()
        qr_list = [
            qr for qr in qr_list
            if qr['is_active'] and (qr['expires_at'] is None or qr['expires_at'] > now)
        ]

    return jsonify({
        'success': True,
        'qr_codes': [QRCodeInfo(**qr).model_dump(mode='json') for qr in qr_list],
        'total': len(qr_list)
    })


# ============================================================
# WITNESS REGISTRATION
# ============================================================

@witness_bp.route('/register', methods=['POST'])
def register_witness():
    """
    Registra un nuevo testigo usando un código QR.

    El testigo escanea el QR, llena sus datos y queda registrado.
    """
    global _witness_id_counter

    try:
        data = request.get_json() or {}
        req = WitnessRegisterRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    # Validar código QR
    qr_data = _qr_codes.get(req.qr_code)

    if not qr_data:
        return jsonify({'success': False, 'error': 'Código QR inválido'}), 400

    if not qr_data['is_active']:
        return jsonify({'success': False, 'error': 'Código QR ya no está activo'}), 400

    if qr_data['expires_at'] and qr_data['expires_at'] < datetime.utcnow():
        return jsonify({'success': False, 'error': 'Código QR expirado'}), 400

    if qr_data['current_uses'] >= qr_data['max_uses']:
        return jsonify({'success': False, 'error': 'Código QR ya fue usado'}), 400

    # Verificar si el teléfono ya está registrado
    for w in _witnesses.values():
        if w['phone'] == req.phone:
            return jsonify({
                'success': False,
                'error': 'Este número de teléfono ya está registrado'
            }), 400

    # Crear testigo
    registration_code = str(uuid.uuid4())
    witness_data = {
        'id': _witness_id_counter,
        'registration_code': registration_code,
        'full_name': req.full_name,
        'phone': req.phone,
        'cedula': req.cedula,
        'email': req.email,
        'status': WitnessStatus.PENDING.value,
        'push_enabled': False,
        'push_subscription': None,
        'current_lat': None,
        'current_lon': None,
        'current_zone': None,
        'location_updated_at': None,
        # Zona de cobertura
        'coverage_dept_code': req.coverage_dept_code,
        'coverage_dept_name': req.coverage_dept_name,
        'coverage_muni_code': req.coverage_muni_code,
        'coverage_muni_name': req.coverage_muni_name,
        'coverage_station_name': req.coverage_station_name,
        'coverage_zone_code': None,
        'registered_at': datetime.utcnow(),
        'last_active_at': datetime.utcnow(),
        'device_info': request.headers.get('User-Agent')
    }
    _witnesses[_witness_id_counter] = witness_data
    _witness_id_counter += 1

    # Actualizar uso del QR
    qr_data['current_uses'] += 1
    if qr_data['current_uses'] >= qr_data['max_uses']:
        qr_data['is_active'] = False
        qr_data['used_by_witness_id'] = witness_data['id']
        qr_data['used_at'] = datetime.utcnow()

    logger.info(f"Nuevo testigo registrado: {req.full_name} (ID: {witness_data['id']})")

    return jsonify(WitnessRegisterResponse(
        witness_id=witness_data['id'],
        registration_code=registration_code,
        message="Registro exitoso. Active las notificaciones para recibir alertas."
    ).model_dump(mode='json'))


# ============================================================
# PUSH NOTIFICATIONS
# ============================================================

@witness_bp.route('/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """Retorna la clave pública VAPID para el cliente."""
    return jsonify(VAPIDConfigResponse(
        public_key=VAPID_PUBLIC_KEY,
        subject=VAPID_SUBJECT
    ).model_dump())


@witness_bp.route('/push/subscribe', methods=['POST'])
def subscribe_push():
    """
    Registra una suscripción push para un testigo.

    El frontend envía el subscription object después de
    obtener permiso del usuario.
    """
    try:
        data = request.get_json() or {}
        req = PushSubscribeRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    witness = _witnesses.get(req.witness_id)
    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    # Guardar subscription
    witness['push_subscription'] = req.subscription.model_dump()
    witness['push_enabled'] = True
    witness['status'] = WitnessStatus.ACTIVE.value
    witness['last_active_at'] = datetime.utcnow()

    logger.info(f"Push habilitado para testigo {req.witness_id}")

    # Enviar notificación de bienvenida
    _send_push_notification(
        witness,
        title="Bienvenido a Castor Control Electoral",
        body="Recibirás notificaciones cuando seas asignado a una mesa.",
        data={'type': 'WELCOME'}
    )

    return jsonify(PushSubscribeResponse(
        message="Notificaciones activadas correctamente"
    ).model_dump())


@witness_bp.route('/push/unsubscribe', methods=['POST'])
def unsubscribe_push():
    """Desactiva push notifications para un testigo."""
    try:
        data = request.get_json() or {}
        witness_id = data.get('witness_id')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    witness = _witnesses.get(witness_id)
    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    witness['push_subscription'] = None
    witness['push_enabled'] = False

    return jsonify({'success': True, 'message': 'Notificaciones desactivadas'})


@witness_bp.route('/notify', methods=['POST'])
def send_notification():
    """
    Envía notificación push a uno o más testigos.
    """
    global _notification_id_counter

    try:
        data = request.get_json() or {}
        req = NotificationSendRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    sent_count = 0
    failed_count = 0
    failures = []

    for witness_id in req.witness_ids:
        witness = _witnesses.get(witness_id)

        if not witness:
            failures.append({'witness_id': witness_id, 'error': 'No encontrado'})
            failed_count += 1
            continue

        if not witness.get('push_enabled') or not witness.get('push_subscription'):
            failures.append({'witness_id': witness_id, 'error': 'Push no habilitado'})
            failed_count += 1
            continue

        success = _send_push_notification(
            witness,
            title=req.title,
            body=req.body,
            data=req.data or {}
        )

        # Registrar notificación
        notification = {
            'id': _notification_id_counter,
            'witness_id': witness_id,
            'assignment_id': req.assignment_id,
            'notification_type': req.notification_type.value,
            'title': req.title,
            'body': req.body,
            'data': req.data,
            'sent_at': datetime.utcnow(),
            'push_success': success
        }
        _notifications[_notification_id_counter] = notification
        _notification_id_counter += 1

        if success:
            sent_count += 1
        else:
            failures.append({'witness_id': witness_id, 'error': 'Falló envío push'})
            failed_count += 1

    return jsonify(NotificationSendResponse(
        sent_count=sent_count,
        failed_count=failed_count,
        failures=failures
    ).model_dump())


def _send_push_notification(witness: dict, title: str, body: str, data: dict = None) -> bool:
    """Envía notificación push a un testigo."""
    if not WEBPUSH_AVAILABLE:
        logger.warning("webpush not available, simulating notification")
        logger.info(f"[SIMULATED PUSH] To: {witness['full_name']} | {title}: {body}")
        return True

    subscription = witness.get('push_subscription')
    if not subscription:
        return False

    payload = json.dumps({
        'title': title,
        'body': body,
        'data': data or {},
        'timestamp': datetime.utcnow().isoformat()
    })

    try:
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={
                'sub': VAPID_SUBJECT
            }
        )
        logger.info(f"Push enviado a testigo {witness['id']}: {title}")
        return True
    except WebPushException as e:
        logger.error(f"Error enviando push a testigo {witness['id']}: {e}")
        # Si el subscription expiró, deshabilitarlo
        if e.response and e.response.status_code in [404, 410]:
            witness['push_enabled'] = False
            witness['push_subscription'] = None
        return False


# ============================================================
# WITNESS MANAGEMENT
# ============================================================

@witness_bp.route('/list', methods=['GET'])
def list_witnesses():
    """Lista todos los testigos registrados."""
    status_filter = request.args.get('status')
    dept_filter = request.args.get('dept_code')
    push_only = request.args.get('push_only', 'false').lower() == 'true'

    witnesses = list(_witnesses.values())

    if status_filter:
        witnesses = [w for w in witnesses if w['status'] == status_filter]

    if dept_filter:
        witnesses = [w for w in witnesses if w.get('default_dept_code') == dept_filter]

    if push_only:
        witnesses = [w for w in witnesses if w.get('push_enabled')]

    return jsonify(WitnessListResponse(
        witnesses=[WitnessResponse(**w) for w in witnesses],
        total=len(witnesses),
        active_count=sum(1 for w in witnesses if w['status'] == WitnessStatus.ACTIVE.value),
        push_enabled_count=sum(1 for w in witnesses if w.get('push_enabled'))
    ).model_dump(mode='json'))


@witness_bp.route('/<int:witness_id>', methods=['GET'])
def get_witness(witness_id: int):
    """Obtiene datos de un testigo."""
    witness = _witnesses.get(witness_id)

    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    return jsonify({
        'success': True,
        'witness': WitnessResponse(**witness).model_dump(mode='json')
    })


@witness_bp.route('/<int:witness_id>/location', methods=['POST'])
def update_witness_location(witness_id: int):
    """Actualiza la ubicación GPS del testigo."""
    try:
        data = request.get_json() or {}
        data['witness_id'] = witness_id
        req = WitnessLocationUpdate(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    witness = _witnesses.get(witness_id)
    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    witness['current_lat'] = req.lat
    witness['current_lon'] = req.lon
    witness['current_zone'] = req.zone
    witness['location_updated_at'] = datetime.utcnow()
    witness['last_active_at'] = datetime.utcnow()

    return jsonify({'success': True, 'message': 'Ubicación actualizada'})


@witness_bp.route('/<int:witness_id>/status', methods=['PUT'])
def update_witness_status(witness_id: int):
    """Actualiza el estado de un testigo."""
    try:
        data = request.get_json() or {}
        new_status = WitnessStatus(data.get('status'))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    witness = _witnesses.get(witness_id)
    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    witness['status'] = new_status.value
    witness['last_active_at'] = datetime.utcnow()

    return jsonify({'success': True, 'status': new_status.value})


# ============================================================
# ASSIGNMENTS
# ============================================================

@witness_bp.route('/assignments', methods=['POST'])
def create_assignment():
    """
    Crea una asignación de testigo a mesa.

    Opcionalmente envía notificación push al testigo.
    """
    global _assignment_id_counter

    try:
        data = request.get_json() or {}
        req = AssignmentCreateRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    witness = _witnesses.get(req.witness_id)
    if not witness:
        return jsonify({'success': False, 'error': 'Testigo no encontrado'}), 404

    # Crear asignación
    assignment = {
        'id': _assignment_id_counter,
        'witness_id': req.witness_id,
        'witness_name': witness['full_name'],
        'polling_table_id': req.polling_table_id,
        'mesa_id': f"MESA-{req.polling_table_id}",  # Mock
        'contest_id': req.contest_id,
        'status': AssignmentStatus.PENDING.value,
        'priority': req.priority,
        'reason': req.reason,
        'assigned_at': datetime.utcnow(),
        'notified_at': None,
        'accepted_at': None,
        'arrived_at': None,
        'completed_at': None
    }
    _assignments[_assignment_id_counter] = assignment
    _assignment_id_counter += 1

    # Actualizar estado del testigo
    witness['status'] = WitnessStatus.ASSIGNED.value

    # Enviar notificación si se solicita
    if req.send_notification and witness.get('push_enabled'):
        success = _send_push_notification(
            witness,
            title="Nueva Asignación",
            body=f"Has sido asignado a {assignment['mesa_id']}. {req.reason or ''}",
            data={
                'type': 'ASSIGNMENT',
                'assignment_id': assignment['id'],
                'mesa_id': assignment['mesa_id']
            }
        )
        if success:
            assignment['notified_at'] = datetime.utcnow()

    logger.info(f"Asignación creada: Testigo {req.witness_id} -> Mesa {req.polling_table_id}")

    return jsonify({
        'success': True,
        'assignment': AssignmentResponse(**assignment).model_dump(mode='json')
    })


@witness_bp.route('/assignments', methods=['GET'])
def list_assignments():
    """Lista asignaciones con filtros."""
    witness_id = request.args.get('witness_id', type=int)
    status_filter = request.args.get('status')

    assignments = list(_assignments.values())

    if witness_id:
        assignments = [a for a in assignments if a['witness_id'] == witness_id]

    if status_filter:
        assignments = [a for a in assignments if a['status'] == status_filter]

    return jsonify(AssignmentListResponse(
        assignments=[AssignmentResponse(**a) for a in assignments],
        total=len(assignments),
        pending_count=sum(1 for a in assignments if a['status'] == AssignmentStatus.PENDING.value),
        active_count=sum(1 for a in assignments if a['status'] in [
            AssignmentStatus.ACCEPTED.value,
            AssignmentStatus.IN_TRANSIT.value,
            AssignmentStatus.ON_SITE.value
        ])
    ).model_dump(mode='json'))


@witness_bp.route('/assignments/<int:assignment_id>', methods=['PUT'])
def update_assignment(assignment_id: int):
    """Actualiza el estado de una asignación."""
    try:
        data = request.get_json() or {}
        req = AssignmentUpdateRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    assignment = _assignments.get(assignment_id)
    if not assignment:
        return jsonify({'success': False, 'error': 'Asignación no encontrada'}), 404

    assignment['status'] = req.status.value

    # Actualizar timestamps según estado
    now = datetime.utcnow()
    if req.status == AssignmentStatus.ACCEPTED:
        assignment['accepted_at'] = now
    elif req.status == AssignmentStatus.ON_SITE:
        assignment['arrived_at'] = now
    elif req.status == AssignmentStatus.COMPLETED:
        assignment['completed_at'] = now
        # Liberar testigo
        witness = _witnesses.get(assignment['witness_id'])
        if witness:
            witness['status'] = WitnessStatus.ACTIVE.value

    if req.notes:
        assignment['notes'] = req.notes
    if req.result:
        assignment['result'] = req.result

    return jsonify({
        'success': True,
        'assignment': AssignmentResponse(**assignment).model_dump(mode='json')
    })


# ============================================================
# NEARBY WITNESSES
# ============================================================

@witness_bp.route('/nearby', methods=['POST'])
def find_nearby_witnesses():
    """
    Encuentra testigos cercanos a una ubicación.

    Útil para asignar testigos a mesas críticas.
    """
    try:
        data = request.get_json() or {}
        req = NearbyWitnessRequest(**data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    import math

    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calcula distancia en km entre dos puntos."""
        R = 6371  # Radio de la Tierra en km
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    nearby = []

    for witness in _witnesses.values():
        if witness.get('current_lat') is None or witness.get('current_lon') is None:
            continue

        if req.status_filter and witness['status'] not in [s.value for s in req.status_filter]:
            continue

        distance = haversine_distance(
            req.lat, req.lon,
            witness['current_lat'], witness['current_lon']
        )

        if distance <= req.radius_km:
            nearby.append(NearbyWitness(
                id=witness['id'],
                full_name=witness['full_name'],
                phone=witness['phone'],
                distance_km=round(distance, 2),
                status=WitnessStatus(witness['status']),
                push_enabled=witness.get('push_enabled', False)
            ))

    # Ordenar por distancia
    nearby.sort(key=lambda w: w.distance_km)

    # Limitar resultados
    nearby = nearby[:req.limit]

    return jsonify(NearbyWitnessResponse(
        witnesses=nearby,
        total=len(nearby),
        search_radius_km=req.radius_km
    ).model_dump(mode='json'))


# ============================================================
# STATISTICS
# ============================================================

@witness_bp.route('/stats', methods=['GET'])
def get_witness_stats():
    """Obtiene estadísticas de testigos."""
    witnesses = list(_witnesses.values())
    assignments = list(_assignments.values())

    today = datetime.utcnow().date()

    stats = WitnessStats(
        total_registered=len(witnesses),
        active=sum(1 for w in witnesses if w['status'] == WitnessStatus.ACTIVE.value),
        assigned=sum(1 for w in witnesses if w['status'] == WitnessStatus.ASSIGNED.value),
        busy=sum(1 for w in witnesses if w['status'] == WitnessStatus.BUSY.value),
        offline=sum(1 for w in witnesses if w['status'] == WitnessStatus.OFFLINE.value),
        push_enabled=sum(1 for w in witnesses if w.get('push_enabled')),
        assignments_pending=sum(1 for a in assignments if a['status'] == AssignmentStatus.PENDING.value),
        assignments_completed_today=sum(
            1 for a in assignments
            if a['status'] == AssignmentStatus.COMPLETED.value
            and a.get('completed_at') and a['completed_at'].date() == today
        )
    )

    return jsonify({
        'success': True,
        'stats': stats.model_dump()
    })


# ============================================================
# GEOGRAPHY FOR REGISTRATION
# ============================================================

# Geography data loaded from static file
_GEOGRAPHY_DATA = None
_POLLING_STATIONS = {}  # Will be populated from database or additional data

def _load_geography_data():
    """Load geography data from static JSON file."""
    global _GEOGRAPHY_DATA
    if _GEOGRAPHY_DATA is not None:
        return _GEOGRAPHY_DATA

    geography_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        'static', 'data', 'geography.json'
    )

    try:
        with open(geography_path, 'r', encoding='utf-8') as f:
            _GEOGRAPHY_DATA = json.load(f)
        logger.info(f"Loaded geography data: {len(_GEOGRAPHY_DATA.get('departments', []))} departments")
    except FileNotFoundError:
        logger.warning(f"Geography file not found: {geography_path}")
        _GEOGRAPHY_DATA = {'departments': []}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in geography file: {e}")
        _GEOGRAPHY_DATA = {'departments': []}

    return _GEOGRAPHY_DATA

def _get_departments():
    """Get list of departments from geography data."""
    data = _load_geography_data()
    return [{'code': d['code'], 'name': d['name']} for d in data.get('departments', [])]

def _get_municipalities(dept_code: str):
    """Get municipalities for a department."""
    data = _load_geography_data()
    for dept in data.get('departments', []):
        if dept['code'] == dept_code:
            return dept.get('municipalities', [])
    return []


@witness_bp.route('/geography/departments', methods=['GET'])
def get_departments():
    """Lista departamentos disponibles."""
    return jsonify({
        'success': True,
        'departments': _get_departments()
    })


@witness_bp.route('/geography/municipalities/<dept_code>', methods=['GET'])
def get_municipalities(dept_code: str):
    """Lista municipios de un departamento."""
    municipalities = _get_municipalities(dept_code)
    return jsonify({
        'success': True,
        'municipalities': municipalities
    })


@witness_bp.route('/geography/stations/<muni_code>', methods=['GET'])
def get_polling_stations(muni_code: str):
    """Lista puestos de votación de un municipio."""
    # Polling stations need to be loaded from database or additional data source
    # For now, return empty list - can be populated later with actual station data
    stations = _POLLING_STATIONS.get(muni_code, [])
    return jsonify({
        'success': True,
        'stations': stations
    })


@witness_bp.route('/by-coverage', methods=['GET'])
def get_witnesses_by_coverage():
    """
    Lista testigos filtrados por zona de cobertura.

    Query params:
    - dept_code: Código del departamento
    - muni_code: Código del municipio
    - station_name: Nombre del puesto
    """
    dept_code = request.args.get('dept_code')
    muni_code = request.args.get('muni_code')
    station_name = request.args.get('station_name')

    witnesses = list(_witnesses.values())

    if dept_code:
        witnesses = [w for w in witnesses if w.get('coverage_dept_code') == dept_code]

    if muni_code:
        witnesses = [w for w in witnesses if w.get('coverage_muni_code') == muni_code]

    if station_name:
        witnesses = [w for w in witnesses if w.get('coverage_station_name') == station_name]

    return jsonify({
        'success': True,
        'witnesses': [WitnessResponse(**w).model_dump(mode='json') for w in witnesses],
        'total': len(witnesses),
        'filters': {
            'dept_code': dept_code,
            'muni_code': muni_code,
            'station_name': station_name
        }
    })
