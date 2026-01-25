"""
Cell Extractor para E-14 Electoral.

Pipeline especializado para extracción de dígitos:
1. Detector de celdas (layout)
2. Recorte por celda
3. Modelo de dígitos para cada recorte
4. Confidence por celda

Diseñado para manejar *** y tachones correctamente.
"""
import base64
import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CellType(Enum):
    """Tipos de celda en el E-14."""
    # Header
    BARCODE = "BARCODE"
    DEPT_CODE = "DEPT_CODE"
    MUNI_CODE = "MUNI_CODE"
    ZONE_CODE = "ZONE_CODE"
    STATION_CODE = "STATION_CODE"
    TABLE_NUMBER = "TABLE_NUMBER"

    # Nivelación
    SUFRAGANTES_DIGIT = "SUFRAGANTES_DIGIT"
    URNA_DIGIT = "URNA_DIGIT"

    # Votos
    PARTY_CODE = "PARTY_CODE"
    PARTY_VOTE_DIGIT = "PARTY_VOTE_DIGIT"
    CANDIDATE_VOTE_DIGIT = "CANDIDATE_VOTE_DIGIT"

    # Especiales
    BLANK_VOTE_DIGIT = "BLANK_VOTE_DIGIT"
    NULL_VOTE_DIGIT = "NULL_VOTE_DIGIT"
    UNMARKED_VOTE_DIGIT = "UNMARKED_VOTE_DIGIT"
    TOTAL_DIGIT = "TOTAL_DIGIT"

    # Otros
    SIGNATURE = "SIGNATURE"
    CHECKBOX = "CHECKBOX"
    TEXT = "TEXT"


@dataclass
class CellBoundingBox:
    """Bounding box de una celda."""
    x: int
    y: int
    width: int
    height: int
    page: int = 1

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x2, self.y2)


@dataclass
class ExtractedCell:
    """Celda extraída con su contenido."""
    # Identificación
    cell_id: str
    cell_type: CellType
    page_no: int

    # Posición
    bbox: CellBoundingBox

    # Contenido extraído
    raw_text: Optional[str] = None
    value_int: Optional[int] = None
    value_str: Optional[str] = None

    # Calidad
    confidence: float = 0.0
    is_empty: bool = False
    has_mark: bool = False
    raw_mark: Optional[str] = None

    # Imagen recortada (base64)
    cropped_image: Optional[str] = None

    # Contexto
    row_index: Optional[int] = None
    col_index: Optional[int] = None
    party_code: Optional[str] = None
    candidate_ordinal: Optional[int] = None

    # Review
    needs_review: bool = False
    review_reason: Optional[str] = None
    alternatives: List[int] = field(default_factory=list)


@dataclass
class CellGrid:
    """Grid de celdas de una sección del E-14."""
    section_name: str
    rows: int
    cols: int
    cells: List[List[ExtractedCell]]

    def get_cell(self, row: int, col: int) -> Optional[ExtractedCell]:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    def get_row_values(self, row: int) -> List[Optional[int]]:
        if 0 <= row < self.rows:
            return [c.value_int for c in self.cells[row]]
        return []

    def get_col_values(self, col: int) -> List[Optional[int]]:
        if 0 <= col < self.cols:
            return [self.cells[row][col].value_int for row in range(self.rows)]
        return []


@dataclass
class PageLayout:
    """Layout detectado de una página del E-14."""
    page_no: int
    width: int
    height: int

    # Regiones detectadas
    header_region: Optional[CellBoundingBox] = None
    barcode_region: Optional[CellBoundingBox] = None
    nivelacion_region: Optional[CellBoundingBox] = None
    parties_region: Optional[CellBoundingBox] = None
    specials_region: Optional[CellBoundingBox] = None
    signatures_region: Optional[CellBoundingBox] = None

    # Grids detectados
    nivelacion_grid: Optional[CellGrid] = None
    party_grids: List[CellGrid] = field(default_factory=list)
    specials_grid: Optional[CellGrid] = None

    # Celdas individuales
    all_cells: List[ExtractedCell] = field(default_factory=list)


# ============================================================
# Prompts especializados para extracción de celdas
# ============================================================

