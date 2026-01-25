"""
E-14 OCR Enhanced Service.

Pipeline mejorado basado en TySE:
1. QR como llave primaria (identificación de mesa)
2. Detector de celdas (layout detection)
3. OCR por celda individual
4. Validación y HITL por excepción

Este servicio extiende E14OCRService con capacidades avanzadas.
"""
import base64
import hashlib
import io
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

from config import Config
from services.qr_parser import (
    parse_qr_barcode,
    validate_qr_against_ocr,
    QRData,
    QRParseStatus,
)
from services.cell_extractor import (
    ExtractedCell,
    CellType,
    CellBoundingBox,
    crop_cell_image,
    enhance_cell_image,
    DIGIT_EXTRACTION_PROMPT,
)
from services.electoral_alphabet import (
    parse_cell_value,
    MarkType,
)

logger = logging.getLogger(__name__)


@dataclass
class CellOCRResult:
    """Resultado de OCR para una celda individual."""
    cell_id: str
    cell_type: str
    value: Optional[int]
    raw_text: str
    raw_mark: Optional[str]
    confidence: float
    needs_review: bool
    alternatives: List[int] = field(default_factory=list)

    # Contexto
    candidate_name: Optional[str] = None
    party_name: Optional[str] = None
    row_index: Optional[int] = None


@dataclass
class E14EnhancedResult:
    """Resultado completo del OCR mejorado."""
    # Identificación por QR (llave primaria)
    qr_data: Optional[QRData]
    polling_table_id: Optional[str]
    qr_confidence: float

    # Header extraído por OCR
    header: Dict[str, Any]

    # Celdas procesadas individualmente
    cells: List[CellOCRResult]

    # Totales calculados
    nivelacion: Dict[str, int]
    candidates: List[Dict[str, Any]]
    specials: Dict[str, int]
    total_mesa: int

    # Validaciones
    qr_ocr_match: bool
    sum_validation: bool
    needs_review_count: int

    # Metadata
    processing_time_ms: int
    model_used: str


