"""
Human-in-the-Loop (HITL) Review System para E-14.

Maneja el flujo de revisión humana para:
- Celdas con baja confianza
- Errores aritméticos (sum mismatch)
- Marcas especiales (**, ***)
- Ambigüedades de dígitos

Incluye:
- Cola de revisión priorizada
- UI data structures
- Audit log before/after
- Feedback loop para mejora del modelo
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Estado de un item de revisión."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"


class ReviewPriority(Enum):
    """Prioridad de revisión."""
    CRITICAL = 1    # Bloquea procesamiento
    HIGH = 2        # Afecta integridad
    MEDIUM = 3      # Revisión recomendada
    LOW = 4         # Revisión opcional


class ReviewReason(Enum):
    """Razón por la que se requiere revisión."""
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ARITHMETIC_MISMATCH = "ARITHMETIC_MISMATCH"
    SPECIAL_MARK = "SPECIAL_MARK"
    AMBIGUOUS_DIGIT = "AMBIGUOUS_DIGIT"
    QR_OCR_MISMATCH = "QR_OCR_MISMATCH"
    DUPLICATE_FORM = "DUPLICATE_FORM"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    MANUAL_FLAG = "MANUAL_FLAG"


@dataclass
class CellReviewData:
    """Datos de una celda para revisión."""
    cell_id: str
    field_key: str

    # Valor OCR
    ocr_value: Optional[int]
    ocr_confidence: float
    ocr_raw_text: Optional[str]
    ocr_raw_mark: Optional[str]

    # Imagen recortada para UI
    cell_image_base64: Optional[str] = None

    # Contexto
    page_no: int = 1
    row_index: Optional[int] = None
    col_index: Optional[int] = None
    party_code: Optional[str] = None
    candidate_ordinal: Optional[int] = None

    # Alternativas sugeridas
    alternatives: List[int] = field(default_factory=list)

    # Valor corregido por humano
    human_value: Optional[int] = None
    human_notes: Optional[str] = None


@dataclass
class ReviewItem:
    """Item en la cola de revisión."""
    # Identificación
    review_id: str
    form_instance_id: str
    mesa_id: str

    # Prioridad y razón
    priority: ReviewPriority
    reason: ReviewReason
    reason_details: str

    # Estado
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Asignación
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Celdas a revisar
    cells: List[CellReviewData] = field(default_factory=list)

    # Contexto del formulario
    department: str = ""
    municipality: str = ""
    corporacion: str = ""
    copy_type: str = ""

    # Validaciones relacionadas
    failed_validations: List[str] = field(default_factory=list)

    # Resolución
    resolution: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class ReviewCorrection:
    """Corrección aplicada durante revisión."""
    correction_id: str
    review_id: str
    cell_id: str

    # Valores antes/después
    before_value: Optional[int]
    after_value: Optional[int]
    before_raw_mark: Optional[str]
    after_raw_mark: Optional[str]

    # Metadata
    corrected_by: str
    corrected_at: datetime
    correction_reason: str

    # Audit trail
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class ReviewQueue:
    """Cola de revisión con priorización."""
    items: List[ReviewItem] = field(default_factory=list)

    def add_item(self, item: ReviewItem):
        """Agrega item manteniendo orden por prioridad."""
        self.items.append(item)
        self.items.sort(key=lambda x: (x.priority.value, x.created_at))

    def get_next(self, reviewer_id: Optional[str] = None) -> Optional[ReviewItem]:
        """Obtiene el siguiente item pendiente."""
        for item in self.items:
            if item.status == ReviewStatus.PENDING:
                if reviewer_id:
                    item.assigned_to = reviewer_id
                    item.assigned_at = datetime.utcnow()
                item.status = ReviewStatus.IN_PROGRESS
                return item
        return None

    def get_by_priority(self, priority: ReviewPriority) -> List[ReviewItem]:
        """Obtiene items por prioridad."""
        return [i for i in self.items if i.priority == priority]

    def get_pending_count(self) -> Dict[str, int]:
        """Obtiene conteo de items pendientes por prioridad."""
        counts = {p.name: 0 for p in ReviewPriority}
        for item in self.items:
            if item.status == ReviewStatus.PENDING:
                counts[item.priority.name] += 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la cola."""
        total = len(self.items)
        pending = sum(1 for i in self.items if i.status == ReviewStatus.PENDING)
        in_progress = sum(1 for i in self.items if i.status == ReviewStatus.IN_PROGRESS)
        completed = sum(1 for i in self.items if i.status == ReviewStatus.COMPLETED)

        return {
            'total': total,
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed,
            'by_priority': self.get_pending_count(),
            'by_reason': self._count_by_reason()
        }

    def _count_by_reason(self) -> Dict[str, int]:
        counts = {r.name: 0 for r in ReviewReason}
        for item in self.items:
            if item.status == ReviewStatus.PENDING:
                counts[item.reason.name] += 1
        return counts


