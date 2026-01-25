"""
Alfabeto Electoral para E-14.

Define el conjunto completo de símbolos reconocidos en formularios E-14:
- Dígitos: 0-9
- Marcas especiales: *, **, ***, guiones, casillas vacías
- Correcciones: tachaduras, sobrescrituras

Este módulo es CRÍTICO para evitar el bug de "*** terminó como 0 válido".
"""
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MarkType(Enum):
    """Tipos de marcas en el alfabeto electoral."""
    # Dígitos válidos
    DIGIT = "DIGIT"

    # Marcas especiales (requieren revisión)
    ASTERISK_SINGLE = "ASTERISK_SINGLE"      # * - Corrección menor
    ASTERISK_DOUBLE = "ASTERISK_DOUBLE"      # ** - Poco legible
    ASTERISK_TRIPLE = "ASTERISK_TRIPLE"      # *** - Muy dudoso/ilegible

    # Valores especiales
    DASH = "DASH"                            # - o -- o --- (cero explícito)
    EMPTY = "EMPTY"                          # Casilla vacía (cero implícito)
    CROSSED = "CROSSED"                      # X o tachado (anulado)

    # Correcciones
    OVERWRITE = "OVERWRITE"                  # Número sobrescrito
    STRIKETHROUGH = "STRIKETHROUGH"          # Número tachado con corrección

    # Especiales
    ILLEGIBLE = "ILLEGIBLE"                  # Completamente ilegible
    PARTIAL = "PARTIAL"                      # Parcialmente visible
    UNCLEAR = "UNCLEAR"                      # Ambiguo (ej: 7 vs 1)


class MarkSeverity(Enum):
    """Severidad de la marca para el flujo de revisión."""
    NONE = "NONE"              # Sin problema
    LOW = "LOW"                # Revisión opcional
    MEDIUM = "MEDIUM"          # Revisión recomendada
    HIGH = "HIGH"              # Revisión obligatoria
    CRITICAL = "CRITICAL"      # Bloquea procesamiento


@dataclass
class ParsedCell:
    """Resultado del parsing de una celda."""
    # Valor numérico normalizado (None si no se puede determinar)
    value: Optional[int] = None

    # Texto raw exactamente como se leyó
    raw_text: Optional[str] = None

    # Marca detectada
    raw_mark: Optional[str] = None
    mark_type: MarkType = MarkType.DIGIT

    # Confianza del OCR (0.0 - 1.0)
    confidence: float = 0.0

    # Flags de estado
    needs_review: bool = False
    is_valid: bool = True

    # Razón de revisión
    review_reason: Optional[str] = None

    # Severidad
    severity: MarkSeverity = MarkSeverity.NONE

    # Metadata adicional
    alternatives: List[int] = field(default_factory=list)  # Valores alternativos posibles
    cell_bbox: Optional[Tuple[int, int, int, int]] = None  # Bounding box para UI


# ============================================================
# Reglas del Alfabeto Electoral
# ============================================================

# Patrones de marcas especiales
MARK_PATTERNS = {
    # Asteriscos (de más a menos específico)
    r'^\*\*\*$': (MarkType.ASTERISK_TRIPLE, MarkSeverity.CRITICAL, None),
    r'^\*\*$': (MarkType.ASTERISK_DOUBLE, MarkSeverity.HIGH, None),
    r'^\*$': (MarkType.ASTERISK_SINGLE, MarkSeverity.MEDIUM, None),

    # Guiones (significan cero)
    r'^-{1,3}$': (MarkType.DASH, MarkSeverity.NONE, 0),
    r'^—$': (MarkType.DASH, MarkSeverity.NONE, 0),  # Em-dash

    # Casilla vacía
    r'^$': (MarkType.EMPTY, MarkSeverity.LOW, 0),
    r'^\s+$': (MarkType.EMPTY, MarkSeverity.LOW, 0),

    # Tachado/anulado
    r'^[Xx]$': (MarkType.CROSSED, MarkSeverity.HIGH, None),
    r'^[Nn][Uu][Ll][Oo]$': (MarkType.CROSSED, MarkSeverity.HIGH, None),

    # Ilegible explícito
    r'^\?+$': (MarkType.ILLEGIBLE, MarkSeverity.CRITICAL, None),
    r'^[Ii][Ll][Ee][Gg]': (MarkType.ILLEGIBLE, MarkSeverity.CRITICAL, None),
}