class E14OCREnhanced:
    """
    Servicio de OCR mejorado para E-14.

    Pipeline:
    1. PDF → Imágenes con preprocesamiento
    2. Extracción de QR/Barcode (llave primaria)
    3. Detección de layout y celdas
    4. OCR por celda individual
    5. Validación cruzada QR vs OCR
    6. Agregación y cálculo de totales
    """

    def __init__(self):
        """Inicializa el servicio."""
        self.api_key = Config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")

        self.model = 'claude-opus-4-20250514'
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.timeout = 300

        logger.info("E14OCREnhanced inicializado")

    def process_e14(
        self,
        pdf_path: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> E14EnhancedResult:
        """
        Procesa un E-14 con el pipeline mejorado.

        Args:
            pdf_path: Ruta al PDF
            image_path: Ruta a imagen
            image_bytes: Bytes de imagen

        Returns:
            E14EnhancedResult con todos los datos
        """
        start_time = time.time()

        # 1. Obtener imagen(es)
        if pdf_path:
            images = self._pdf_to_images(Path(pdf_path).read_bytes())
        elif image_path:
            with open(image_path, 'rb') as f:
                images = [base64.b64encode(f.read()).decode('utf-8')]
        elif image_bytes:
            images = [base64.b64encode(image_bytes).decode('utf-8')]
        else:
            raise ValueError("Debe proporcionar pdf_path, image_path o image_bytes")

        # 2. Extraer QR (llave primaria) - PASO CRÍTICO
        qr_data = self._extract_qr(images[0])

        # 3. Procesar E-14 completo con detección de celdas
        ocr_result = self._process_with_cell_detection(images)

        # 4. Validar QR vs OCR y construir polling_table_id
        qr_ocr_match = True
        header = ocr_result.get('header', {})

        # Si QR es parcial o no está, usar header para polling_table_id
        if not qr_data or not qr_data.is_complete:
            # Construir polling_table_id desde header OCR
            if all([header.get('dept_code'), header.get('muni_code'),
                    header.get('zone_code'), header.get('station_code'),
                    header.get('table_number') is not None]):
                polling_table_id = (
                    f"{header['dept_code']}-{header['muni_code']}-"
                    f"{header.get('zone_code', '01')}-{header.get('station_code', '0001')}-"
                    f"{int(header['table_number']):03d}"
                )
                logger.info(f"Polling table ID from header: {polling_table_id}")
                if qr_data:
                    qr_data.dept_code = header.get('dept_code')
                    qr_data.muni_code = header.get('muni_code')
                    qr_data.zone_code = header.get('zone_code')
                    qr_data.station_code = header.get('station_code')
                    qr_data.table_number = header.get('table_number')
        else:
            qr_ocr_match, mismatches = validate_qr_against_ocr(qr_data, header)
            if mismatches:
                logger.warning(f"QR vs OCR mismatches: {mismatches}")

        # 5. Procesar celdas y calcular totales
        cells = self._parse_cells(ocr_result)
        candidates = self._extract_candidates(ocr_result)
        specials = self._extract_specials(ocr_result)
        nivelacion = self._extract_nivelacion(ocr_result)

        # 6. Validar suma
        total_calculated = sum(c.get('votes', 0) for c in candidates)
        total_calculated += specials.get('blank', 0) + specials.get('null', 0) + specials.get('unmarked', 0)
        total_reported = ocr_result.get('total_mesa', nivelacion.get('urna', 0))
        sum_validation = abs(total_calculated - total_reported) <= 1

        # 7. Contar items que necesitan revisión
        needs_review_count = sum(1 for c in cells if c.needs_review)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return E14EnhancedResult(
            qr_data=qr_data,
            polling_table_id=qr_data.polling_table_id if qr_data else None,
            qr_confidence=qr_data.confidence if qr_data else 0.0,
            header=ocr_result.get('header', {}),
            cells=cells,
            nivelacion=nivelacion,
            candidates=candidates,
            specials=specials,
            total_mesa=total_reported,
            qr_ocr_match=qr_ocr_match,
            sum_validation=sum_validation,
            needs_review_count=needs_review_count,
            processing_time_ms=processing_time_ms,
            model_used=self.model,
        )

    def _extract_qr(self, image_base64: str) -> Optional[QRData]:
        """
        Extrae y parsea el código QR/barcode del E-14.

        Este es el paso más crítico - el QR es la llave primaria
        que identifica unívocamente la mesa.
        """
        prompt = """Analiza esta imagen de un formulario E-14 electoral colombiano.

TAREA ESPECÍFICA: Encuentra y extrae el CÓDIGO DE BARRAS en la parte superior del formulario.

El código de barras típicamente aparece como:
- Una secuencia de números y/o letras
- Formato común: X-7-89-84-17-X o similar
- Puede tener separadores como guiones

RESPONDE SOLO CON EL TEXTO DEL CÓDIGO DE BARRAS.
Si no puedes leerlo claramente, responde "NO_LEGIBLE".
No agregues explicaciones, solo el código."""

        try:
            result = self._call_claude_simple(image_base64, prompt)
            barcode_text = result.strip()

            if barcode_text and barcode_text != "NO_LEGIBLE":
                qr_data = parse_qr_barcode(barcode_text)
                logger.info(f"QR extraído: {barcode_text} → {qr_data.polling_table_id}")
                return qr_data
            else:
                logger.warning("No se pudo extraer código de barras")
                return QRData(parse_status=QRParseStatus.NOT_FOUND)

        except Exception as e:
            logger.error(f"Error extrayendo QR: {e}")
            return None

    def _process_with_cell_detection(self, images: List[str]) -> Dict[str, Any]:
        """
        Procesa E-14 con detección de celdas.

        En lugar de procesar la página completa, identifica
        cada celda de votación y la procesa individualmente.
        """
        prompt = self._build_cell_detection_prompt()

        # Construir contenido con imagen(es)
        content = []
        for i, img_base64 in enumerate(images):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_base64
                }
            })
            if len(images) > 1:
                content.append({
                    "type": "text",
                    "text": f"[Página {i + 1} de {len(images)}]"
                })

        content.append({"type": "text", "text": prompt})

        # Llamar a Claude
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": content}]
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise ValueError(f"Error API: {response.status_code}")

        result = response.json()
        text = result['content'][0]['text']

        logger.debug(f"Raw response: {text[:500]}...")

        # Parsear JSON
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Buscar JSON en la respuesta
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Intentar encontrar JSON en la respuesta
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            logger.error(f"No se pudo parsear JSON: {text[:200]}...")
            # Retornar estructura vacía
            return {
                "header": {},
                "nivelacion": {"sufragantes_e11": 0, "votos_urna": 0},
                "candidates": [],
                "specials": {"blank": 0, "null": 0, "unmarked": 0},
                "total_mesa": 0
            }

    def _build_cell_detection_prompt(self) -> str:
        """Construye prompt para detección de celdas."""
        return """Analiza este formulario E-14 electoral colombiano.

TAREA: Extrae los datos celda por celda con máxima precisión.

ESTRUCTURA DEL FORMULARIO:
1. HEADER (parte superior):
   - Busca "DEPARTAMENTO XX - NOMBRE"
   - Busca "MUNICIPIO XXX - NOMBRE"
   - Busca "ZONA: XX  PUESTO: XX  MESA: XXX"
   - Busca "COPIA PARA: DELEGADOS/CLAVEROS/TRANSMISION"

2. NIVELACIÓN (cuadro con totales):
   - "TOTAL SUFRAGANTES SEGÚN E-11": número
   - "TOTAL VOTOS DEPOSITADOS EN LA URNA": número

3. CANDIDATOS (tabla central):
   - Cada fila tiene: Logo | Partido | Candidato | Votos (3 dígitos)
   - Lee los votos de DERECHA de cada candidato

4. ESPECIALES (después de candidatos):
   - "VOTOS EN BLANCO": número
   - "VOTOS NULOS": número
   - "VOTOS NO MARCADOS": número

5. TOTAL: "TOTAL VOTOS DE LA MESA": número

CÓMO LEER NÚMEROS:
- Cada casilla tiene 3 espacios: [Centenas][Decenas][Unidades]
- "0 4 8" → 48, "1 7 7" → 177, "0 0 3" → 3
- Vacío o guiones "- - -" → 0
- Asteriscos (*, **, ***) → reporta en raw_mark

Responde en JSON:
{
  "header": {
    "dept_code": "27",
    "dept_name": "SANTANDER",
    "muni_code": "001",
    "muni_name": "BUCARAMANGA",
    "zone_code": "01",
    "station_code": "01",
    "table_number": 6,
    "copy_type": "DELEGADOS"
  },
  "nivelacion": {
    "sufragantes_e11": 217,
    "votos_urna": 217
  },
  "candidates": [
    {
      "row": 1,
      "party_name": "LIGA",
      "candidate_name": "RODOLFO HERNÁNDEZ",
      "votes": 177,
      "raw_text": "1 7 7",
      "raw_mark": null,
      "confidence": 0.95,
      "needs_review": false
    }
  ],
  "specials": {
    "blank": 3,
    "null": 0,
    "unmarked": 0
  },
  "total_mesa": 217
}

CRÍTICO: Lee CADA número EXACTAMENTE como está escrito en la imagen."""

    def _call_claude_simple(self, image_base64: str, prompt: str) -> str:
        """Llamada simple a Claude con una imagen y prompt."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        }

        with httpx.Client(timeout=60) as client:
            response = client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise ValueError(f"Error API: {response.status_code}")

        return response.json()['content'][0]['text']

    def _pdf_to_images(self, pdf_data: bytes) -> List[str]:
        """Convierte PDF a imágenes con preprocesamiento."""
        try:
            from pdf2image import convert_from_bytes
            from PIL import Image, ImageEnhance, ImageFilter

            pil_images = convert_from_bytes(pdf_data, dpi=200, fmt='PNG')

            base64_images = []
            for img in pil_images:
                # Preprocesamiento
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Contraste
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)

                # Brillo
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)

                # Nitidez
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)

                # Edge enhance
                img = img.filter(ImageFilter.EDGE_ENHANCE)

                # Convertir a base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True)
                base64_images.append(base64.b64encode(buffer.getvalue()).decode('utf-8'))

            return base64_images

        except ImportError:
            raise ImportError("pdf2image no instalado")

    def _parse_cells(self, ocr_result: Dict[str, Any]) -> List[CellOCRResult]:
        """Parsea celdas del resultado OCR."""
        cells = []

        for i, cand in enumerate(ocr_result.get('candidates', [])):
            cell = CellOCRResult(
                cell_id=f"CANDIDATE_{i+1:02d}",
                cell_type="CANDIDATE_VOTE",
                value=cand.get('votes'),
                raw_text=cand.get('raw_text', ''),
                raw_mark=cand.get('raw_mark'),
                confidence=cand.get('confidence', 0.9),
                needs_review=cand.get('needs_review', False),
                candidate_name=cand.get('candidate_name'),
                party_name=cand.get('party_name'),
                row_index=cand.get('row', i+1),
            )
            cells.append(cell)

        return cells

    def _extract_candidates(self, ocr_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae lista de candidatos."""
        return ocr_result.get('candidates', [])

    def _extract_specials(self, ocr_result: Dict[str, Any]) -> Dict[str, int]:
        """Extrae votos especiales."""
        return ocr_result.get('specials', {
            'blank': 0,
            'null': 0,
            'unmarked': 0
        })

    def _extract_nivelacion(self, ocr_result: Dict[str, Any]) -> Dict[str, int]:
        """Extrae nivelación de mesa."""
        niv = ocr_result.get('nivelacion', {})
        return {
            'sufragantes': niv.get('sufragantes_e11', 0),
            'urna': niv.get('votos_urna', 0)
        }


