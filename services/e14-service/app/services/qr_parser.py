"""
QR Parser para E-14 Electoral.
Extrae identificadores de mesa desde el código QR/barcode del formulario.

El QR del E-14 contiene la "llave primaria" que identifica:
- Departamento
- Municipio
- Zona
- Puesto de votación
- Mesa

Esto reduce errores de clasificación y acelera reconciliación.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class QRParseStatus(Enum):
    """Estado del parsing de QR."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"  # Algunos campos extraídos
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class QRData:
    """Datos extraídos del QR del E-14."""
    # Identificadores de ubicación
    dept_code: Optional[str] = None
    muni_code: Optional[str] = None
    zone_code: Optional[str] = None
    station_code: Optional[str] = None
    table_number: Optional[int] = None

    # Identificadores de elección
    election_code: Optional[str] = None
    corporacion_code: Optional[str] = None
    copy_type_code: Optional[str] = None

    # Metadata
    raw_barcode: Optional[str] = None
    parse_status: QRParseStatus = QRParseStatus.NOT_FOUND
    confidence: float = 0.0

    @property
    def polling_table_id(self) -> Optional[str]:
        """
        Genera el polling_table_id canónico.
        Formato: {dept}-{muni}-{zone}-{station}-{table}
        Ejemplo: 11-001-01-0045-003
        """
        if all([self.dept_code, self.muni_code, self.zone_code,
                self.station_code, self.table_number is not None]):
            return f"{self.dept_code}-{self.muni_code}-{self.zone_code}-{self.station_code}-{self.table_number:03d}"
        return None

    @property
    def mesa_id(self) -> Optional[str]:
        """Alias para polling_table_id (compatibilidad)."""
        return self.polling_table_id

    @property
    def is_complete(self) -> bool:
        """Verifica si todos los campos obligatorios están presentes."""
        return all([
            self.dept_code,
            self.muni_code,
            self.zone_code,
            self.station_code,
            self.table_number is not None
        ])


# ============================================================
# Patrones de QR conocidos para E-14
# ============================================================

# Patrón Registraduría 2024+ (código de barras largo)
# Formato típico: EEYYYYMMDD-CC-DD-MMM-ZZ-PPPP-TTT-X
# E=Elección, YYYY=Año, MM=Mes, DD=Día, CC=Corporación, DD=Depto, MMM=Muni, ZZ=Zona, PPPP=Puesto, TTT=Mesa, X=Copia
PATTERN_REGISTRADURIA_2024 = re.compile(
    r'^(?P<election>\d{2})'
    r'(?P<date>\d{8})-?'
    r'(?P<corporacion>\d{2})-?'
    r'(?P<dept>\d{2})-?'
    r'(?P<muni>\d{3})-?'
    r'(?P<zone>\d{2})-?'
    r'(?P<station>\d{4})-?'
    r'(?P<table>\d{3})-?'
    r'(?P<copy>\d)?$'
)

# Patrón alternativo (más corto)
# Formato: DD-MMM-ZZ-PPPP-TTT
PATTERN_SHORT = re.compile(
    r'^(?P<dept>\d{2})-?'
    r'(?P<muni>\d{3})-?'
    r'(?P<zone>\d{2})-?'
    r'(?P<station>\d{4})-?'
    r'(?P<table>\d{3})$'
)

# Patrón legacy (código numérico largo sin separadores)
# Formato: DDMMMZZPPPPTTТ (15 dígitos)
PATTERN_LEGACY = re.compile(
    r'^(?P<dept>\d{2})'
    r'(?P<muni>\d{3})'
    r'(?P<zone>\d{2})'
    r'(?P<station>\d{4})'
    r'(?P<table>\d{3})'
    r'(?P<extra>\d+)?$'
)

# Patrón E-14 con marcadores X (formato visto en formularios reales)
# Formato: "X 7-70-48-16 X" donde los números son identificadores parciales
# Este formato NO contiene datos geográficos directos, es un checksum/identificador
PATTERN_WITH_X = re.compile(
    r'^X[\s-]*'
    r'(?P<id1>\d{1,2})[\s-]*'
    r'(?P<id2>\d{2,3})[\s-]*'
    r'(?P<id3>\d{2})[\s-]*'
    r'(?P<id4>\d{2,4})[\s-]*'
    r'X?$',
    re.IGNORECASE
)

# Mapeo de códigos de corporación
CORPORACION_CODES = {
    '01': 'PRESIDENCIA',
    '02': 'SENADO',
    '03': 'CAMARA',
    '04': 'GOBERNACION',
    '05': 'ASAMBLEA',
    '06': 'ALCALDIA',
    '07': 'CONCEJO',
    '08': 'JAL',
    '09': 'CONSULTA',
    '10': 'CONSULTA_POPULAR',
}

# Mapeo de códigos de copia
COPY_TYPE_CODES = {
    '1': 'CLAVEROS',
    '2': 'DELEGADOS',
    '3': 'TRANSMISION',
}