CELL_DETECTION_PROMPT = """Analiza esta imagen de un formulario E-14 y detecta TODAS las celdas de votación.

Para cada celda que contenga un número manuscrito, reporta:
1. Posición aproximada (fila, columna dentro de su sección)
2. El valor numérico que ves (0-999)
3. Tu confianza (0.0-1.0)
4. Si hay marcas especiales (*, **, ***, tachaduras, correcciones)

ALFABETO ELECTORAL - Valores válidos:
- Dígitos: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- Guión o vacío: significa 0
- * (asterisco): corrección menor
- ** (doble asterisco): poco legible
- *** (triple asterisco): muy dudoso/ilegible
- Tachadura: número anulado

REGLAS CRÍTICAS:
1. Si ves "- - -" o casilla vacía → valor = 0
2. Si ves número con * → reporta el número Y la marca
3. Si ves *** o ilegible → valor = null, needs_review = true
4. NO inventes números. Si no puedes leer, di null.

Responde en JSON:
{
  "cells": [
    {
      "section": "NIVELACION|PARTIDO_XXXX|ESPECIALES",
      "row": 0,
      "col": 0,
      "cell_type": "SUFRAGANTES_DIGIT|PARTY_VOTE_DIGIT|etc",
      "raw_text": "texto exacto",
      "value": número o null,
      "raw_mark": null | "*" | "**" | "***",
      "confidence": 0.0-1.0,
      "needs_review": true|false,
      "notes": "observaciones"
    }
  ]
}"""


DIGIT_EXTRACTION_PROMPT = """Analiza este recorte de celda de un formulario E-14 electoral.

La celda puede contener:
- Un número de 1-3 dígitos escritos a mano (0-999)
- Guiones "- - -" que significan CERO
- Casilla vacía que significa CERO
- Marcas especiales: *, **, ***
- Tachaduras o correcciones

INSTRUCCIONES:
1. Lee el número de izquierda a derecha (centenas, decenas, unidades)
2. Si hay correcciones, lee el valor FINAL corregido
3. Indica tu confianza (0.0-1.0)
4. Si hay marcas especiales, repórtalas

Responde en JSON:
{
  "value": número o null,
  "raw_text": "texto exacto como lo ves",
  "raw_mark": null | "*" | "**" | "***",
  "confidence": 0.95,
  "needs_review": false,
  "alternatives": [otros valores posibles si hay ambigüedad],
  "notes": "observaciones"
}"""


# ============================================================
# Funciones de extracción
# ============================================================

def build_cell_extraction_prompt(
    page_count: int,
    page_type: str = "GENERAL",
    corporacion: Optional[str] = None
) -> str:
    """
    Construye prompt optimizado para extracción de celdas.

    Args:
        page_count: Número total de páginas
        page_type: HEADER|PARTY|SPECIALS|GENERAL
        corporacion: Tipo de corporación

    Returns:
        Prompt string
    """
    base_prompt = CELL_DETECTION_PROMPT

    # Agregar contexto específico
    if page_type == "HEADER":
        base_prompt += """

ENFÓCATE EN:
- Código de barras / QR
- Departamento, Municipio, Zona, Puesto, Mesa
- Nivelación (Sufragantes E-11, Votos en Urna)
"""
    elif page_type == "PARTY":
        base_prompt += """

ENFÓCATE EN:
- Código del partido (4 dígitos)
- Votos por la lista (renglón 0)
- Votos por candidato (renglones 51-70 típicamente)
- Total del partido
"""
    elif page_type == "SPECIALS":
        base_prompt += """

ENFÓCATE EN:
- Votos en blanco
- Votos nulos
- Votos no marcados
- Total general
- Constancias (recuento, firmas)
"""

    if corporacion:
        base_prompt += f"\n\nCORPORACIÓN: {corporacion}"

    return base_prompt


def parse_cell_extraction_response(response: Dict[str, Any]) -> List[ExtractedCell]:
    """
    Parsea la respuesta del modelo de extracción de celdas.

    Args:
        response: Respuesta JSON del modelo

    Returns:
        Lista de ExtractedCell
    """
    cells = []

    for cell_data in response.get('cells', []):
        cell_type = _parse_cell_type(cell_data.get('cell_type', 'TEXT'))

        cell = ExtractedCell(
            cell_id=f"{cell_data.get('section', 'UNK')}_{cell_data.get('row', 0)}_{cell_data.get('col', 0)}",
            cell_type=cell_type,
            page_no=cell_data.get('page', 1),
            bbox=CellBoundingBox(
                x=cell_data.get('x', 0),
                y=cell_data.get('y', 0),
                width=cell_data.get('width', 50),
                height=cell_data.get('height', 30),
                page=cell_data.get('page', 1)
            ),
            raw_text=cell_data.get('raw_text'),
            value_int=cell_data.get('value'),
            confidence=cell_data.get('confidence', 0.0),
            has_mark=cell_data.get('raw_mark') is not None,
            raw_mark=cell_data.get('raw_mark'),
            row_index=cell_data.get('row'),
            col_index=cell_data.get('col'),
            party_code=cell_data.get('party_code'),
            needs_review=cell_data.get('needs_review', False),
            review_reason=cell_data.get('notes'),
            alternatives=cell_data.get('alternatives', [])
        )

        # Determinar si necesita revisión adicional
        if cell.raw_mark in ['**', '***']:
            cell.needs_review = True
            cell.review_reason = f"Marca especial: {cell.raw_mark}"
        elif cell.confidence < 0.7 and cell.value_int is not None:
            cell.needs_review = True
            cell.review_reason = f"Baja confianza: {cell.confidence:.2f}"

        cells.append(cell)

    return cells