# Dígitos ambiguos que se confunden frecuentemente
AMBIGUOUS_PAIRS = {
    ('1', '7'): 0.3,   # 1 y 7 se confunden mucho
    ('0', '6'): 0.2,   # 0 y 6 cerrados
    ('0', '8'): 0.2,   # 0 y 8
    ('3', '8'): 0.2,   # 3 y 8
    ('5', '6'): 0.2,   # 5 y 6
    ('4', '9'): 0.15,  # 4 y 9
}

# Threshold de confianza por tipo
CONFIDENCE_THRESHOLDS = {
    'digit_high': 0.90,      # Dígito claro
    'digit_medium': 0.70,    # Dígito probable
    'digit_low': 0.50,       # Dígito dudoso
    'needs_review': 0.70,    # Umbral para revisión
    'reject': 0.30,          # Umbral para rechazo
}


def parse_cell_value(raw_text: str, confidence: float = 1.0) -> ParsedCell:
    """
    Parsea el valor de una celda según el alfabeto electoral.

    Args:
        raw_text: Texto raw extraído por OCR
        confidence: Confianza del OCR (0.0-1.0)

    Returns:
        ParsedCell con el valor normalizado y metadata
    """
    result = ParsedCell(
        raw_text=raw_text,
        confidence=confidence
    )

    if raw_text is None:
        result.mark_type = MarkType.EMPTY
        result.value = 0
        result.severity = MarkSeverity.LOW
        result.needs_review = True
        result.review_reason = "Celda vacía (null)"
        return result

    # Limpiar texto
    cleaned = raw_text.strip()

    # Verificar patrones de marcas especiales
    for pattern, (mark_type, severity, default_value) in MARK_PATTERNS.items():
        if re.match(pattern, cleaned):
            result.mark_type = mark_type
            result.severity = severity
            result.value = default_value
            result.raw_mark = cleaned if cleaned else None

            # Determinar si necesita revisión
            if severity in [MarkSeverity.HIGH, MarkSeverity.CRITICAL]:
                result.needs_review = True
                result.review_reason = f"Marca especial: {mark_type.value}"
            elif severity == MarkSeverity.MEDIUM and confidence < CONFIDENCE_THRESHOLDS['digit_medium']:
                result.needs_review = True
                result.review_reason = f"Marca especial con baja confianza"

            return result

    # Verificar si contiene asteriscos junto con números
    if '*' in cleaned:
        # Extraer número si hay
        digits = re.sub(r'[^\d]', '', cleaned)
        asterisk_count = cleaned.count('*')

        if digits:
            result.value = int(digits)

        result.raw_mark = '*' * min(asterisk_count, 3)

        if asterisk_count >= 3:
            result.mark_type = MarkType.ASTERISK_TRIPLE
            result.severity = MarkSeverity.CRITICAL
        elif asterisk_count == 2:
            result.mark_type = MarkType.ASTERISK_DOUBLE
            result.severity = MarkSeverity.HIGH
        else:
            result.mark_type = MarkType.ASTERISK_SINGLE
            result.severity = MarkSeverity.MEDIUM

        result.needs_review = True
        result.review_reason = f"Número con {asterisk_count} asterisco(s)"
        return result

    # Intentar parsear como número
    digits_only = re.sub(r'[^\d]', '', cleaned)

    if digits_only:
        try:
            result.value = int(digits_only)
            result.mark_type = MarkType.DIGIT

            # Verificar confianza
            if confidence < CONFIDENCE_THRESHOLDS['reject']:
                result.needs_review = True
                result.is_valid = False
                result.severity = MarkSeverity.CRITICAL
                result.review_reason = f"Confianza muy baja: {confidence:.2f}"
            elif confidence < CONFIDENCE_THRESHOLDS['needs_review']:
                result.needs_review = True
                result.severity = MarkSeverity.MEDIUM
                result.review_reason = f"Confianza baja: {confidence:.2f}"
            else:
                result.severity = MarkSeverity.NONE

            # Detectar posibles confusiones de dígitos
            _check_ambiguous_digits(result, cleaned, confidence)

            return result
        except ValueError:
            pass

    # No se pudo parsear
    result.mark_type = MarkType.UNCLEAR
    result.severity = MarkSeverity.HIGH
    result.needs_review = True
    result.is_valid = False
    result.review_reason = f"No se pudo parsear: '{cleaned}'"

    return result