# ============================================================
# Funciones de creación de items de revisión
# ============================================================

def create_review_item_for_low_confidence(
    form_instance_id: str,
    mesa_id: str,
    cells: List[Dict],
    threshold: float = 0.7,
    department: str = "",
    municipality: str = "",
    corporacion: str = "",
) -> Optional[ReviewItem]:
    """
    Crea item de revisión para celdas con baja confianza.

    Args:
        form_instance_id: ID del formulario
        mesa_id: ID de la mesa
        cells: Lista de celdas con sus datos
        threshold: Umbral de confianza
        department: Código de departamento
        municipality: Código de municipio
        corporacion: Tipo de corporación

    Returns:
        ReviewItem o None si no hay celdas para revisar
    """
    cells_to_review = []

    for cell in cells:
        confidence = cell.get('confidence', 1.0)
        if confidence < threshold:
            cells_to_review.append(CellReviewData(
                cell_id=cell.get('cell_id', str(uuid.uuid4())),
                field_key=cell.get('field_key', 'UNKNOWN'),
                ocr_value=cell.get('value'),
                ocr_confidence=confidence,
                ocr_raw_text=cell.get('raw_text'),
                ocr_raw_mark=cell.get('raw_mark'),
                cell_image_base64=cell.get('cell_image'),
                page_no=cell.get('page_no', 1),
                row_index=cell.get('row_index'),
                col_index=cell.get('col_index'),
                party_code=cell.get('party_code'),
                candidate_ordinal=cell.get('candidate_ordinal'),
                alternatives=cell.get('alternatives', [])
            ))

    if not cells_to_review:
        return None

    # Determinar prioridad basada en la confianza mínima
    min_confidence = min(c.ocr_confidence for c in cells_to_review)
    if min_confidence < 0.3:
        priority = ReviewPriority.CRITICAL
    elif min_confidence < 0.5:
        priority = ReviewPriority.HIGH
    elif min_confidence < 0.7:
        priority = ReviewPriority.MEDIUM
    else:
        priority = ReviewPriority.LOW

    return ReviewItem(
        review_id=str(uuid.uuid4()),
        form_instance_id=form_instance_id,
        mesa_id=mesa_id,
        priority=priority,
        reason=ReviewReason.LOW_CONFIDENCE,
        reason_details=f"{len(cells_to_review)} celdas con confianza < {threshold}",
        cells=cells_to_review,
        department=department,
        municipality=municipality,
        corporacion=corporacion
    )