def _parse_cell_type(type_str: str) -> CellType:
    """Parsea string a CellType."""
    mapping = {
        'BARCODE': CellType.BARCODE,
        'DEPT_CODE': CellType.DEPT_CODE,
        'MUNI_CODE': CellType.MUNI_CODE,
        'ZONE_CODE': CellType.ZONE_CODE,
        'STATION_CODE': CellType.STATION_CODE,
        'TABLE_NUMBER': CellType.TABLE_NUMBER,
        'SUFRAGANTES_DIGIT': CellType.SUFRAGANTES_DIGIT,
        'URNA_DIGIT': CellType.URNA_DIGIT,
        'PARTY_CODE': CellType.PARTY_CODE,
        'PARTY_VOTE_DIGIT': CellType.PARTY_VOTE_DIGIT,
        'CANDIDATE_VOTE_DIGIT': CellType.CANDIDATE_VOTE_DIGIT,
        'BLANK_VOTE_DIGIT': CellType.BLANK_VOTE_DIGIT,
        'NULL_VOTE_DIGIT': CellType.NULL_VOTE_DIGIT,
        'UNMARKED_VOTE_DIGIT': CellType.UNMARKED_VOTE_DIGIT,
        'TOTAL_DIGIT': CellType.TOTAL_DIGIT,
        'SIGNATURE': CellType.SIGNATURE,
        'CHECKBOX': CellType.CHECKBOX,
    }
    return mapping.get(type_str.upper(), CellType.TEXT)


def group_cells_by_party(cells: List[ExtractedCell]) -> Dict[str, List[ExtractedCell]]:
    """Agrupa celdas por partido."""
    groups: Dict[str, List[ExtractedCell]] = {}

    for cell in cells:
        if cell.party_code:
            if cell.party_code not in groups:
                groups[cell.party_code] = []
            groups[cell.party_code].append(cell)

    return groups


def calculate_party_total(cells: List[ExtractedCell]) -> Tuple[int, bool]:
    """
    Calcula el total de votos de un partido desde sus celdas.

    Returns:
        (total, has_review_items)
    """
    total = 0
    has_review = False

    for cell in cells:
        if cell.value_int is not None:
            total += cell.value_int
        if cell.needs_review:
            has_review = True

    return total, has_review


def validate_cell_sum(
    cells: List[ExtractedCell],
    expected_total: int,
    tolerance: int = 0
) -> Tuple[bool, int, List[ExtractedCell]]:
    """
    Valida que la suma de celdas coincida con el total esperado.

    Returns:
        (is_valid, computed_total, problematic_cells)
    """
    computed = sum(c.value_int or 0 for c in cells if c.cell_type != CellType.TOTAL_DIGIT)
    delta = abs(computed - expected_total)

    problematic = []
    if delta > tolerance:
        # Buscar celdas problemáticas
        problematic = [c for c in cells if c.needs_review or c.raw_mark]

    return delta <= tolerance, computed, problematic


# ============================================================
# Utilidades de imagen
# ============================================================

def crop_cell_image(
    page_image: bytes,
    bbox: CellBoundingBox,
    padding: int = 5
) -> Optional[str]:
    """
    Recorta una celda de la imagen de página.

    Args:
        page_image: Imagen de la página completa (bytes PNG/JPEG)
        bbox: Bounding box de la celda
        padding: Padding adicional en pixels

    Returns:
        Imagen recortada en base64 o None si falla
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(page_image))

        # Aplicar padding
        x1 = max(0, bbox.x - padding)
        y1 = max(0, bbox.y - padding)
        x2 = min(img.width, bbox.x2 + padding)
        y2 = min(img.height, bbox.y2 + padding)

        # Recortar
        cropped = img.crop((x1, y1, x2, y2))

        # Convertir a base64
        buffer = io.BytesIO()
        cropped.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    except Exception as e:
        logger.error(f"Error cropping cell: {e}")
        return None


def enhance_cell_image(image_base64: str) -> str:
    """
    Mejora la imagen de una celda para OCR.

    Args:
        image_base64: Imagen en base64

    Returns:
        Imagen mejorada en base64
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter

        # Decodificar
        img_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_data))

        # Convertir a escala de grises
        img = img.convert('L')

        # Aumentar contraste
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Aumentar nitidez
        img = img.filter(ImageFilter.SHARPEN)

        # Codificar de vuelta
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    except Exception as e:
        logger.error(f"Error enhancing cell image: {e}")
        return image_base64