def test_enhanced_ocr():
    """Test del OCR mejorado."""
    import sys

    pdf_path = '/Users/arielsanroj/Downloads/pruebaclaude.pdf'

    print("=" * 60)
    print("🗳️  E-14 OCR MEJORADO (QR + Celdas)")
    print("=" * 60)

    service = E14OCREnhanced()
    result = service.process_e14(pdf_path=pdf_path)

    print(f"\n📊 IDENTIFICACIÓN POR QR:")
    print(f"   Polling Table ID: {result.polling_table_id}")
    print(f"   QR Confidence: {result.qr_confidence:.2f}")
    print(f"   QR vs OCR Match: {'✅' if result.qr_ocr_match else '❌'}")

    print(f"\n📋 HEADER:")
    h = result.header
    print(f"   Depto: {h.get('dept_code')} - {h.get('dept_name')}")
    print(f"   Muni: {h.get('muni_code')} - {h.get('muni_name')}")
    print(f"   Mesa: {h.get('table_number')}")

    print(f"\n📈 NIVELACIÓN:")
    print(f"   Sufragantes E-11: {result.nivelacion.get('sufragantes')}")
    print(f"   Votos Urna: {result.nivelacion.get('urna')}")

    print(f"\n🗳️  CANDIDATOS:")
    for cand in result.candidates:
        mark = f" ({cand.get('raw_mark')})" if cand.get('raw_mark') else ""
        review = " ⚠️" if cand.get('needs_review') else ""
        print(f"   {cand.get('candidate_name', 'N/A')}: {cand.get('votes')}{mark}{review}")

    print(f"\n📊 ESPECIALES:")
    print(f"   Blancos: {result.specials.get('blank')}")
    print(f"   Nulos: {result.specials.get('null')}")
    print(f"   No Marcados: {result.specials.get('unmarked')}")

    print(f"\n✓ TOTAL MESA: {result.total_mesa}")
    print(f"   Suma válida: {'✅' if result.sum_validation else '❌'}")
    print(f"   Celdas para revisión: {result.needs_review_count}")

    print(f"\n⏱️  Tiempo: {result.processing_time_ms}ms")
    print("=" * 60)


if __name__ == "__main__":
    test_enhanced_ocr()