def create_review_item_for_arithmetic_mismatch(
    form_instance_id: str,
    mesa_id: str,
    expected_sum: int,
    actual_sum: int,
    cells: List[Dict],
    validation_name: str,
    department: str = "",
    municipality: str = "",
    corporacion: str = "",
) -> ReviewItem:
    """
    Crea item de revisión para error aritmético.
    """
    cells_to_review = [
        CellReviewData(
            cell_id=cell.get('cell_id', str(uuid.uuid4())),
            field_key=cell.get('field_key', 'UNKNOWN'),
            ocr_value=cell.get('value'),
            ocr_confidence=cell.get('confidence', 0.0),
            ocr_raw_text=cell.get('raw_text'),
            ocr_raw_mark=cell.get('raw_mark'),
            cell_image_base64=cell.get('cell_image'),
            page_no=cell.get('page_no', 1),
            party_code=cell.get('party_code'),
            alternatives=cell.get('alternatives', [])
        )
        for cell in cells
    ]

    delta = abs(expected_sum - actual_sum)
    priority = ReviewPriority.CRITICAL if delta > 10 else ReviewPriority.HIGH

    return ReviewItem(
        review_id=str(uuid.uuid4()),
        form_instance_id=form_instance_id,
        mesa_id=mesa_id,
        priority=priority,
        reason=ReviewReason.ARITHMETIC_MISMATCH,
        reason_details=f"Suma esperada: {expected_sum}, actual: {actual_sum}, delta: {delta}",
        cells=cells_to_review,
        failed_validations=[validation_name],
        department=department,
        municipality=municipality,
        corporacion=corporacion
    )


def create_review_item_for_special_marks(
    form_instance_id: str,
    mesa_id: str,
    cells: List[Dict],
    department: str = "",
    municipality: str = "",
    corporacion: str = "",
) -> Optional[ReviewItem]:
    """
    Crea item de revisión para celdas con marcas especiales.
    """
    cells_to_review = []

    for cell in cells:
        raw_mark = cell.get('raw_mark')
        if raw_mark and raw_mark in ['**', '***']:
            cells_to_review.append(CellReviewData(
                cell_id=cell.get('cell_id', str(uuid.uuid4())),
                field_key=cell.get('field_key', 'UNKNOWN'),
                ocr_value=cell.get('value'),
                ocr_confidence=cell.get('confidence', 0.0),
                ocr_raw_text=cell.get('raw_text'),
                ocr_raw_mark=raw_mark,
                cell_image_base64=cell.get('cell_image'),
                page_no=cell.get('page_no', 1),
                party_code=cell.get('party_code'),
            ))

    if not cells_to_review:
        return None

    # Prioridad basada en tipo de marca
    has_triple = any(c.ocr_raw_mark == '***' for c in cells_to_review)
    priority = ReviewPriority.CRITICAL if has_triple else ReviewPriority.HIGH

    return ReviewItem(
        review_id=str(uuid.uuid4()),
        form_instance_id=form_instance_id,
        mesa_id=mesa_id,
        priority=priority,
        reason=ReviewReason.SPECIAL_MARK,
        reason_details=f"{len(cells_to_review)} celdas con marcas especiales",
        cells=cells_to_review,
        department=department,
        municipality=municipality,
        corporacion=corporacion
    )


# ============================================================
# Procesamiento de correcciones
# ============================================================

def apply_correction(
    review_item: ReviewItem,
    corrections: List[Dict],
    reviewer_id: str,
    reviewer_ip: Optional[str] = None
) -> List[ReviewCorrection]:
    """
    Aplica correcciones a un item de revisión.

    Args:
        review_item: Item de revisión
        corrections: Lista de correcciones {cell_id, new_value, notes}
        reviewer_id: ID del revisor
        reviewer_ip: IP del revisor

    Returns:
        Lista de ReviewCorrection aplicadas
    """
    applied_corrections = []

    for corr in corrections:
        cell_id = corr.get('cell_id')
        new_value = corr.get('new_value')
        notes = corr.get('notes', '')

        # Encontrar la celda
        cell = next((c for c in review_item.cells if c.cell_id == cell_id), None)
        if not cell:
            logger.warning(f"Cell {cell_id} not found in review item")
            continue

        # Crear registro de corrección
        correction = ReviewCorrection(
            correction_id=str(uuid.uuid4()),
            review_id=review_item.review_id,
            cell_id=cell_id,
            before_value=cell.ocr_value,
            after_value=new_value,
            before_raw_mark=cell.ocr_raw_mark,
            after_raw_mark=None,  # Las correcciones limpian las marcas
            corrected_by=reviewer_id,
            corrected_at=datetime.utcnow(),
            correction_reason=notes,
            ip_address=reviewer_ip
        )
        applied_corrections.append(correction)

        # Actualizar celda
        cell.human_value = new_value
        cell.human_notes = notes

        logger.info(
            f"Correction applied: cell={cell_id}, "
            f"before={cell.ocr_value}, after={new_value}, "
            f"by={reviewer_id}"
        )

    # Actualizar estado del review item
    review_item.status = ReviewStatus.COMPLETED
    review_item.completed_at = datetime.utcnow()
    review_item.updated_at = datetime.utcnow()

    return applied_corrections