def parse_qr_barcode(barcode: str) -> QRData:
    """
    Parsea el código QR/barcode del E-14.

    Args:
        barcode: String del código de barras escaneado o extraído por OCR

    Returns:
        QRData con los campos extraídos
    """
    if not barcode:
        return QRData(parse_status=QRParseStatus.NOT_FOUND)

    # Limpiar el barcode
    cleaned = barcode.strip().upper().replace(' ', '').replace('O', '0')

    result = QRData(raw_barcode=barcode)

    # Intentar patrón Registraduría 2024+
    match = PATTERN_REGISTRADURIA_2024.match(cleaned)
    if match:
        result.dept_code = match.group('dept')
        result.muni_code = match.group('muni')
        result.zone_code = match.group('zone')
        result.station_code = match.group('station')
        result.table_number = int(match.group('table'))
        result.election_code = match.group('election')
        result.corporacion_code = match.group('corporacion')
        result.copy_type_code = match.group('copy')
        result.parse_status = QRParseStatus.SUCCESS
        result.confidence = 0.95
        logger.info(f"QR parsed (Registraduría 2024): {result.polling_table_id}")
        return result

    # Intentar patrón corto
    match = PATTERN_SHORT.match(cleaned)
    if match:
        result.dept_code = match.group('dept')
        result.muni_code = match.group('muni')
        result.zone_code = match.group('zone')
        result.station_code = match.group('station')
        result.table_number = int(match.group('table'))
        result.parse_status = QRParseStatus.SUCCESS
        result.confidence = 0.90
        logger.info(f"QR parsed (short): {result.polling_table_id}")
        return result

    # Intentar patrón legacy
    match = PATTERN_LEGACY.match(cleaned)
    if match:
        result.dept_code = match.group('dept')
        result.muni_code = match.group('muni')
        result.zone_code = match.group('zone')
        result.station_code = match.group('station')
        result.table_number = int(match.group('table'))
        result.parse_status = QRParseStatus.SUCCESS
        result.confidence = 0.85
        logger.info(f"QR parsed (legacy): {result.polling_table_id}")
        return result

    # Intentar patrón con marcadores X (formato checksum)
    # Este formato NO contiene datos geográficos, solo es identificador
    # Los datos reales vienen del header OCR
    match = PATTERN_WITH_X.match(barcode.strip())
    if match:
        # Guardar el raw barcode para referencia
        result.raw_barcode = barcode
        result.parse_status = QRParseStatus.PARTIAL
        result.confidence = 0.60  # Baja confianza - necesita datos del header
        logger.info(f"QR parsed (X format): {barcode} - requiere datos de header OCR")
        return result

    # Intentar extracción parcial
    partial_result = _try_partial_extraction(cleaned)
    if partial_result:
        return partial_result

    logger.warning(f"Could not parse QR barcode: {barcode[:50]}...")
    result.parse_status = QRParseStatus.FAILED
    return result


def _try_partial_extraction(barcode: str) -> Optional[QRData]:
    """Intenta extraer campos parciales del barcode."""
    result = QRData(raw_barcode=barcode)

    # Buscar patrones de departamento (2 dígitos al inicio)
    dept_match = re.match(r'^(\d{2})', barcode)
    if dept_match:
        result.dept_code = dept_match.group(1)

    # Buscar secuencias de 3 dígitos para municipio
    muni_matches = re.findall(r'(\d{3})', barcode)
    if muni_matches and len(muni_matches) >= 1:
        # El primer grupo de 3 dígitos después del depto suele ser muni
        result.muni_code = muni_matches[0]

    # Buscar mesa (últimos 3 dígitos)
    table_match = re.search(r'(\d{3})$', barcode)
    if table_match:
        result.table_number = int(table_match.group(1))

    if result.dept_code or result.muni_code or result.table_number:
        result.parse_status = QRParseStatus.PARTIAL
        result.confidence = 0.5
        logger.info(f"QR partial extraction: dept={result.dept_code}, muni={result.muni_code}, table={result.table_number}")
        return result

    return None


def validate_qr_against_ocr(qr_data: QRData, ocr_header: dict) -> Tuple[bool, list]:
    """
    Valida que los datos del QR coincidan con el header extraído por OCR.

    Args:
        qr_data: Datos parseados del QR
        ocr_header: Header extraído por OCR (dept_code, muni_code, etc.)

    Returns:
        (is_valid, list_of_mismatches)
    """
    mismatches = []

    if qr_data.dept_code and ocr_header.get('dept_code'):
        if qr_data.dept_code != ocr_header['dept_code']:
            mismatches.append({
                'field': 'dept_code',
                'qr_value': qr_data.dept_code,
                'ocr_value': ocr_header['dept_code']
            })

    if qr_data.muni_code and ocr_header.get('muni_code'):
        if qr_data.muni_code != ocr_header['muni_code']:
            mismatches.append({
                'field': 'muni_code',
                'qr_value': qr_data.muni_code,
                'ocr_value': ocr_header['muni_code']
            })

    if qr_data.zone_code and ocr_header.get('zone_code'):
        if qr_data.zone_code != ocr_header['zone_code']:
            mismatches.append({
                'field': 'zone_code',
                'qr_value': qr_data.zone_code,
                'ocr_value': ocr_header['zone_code']
            })

    if qr_data.station_code and ocr_header.get('station_code'):
        if qr_data.station_code != ocr_header['station_code']:
            mismatches.append({
                'field': 'station_code',
                'qr_value': qr_data.station_code,
                'ocr_value': ocr_header['station_code']
            })

    if qr_data.table_number is not None and ocr_header.get('table_number') is not None:
        if qr_data.table_number != int(ocr_header['table_number']):
            mismatches.append({
                'field': 'table_number',
                'qr_value': qr_data.table_number,
                'ocr_value': ocr_header['table_number']
            })

    return len(mismatches) == 0, mismatches


def get_corporacion_from_code(code: str) -> Optional[str]:
    """Obtiene nombre de corporación desde código."""
    return CORPORACION_CODES.get(code)


def get_copy_type_from_code(code: str) -> Optional[str]:
    """Obtiene tipo de copia desde código."""
    return COPY_TYPE_CODES.get(code)