def _check_ambiguous_digits(result: ParsedCell, text: str, confidence: float):
    """Verifica si hay dígitos ambiguos y sugiere alternativas."""
    if confidence > CONFIDENCE_THRESHOLDS['digit_high']:
        return  # Alta confianza, no verificar

    # Buscar dígitos que podrían confundirse
    alternatives = set()
    for char in text:
        if char.isdigit():
            for (d1, d2), penalty in AMBIGUOUS_PAIRS.items():
                if char == d1:
                    alternatives.add(int(text.replace(d1, d2, 1)))
                elif char == d2:
                    alternatives.add(int(text.replace(d2, d1, 1)))

    if alternatives:
        result.alternatives = sorted(alternatives)
        if not result.needs_review and confidence < CONFIDENCE_THRESHOLDS['digit_medium']:
            result.needs_review = True
            result.severity = MarkSeverity.LOW
            result.review_reason = f"Posibles alternativas: {result.alternatives}"


def normalize_cell_value(
    raw_text: str,
    confidence: float,
    context: Optional[Dict] = None
) -> Tuple[Optional[int], bool, str]:
    """
    Normaliza el valor de una celda para la base de datos.

    Args:
        raw_text: Texto raw
        confidence: Confianza OCR
        context: Contexto adicional (tipo de campo, etc.)

    Returns:
        (valor_normalizado, needs_review, raw_mark)
    """
    parsed = parse_cell_value(raw_text, confidence)

    raw_mark = parsed.raw_mark or ""
    if parsed.mark_type != MarkType.DIGIT and not parsed.raw_mark:
        raw_mark = parsed.mark_type.value

    return parsed.value, parsed.needs_review, raw_mark


def format_raw_mark(mark_type: MarkType) -> Optional[str]:
    """Formatea el raw_mark para almacenamiento."""
    mapping = {
        MarkType.ASTERISK_SINGLE: "*",
        MarkType.ASTERISK_DOUBLE: "**",
        MarkType.ASTERISK_TRIPLE: "***",
        MarkType.DASH: "-",
        MarkType.EMPTY: "",
        MarkType.CROSSED: "X",
        MarkType.ILLEGIBLE: "???",
        MarkType.OVERWRITE: "~",
        MarkType.STRIKETHROUGH: "//",
    }
    return mapping.get(mark_type)


def get_review_priority(cells: List[ParsedCell]) -> str:
    """
    Determina la prioridad de revisión para un conjunto de celdas.

    Returns:
        'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE'
    """
    severities = [c.severity for c in cells if c.needs_review]

    if MarkSeverity.CRITICAL in severities:
        return 'CRITICAL'
    if MarkSeverity.HIGH in severities:
        return 'HIGH'
    if MarkSeverity.MEDIUM in severities:
        return 'MEDIUM'
    if MarkSeverity.LOW in severities:
        return 'LOW'
    return 'NONE'


# ============================================================
# Validación aritmética con alfabeto
# ============================================================

def validate_arithmetic(
    cells: List[ParsedCell],
    expected_sum: Optional[int] = None,
    tolerance: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Valida que la suma de celdas coincida con el total esperado.

    Args:
        cells: Lista de celdas parseadas
        expected_sum: Suma esperada (si se conoce)
        tolerance: Tolerancia en votos

    Returns:
        (is_valid, error_message)
    """
    # Filtrar celdas con valores válidos
    valid_cells = [c for c in cells if c.value is not None and c.is_valid]

    if not valid_cells:
        return False, "No hay celdas válidas para sumar"

    actual_sum = sum(c.value for c in valid_cells)

    if expected_sum is not None:
        delta = abs(actual_sum - expected_sum)
        if delta > tolerance:
            return False, f"Suma no coincide: {actual_sum} vs {expected_sum} (delta={delta})"

    # Verificar celdas con marcas que podrían afectar
    problematic = [c for c in cells if c.mark_type in [
        MarkType.ASTERISK_TRIPLE,
        MarkType.ILLEGIBLE,
        MarkType.CROSSED
    ]]

    if problematic:
        return False, f"Hay {len(problematic)} celdas problemáticas que afectan la suma"

    return True, None