def generate_audit_log_entry(correction: ReviewCorrection) -> Dict[str, Any]:
    """
    Genera entrada para audit_log de una corrección.
    """
    return {
        'actor_user_id': correction.corrected_by,
        'action': 'CORRECT',
        'entity_type': 'ocr_field',
        'entity_id': correction.cell_id,
        'before_state': {
            'value': correction.before_value,
            'raw_mark': correction.before_raw_mark
        },
        'after_state': {
            'value': correction.after_value,
            'raw_mark': correction.after_raw_mark
        },
        'reason': correction.correction_reason,
        'ip_address': correction.ip_address,
        'created_at': correction.corrected_at.isoformat()
    }


# ============================================================
# Feedback loop para mejora del modelo
# ============================================================

@dataclass
class TrainingFeedback:
    """Feedback para entrenamiento del modelo."""
    cell_image_base64: str
    ocr_prediction: Optional[int]
    human_correction: int
    ocr_confidence: float
    cell_type: str
    raw_mark: Optional[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


def collect_training_feedback(corrections: List[ReviewCorrection], cells: List[CellReviewData]) -> List[TrainingFeedback]:
    """
    Recolecta feedback de correcciones para entrenamiento.

    Esto permite mejorar el modelo OCR con el tiempo.
    """
    feedback_items = []

    for correction in corrections:
        cell = next((c for c in cells if c.cell_id == correction.cell_id), None)
        if cell and cell.cell_image_base64:
            feedback_items.append(TrainingFeedback(
                cell_image_base64=cell.cell_image_base64,
                ocr_prediction=correction.before_value,
                human_correction=correction.after_value,
                ocr_confidence=cell.ocr_confidence,
                cell_type=cell.field_key,
                raw_mark=correction.before_raw_mark
            ))

    return feedback_items


# ============================================================
# UI Data Structures
# ============================================================

def prepare_review_ui_data(review_item: ReviewItem) -> Dict[str, Any]:
    """
    Prepara datos para la UI de revisión.

    Returns:
        Diccionario con todos los datos necesarios para el componente de revisión
    """
    return {
        'review_id': review_item.review_id,
        'mesa_id': review_item.mesa_id,
        'priority': review_item.priority.name,
        'reason': review_item.reason.name,
        'reason_details': review_item.reason_details,
        'status': review_item.status.name,
        'context': {
            'department': review_item.department,
            'municipality': review_item.municipality,
            'corporacion': review_item.corporacion,
            'copy_type': review_item.copy_type
        },
        'cells': [
            {
                'cell_id': c.cell_id,
                'field_key': c.field_key,
                'ocr_value': c.ocr_value,
                'ocr_confidence': c.ocr_confidence,
                'ocr_raw_text': c.ocr_raw_text,
                'ocr_raw_mark': c.ocr_raw_mark,
                'cell_image': c.cell_image_base64,
                'page_no': c.page_no,
                'party_code': c.party_code,
                'candidate_ordinal': c.candidate_ordinal,
                'alternatives': c.alternatives,
                'human_value': c.human_value,
                'human_notes': c.human_notes
            }
            for c in review_item.cells
        ],
        'failed_validations': review_item.failed_validations,
        'created_at': review_item.created_at.isoformat(),
        'assigned_to': review_item.assigned_to
    }
