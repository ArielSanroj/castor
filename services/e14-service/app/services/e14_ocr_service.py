"""
E-14 OCR Service usando Claude Vision API.
Extrae datos estructurados de formularios E-14 de la Registraduría Nacional de Colombia.

Version 2.0 - Soporte para payload v2 con:
- Multi-página (Asamblea, Concejo, Cámara)
- ballot_option_type (LIST_ONLY, LIST_CANDIDATE, CANDIDATE)
- raw_mark para marcas especiales (*, **, ***)
- Estructura normalizada para BD v2
- Métricas integradas (QAS L2, S1)
"""
import base64
import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx

from config import Config
from utils.metrics import (
    get_metrics_registry,
    OCRMetrics,
    ValidationMetrics,
    track_ocr_processing,
)
from services.qr_parser import (
    parse_qr_barcode,
    validate_qr_against_ocr,
    QRData,
    QRParseStatus,
)
from services.electoral_alphabet import (
    parse_cell_value,
    normalize_cell_value,
    ParsedCell,
    MarkType,
    MarkSeverity,
    CONFIDENCE_THRESHOLDS,
)
from services.hitl_review import (
    create_review_item_for_low_confidence,
    create_review_item_for_arithmetic_mismatch,
    create_review_item_for_special_marks,
    ReviewItem,
    ReviewQueue,
)
from app.schemas.e14 import (
    # V1 schemas (backwards compatibility)
    E14ExtractionResult,
    E14Header,
    E14ValidationReport,
    NivelacionMesa,
    PartyVotes,
    VotosEspeciales,
    ConstanciasMesa,
    CandidateVotes,
    ValidationResult,
    ValidationSeverity,
    CopyType,
    Corporacion,
    ListType,
    CircunscripcionType,
    # V2 schemas
    E14PayloadV2,
    PipelineContext,
    TargetProcess,
    ProcessType,
    ContestType,
    ContestScope,
    InputDocument,
    PageInfo,
    SourceType,
    DocumentHeaderExtracted,
    OCRField,
    BallotOptionType,
    PoliticalGroupTally,
    SpecialsTally,
    TallyEntry,
    ValidationResultV2,
    DBWritePlan,
    AlertRow,
)

logger = logging.getLogger(__name__)


# ============================================================
# Prompts optimizados para Claude Vision
# ============================================================

SYSTEM_PROMPT = """Eres un sistema experto de OCR especializado en formularios electorales colombianos E-14 (Acta de Escrutinio de Jurados de Votación).

Tu tarea es extraer TODOS los datos del formulario E-14 con precisión absoluta. Los E-14 contienen:
1. Encabezado: código de barras, corporación, departamento, municipio, zona, puesto, mesa
2. Nivelación de mesa: total sufragantes E-11, total votos en urna, votos incinerados
3. Resultados por partido/lista: código, nombre, tipo de lista, votos por agrupación, votos por candidato
4. Votos especiales: en blanco, nulos, no marcados
5. Constancias: si hubo recuento, firmas de jurados

REGLAS CRÍTICAS:
- Los números están escritos A MANO en casillas de 3 dígitos (centenas-decenas-unidades)
- Una casilla vacía o con guión "-" significa 0 (cero)
- Si un dígito es ambiguo, indica confidence bajo y needs_review=true
- NUNCA inventes datos. Si no puedes leer algo, indica null con confidence 0
- Extrae TODOS los partidos de TODAS las páginas
- Distingue entre "LISTA CON VOTO PREFERENTE" y "LISTA SIN VOTO PREFERENTE"

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional."""

SYSTEM_PROMPT_V2 = """Eres un sistema experto de OCR especializado en formularios electorales colombianos E-14 (Acta de Escrutinio de Jurados de Votación).

Tu tarea es extraer TODOS los datos del formulario E-14 con precisión absoluta, generando un payload estructurado para procesamiento automatizado.

TIPOS DE FORMULARIOS E-14:
1. SIMPLE (1-2 páginas): Consulta Popular, Presidencia, Gobernación, Alcaldía
   - Cada opción es un CANDIDATE individual

2. MULTI-PÁGINA (3-9 páginas): Cámara, Senado, Asamblea, Concejo
   - Página 1: Encabezado + Nivelación + Primer partido
   - Páginas 2-N: Partidos con voto preferente (LIST_ONLY + LIST_CANDIDATE)
   - Última página: Votos especiales + Firmas

=== CÓDIGO QR/BARCODE (LLAVE PRIMARIA) ===
El código de barras en la parte superior es la LLAVE PRIMARIA del formulario.
Extráelo SIEMPRE con máxima prioridad. Formato típico:
- Formato largo: EEYYYYMMDD-CC-DD-MMM-ZZ-PPPP-TTT-X
- E=Elección, YYYY=Año, CC=Corporación, DD=Depto, MMM=Muni, ZZ=Zona, PPPP=Puesto, TTT=Mesa
Si el QR está parcialmente visible, extrae lo que puedas leer.

=== ALFABETO ELECTORAL (MARCAS ESPECIALES) ===
Además de dígitos 0-9, reconoce estas marcas:
- "-" o "---" (guiones): Significa CERO (0)
- Casilla vacía: Significa CERO (0)
- "*" (asterisco): Corrección menor, el número es LEGIBLE
- "**" (doble asterisco): Poco legible, necesita revisión
- "***" (triple asterisco): MUY DUDOSO o ILEGIBLE, NO asignes valor
- "X" o tachadura: Anulado, valor = null
- Sobrescritura: Lee el valor FINAL corregido, marca con "*"

REGLA CRÍTICA: Si ves *** o algo ilegible, NUNCA inventes un número.
Reporta: value=null, raw_mark="***", needs_review=true

=== REGLAS DE EXTRACCIÓN ===
- Los números están escritos A MANO en casillas de 3 dígitos (centenas-decenas-unidades)
- Lee de IZQUIERDA a DERECHA: centenas, decenas, unidades
- Si un dígito tiene marcas o correcciones, incluye raw_mark y needs_review=true
- Extrae TODOS los partidos/candidatos de TODAS las páginas
- Indica el page_no donde aparece cada campo
- Reporta confidence por cada celda (0.0-1.0)

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional."""


def build_extraction_prompt(pages_count: int) -> str:
    """Construye el prompt de extracción basado en el número de páginas."""
    return f"""Analiza este formulario E-14 de {pages_count} página(s) y extrae TODOS los datos en el siguiente formato JSON:

{{
  "header": {{
    "barcode": "código de barras (número largo arriba)",
    "copy_type": "CLAVEROS|DELEGADOS|TRANSMISION",
    "election_name": "nombre de la elección",
    "election_date": "fecha",
    "corporacion": "CAMARA|SENADO|PRESIDENCIA|GOBERNACION|ALCALDIA|ASAMBLEA|CONCEJO|JAL|CONSULTA",
    "departamento_code": "código de 2 dígitos",
    "departamento_name": "nombre",
    "municipio_code": "código",
    "municipio_name": "nombre",
    "lugar": "nombre del puesto de votación",
    "zona": "código zona",
    "puesto": "código puesto",
    "mesa": "número mesa"
  }},
  "nivelacion": {{
    "total_sufragantes_e11": número,
    "total_votos_urna": número,
    "total_votos_incinerados": número o null,
    "confidence_sufragantes": 0.0-1.0,
    "confidence_urna": 0.0-1.0
  }},
  "partidos": [
    {{
      "party_code": "código 4 dígitos",
      "party_name": "nombre completo",
      "list_type": "CON_VOTO_PREFERENTE|SIN_VOTO_PREFERENTE",
      "circunscripcion": "TERRITORIAL|ESPECIAL_INDIGENA|ESPECIAL_AFRO",
      "votos_agrupacion": número,
      "votos_candidatos": [
        {{"candidate_number": "101", "votes": número, "confidence": 0.0-1.0}},
        ...
      ],
      "total_votos": número,
      "confidence_total": 0.0-1.0,
      "needs_review": true|false
    }}
  ],
  "votos_especiales": {{
    "votos_blanco": número,
    "votos_nulos": número,
    "votos_no_marcados": número,
    "confidence_blanco": 0.0-1.0,
    "confidence_nulos": 0.0-1.0,
    "confidence_no_marcados": 0.0-1.0
  }},
  "constancias": {{
    "hubo_recuento": true|false|null,
    "recuento_solicitado_por": "texto o null",
    "otras_constancias": "texto o null",
    "num_jurados_firmantes": número de 0 a 6
  }},
  "metadata": {{
    "total_pages": {pages_count},
    "pages_with_data": número,
    "overall_confidence": 0.0-1.0,
    "fields_needing_review": número,
    "notes": "observaciones del OCR"
  }}
}}

INSTRUCCIONES ESPECÍFICAS:
1. Para casillas con guiones "- - -" o vacías: valor = 0
2. Para números manuscritos: lee cada dígito de izquierda a derecha (centenas, decenas, unidades)
3. Si un partido tiene "LISTA SIN VOTO PREFERENTE" solo tiene votos de agrupación (la flecha →)
4. Si un partido tiene "LISTA CON VOTO PREFERENTE" tiene votos de agrupación (fila 0 con ←) Y votos por candidato (filas 101-117)
5. La circunscripción se identifica por secciones: "CIRCUNSCRIPCIÓN TERRITORIAL", "ESPECIAL COMUNIDADES INDÍGENAS", "ESPECIAL COMUNIDADES AFRO-DESCENDIENTES"
6. Extrae TODOS los partidos, incluso los que tienen 0 votos
7. Para dígitos dudosos: si parece "7" o "1", indica confidence bajo y needs_review=true"""


def build_extraction_prompt_v2(pages_count: int, corporacion_hint: Optional[str] = None) -> str:
    """Construye el prompt de extracción v2 con soporte para raw_mark y multi-página."""

    # Determinar tipo de formulario
    is_multipage = pages_count > 2 or corporacion_hint in ['CAMARA', 'SENADO', 'ASAMBLEA', 'CONCEJO']

    if is_multipage:
        return f"""Analiza este formulario E-14 MULTI-PÁGINA de {pages_count} página(s) y extrae TODOS los datos en formato v2.

ESTRUCTURA ESPERADA:
- Página 1: Encabezado + Nivelación + Posiblemente primer partido
- Páginas intermedias: Partidos con voto preferente
- Última página: Votos especiales + Constancias + Firmas

Extrae en el siguiente formato JSON:

{{
  "header": {{
    "election_date": "YYYY-MM-DD",
    "election_label": "texto completo de la elección",
    "corporacion": "CAMARA|SENADO|ASAMBLEA|CONCEJO|...",
    "dept_code": "código 2 dígitos",
    "dept_name": "nombre departamento",
    "muni_code": "código",
    "muni_name": "nombre municipio",
    "zone_code": "código zona",
    "station_code": "código puesto",
    "table_number": número_mesa,
    "place_name": "nombre lugar votación",
    "page_count_reported": número_páginas_según_formulario,
    "copy_type": "CLAVEROS|DELEGADOS|TRANSMISION"
  }},

  "nivelacion": {{
    "total_sufragantes_e11": número,
    "total_votos_urna": número,
    "confidence_sufragantes": 0.0-1.0,
    "confidence_urna": 0.0-1.0
  }},

  "ocr_fields": [
    {{
      "field_key": "TOTAL_SUFRAGANTES_E11",
      "page_no": 1,
      "value_int": número,
      "raw_text": "texto exacto leído",
      "raw_mark": null | "*" | "**" | "***",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "LIST_HEADER",
      "page_no": 1,
      "political_group_code": "0001",
      "political_group_name": "NOMBRE DEL PARTIDO",
      "list_type": "CON_VOTO_PREFERENTE|SIN_VOTO_PREFERENTE"
    }},
    {{
      "field_key": "LIST_ONLY_VOTES",
      "page_no": 1,
      "ballot_option_type": "LIST_ONLY",
      "political_group_code": "0001",
      "value_int": número,
      "raw_text": "texto",
      "raw_mark": null,
      "confidence": 0.0-1.0,
      "needs_review": false,
      "notes": "Votos solo por la lista (renglón 0)"
    }},
    {{
      "field_key": "CANDIDATE_51",
      "page_no": 1,
      "ballot_option_type": "LIST_CANDIDATE",
      "political_group_code": "0001",
      "candidate_ordinal": 51,
      "candidate_name": "NOMBRE APELLIDO",
      "value_int": número,
      "raw_text": "texto",
      "raw_mark": "*",
      "confidence": 0.65,
      "needs_review": true
    }},
    {{
      "field_key": "LIST_TOTAL",
      "page_no": 1,
      "political_group_code": "0001",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false,
      "notes": "Total del partido"
    }},
    {{
      "field_key": "VOTOS_EN_BLANCO",
      "page_no": {pages_count},
      "ballot_option_type": "BLANK",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "VOTOS_NULOS",
      "page_no": {pages_count},
      "ballot_option_type": "NULL",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "VOTOS_NO_MARCADOS",
      "page_no": {pages_count},
      "ballot_option_type": "UNMARKED",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "TOTAL_VOTOS_MESA",
      "page_no": {pages_count},
      "ballot_option_type": "TOTAL",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "HUBO_RECUENTO",
      "page_no": {pages_count},
      "value_bool": true|false,
      "raw_text": "SI|NO",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "FIRMA_JURADO_1",
      "page_no": {pages_count},
      "value_bool": true,
      "confidence": 0.0-1.0,
      "needs_review": false
    }}
  ],

  "page_mapping": [
    {{"page_no": 1, "political_group_code": "HEADER", "description": "Encabezado + Nivelación"}},
    {{"page_no": 2, "political_group_code": "0001", "description": "Partido 1"}},
    {{"page_no": 3, "political_group_code": "0002", "description": "Partido 2"}}
  ],

  "metadata": {{
    "total_pages": {pages_count},
    "pages_with_data": número,
    "overall_confidence": 0.0-1.0,
    "fields_needing_review": número,
    "fields_with_marks": ["campo1", "campo2"],
    "notes": "observaciones del OCR"
  }}
}}

INSTRUCCIONES:
1. Extrae TODOS los partidos con TODOS sus candidatos
2. Usa page_no para indicar en qué página está cada campo
3. Usa raw_mark para indicar correcciones: "*" tachadura, "**" poco legible, "***" muy dudoso
4. Para listas CON VOTO PREFERENTE: incluye LIST_ONLY (renglón 0) + CANDIDATE_XX
5. Para listas SIN VOTO PREFERENTE: solo incluye el total de la lista
6. Los candidate_ordinal típicos son: 51, 52, 53... hasta 70 aproximadamente"""

    else:
        return f"""Analiza este formulario E-14 SIMPLE de {pages_count} página(s) y extrae TODOS los datos en formato v2.

ESTRUCTURA ESPERADA (Consulta/Presidencia/Gobernación/Alcaldía):
- Página única o 2 páginas con candidatos individuales
- Cada opción es un CANDIDATE (no hay voto preferente)

Extrae en el siguiente formato JSON:

{{
  "header": {{
    "election_date": "YYYY-MM-DD",
    "election_label": "texto completo de la elección",
    "corporacion": "CONSULTA|PRESIDENCIA|GOBERNACION|ALCALDIA",
    "dept_code": "código 2 dígitos",
    "dept_name": "nombre departamento",
    "muni_code": "código",
    "muni_name": "nombre municipio",
    "zone_code": "código zona",
    "station_code": "código puesto",
    "table_number": número_mesa,
    "place_name": "nombre lugar votación",
    "copy_type": "CLAVEROS|DELEGADOS|TRANSMISION"
  }},

  "nivelacion": {{
    "total_sufragantes_e11": número,
    "total_votos_urna": número,
    "confidence_sufragantes": 0.0-1.0,
    "confidence_urna": 0.0-1.0
  }},

  "ocr_fields": [
    {{
      "field_key": "TOTAL_SUFRAGANTES_E11",
      "page_no": 1,
      "value_int": número,
      "raw_text": "texto exacto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "TOTAL_VOTOS_URNA",
      "page_no": 1,
      "value_int": número,
      "raw_text": "texto exacto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "CANDIDATE_01",
      "page_no": 1,
      "ballot_option_type": "CANDIDATE",
      "political_group_code": "0001",
      "political_group_name": "NOMBRE PARTIDO/MOVIMIENTO",
      "candidate_ordinal": 1,
      "candidate_name": "NOMBRE COMPLETO CANDIDATO",
      "value_int": número_votos,
      "raw_text": "texto leído",
      "raw_mark": null | "*" | "**" | "***",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "VOTOS_EN_BLANCO",
      "page_no": 1,
      "ballot_option_type": "BLANK",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "VOTOS_NULOS",
      "page_no": 1,
      "ballot_option_type": "NULL",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "VOTOS_NO_MARCADOS",
      "page_no": 1,
      "ballot_option_type": "UNMARKED",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "TOTAL_VOTOS_MESA",
      "page_no": 1,
      "ballot_option_type": "TOTAL",
      "value_int": número,
      "raw_text": "texto",
      "confidence": 0.0-1.0,
      "needs_review": false
    }},
    {{
      "field_key": "HUBO_RECUENTO",
      "page_no": {pages_count},
      "value_bool": true|false,
      "raw_text": "SI|NO",
      "confidence": 0.0-1.0
    }},
    {{
      "field_key": "FIRMA_JURADO_1",
      "page_no": {pages_count},
      "value_bool": true,
      "confidence": 0.0-1.0
    }}
  ],

  "metadata": {{
    "total_pages": {pages_count},
    "pages_with_data": número,
    "overall_confidence": 0.0-1.0,
    "fields_needing_review": número,
    "fields_with_marks": [],
    "notes": "observaciones"
  }}
}}

INSTRUCCIONES:
1. Extrae TODOS los candidatos visibles
2. Usa raw_mark para correcciones: "*" tachadura, "**" poco legible, "***" muy dudoso
3. candidate_ordinal es el número de orden del candidato (1, 2, 3...)
4. Incluye el nombre del partido/movimiento en political_group_name"""


# ============================================================
# Servicio principal
# ============================================================

class E14OCRService:
    """Servicio de OCR para E-14 usando Claude Vision."""

    def __init__(self):
        """Inicializa el servicio."""
        self.api_key = Config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")

        # Usar Claude 3.5 Sonnet que tiene buenas capacidades de visión
        self.model = 'claude-sonnet-4-20250514'
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.max_tokens = 16000  # E-14 puede ser largo
        self.timeout = 300  # 5 minutos para PDFs grandes con muchas páginas

        logger.info(f"E14OCRService inicializado con modelo: {self.model}")

    # ============================================================
    # Métodos V2 - Payload estructurado
    # ============================================================

    def process_pdf_v2(
        self,
        pdf_path: Optional[str] = None,
        pdf_url: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        source_type: SourceType = SourceType.WITNESS_UPLOAD,
        corporacion_hint: Optional[str] = None,
    ) -> E14PayloadV2:
        """
        Procesa un PDF de E-14 y genera payload v2 estructurado.

        Args:
            pdf_path: Ruta local al archivo PDF
            pdf_url: URL del PDF
            pdf_bytes: Bytes del PDF
            source_type: Origen del documento
            corporacion_hint: Tipo de corporación si se conoce

        Returns:
            E14PayloadV2 con todos los datos extraídos en formato v2
        """
        start_time = time.time()
        extraction_id = str(uuid.uuid4())
        registry = get_metrics_registry()
        ocr_status = "success"

        try:
            # 1. Obtener el PDF
            if pdf_path:
                pdf_data = Path(pdf_path).read_bytes()
                source_file = Path(pdf_path).name
            elif pdf_url:
                pdf_data = self._download_pdf(pdf_url)
                source_file = pdf_url.split('/')[-1] if '/' in pdf_url else pdf_url
            elif pdf_bytes:
                pdf_data = pdf_bytes
                source_file = f"upload_{extraction_id[:8]}.pdf"
            else:
                raise ValueError("Debe proporcionar pdf_path, pdf_url o pdf_bytes")

            # Registrar tamaño de archivo
            registry.observe("castor_ocr_file_size_bytes", len(pdf_data))

            # 2. Calcular hash
            sha256 = hashlib.sha256(pdf_data).hexdigest()

            # 3. Convertir PDF a imágenes
            images = self._pdf_to_images(pdf_data)
            total_pages = len(images)
            logger.info(f"PDF convertido a {total_pages} imágenes")

            # Registrar páginas procesadas
            registry.observe("castor_ocr_pages_total", total_pages)

            # 4. Llamar a Claude Vision con prompt v2
            raw_result = self._call_claude_vision_v2(images, corporacion_hint)

            # 5. Generar payload v2
            processing_time_ms = int((time.time() - start_time) * 1000)
            payload = self._build_v2_payload(
                raw_result=raw_result,
                extraction_id=extraction_id,
                source_file=source_file,
                source_type=source_type,
                sha256=sha256,
                total_pages=total_pages,
                processing_time_ms=processing_time_ms
            )

            # Registrar métricas de confianza
            overall_confidence = payload.meta.get('overall_confidence', 0.0) if payload.meta else 0.0
            registry.observe("castor_ocr_confidence", overall_confidence, {"field_type": "overall"})

            # Registrar campos que necesitan revisión
            needs_review_count = sum(1 for f in payload.ocr_fields if f.needs_review)
            if needs_review_count > 0:
                for field in payload.ocr_fields:
                    if field.needs_review:
                        reason = "low_confidence" if (field.confidence or 0) < 0.7 else "raw_mark"
                        if field.raw_mark:
                            reason = f"raw_mark_{field.raw_mark}"
                        OCRMetrics.track_needs_review(field.field_key, reason)

            # Registrar validaciones
            for validation in payload.validations:
                ValidationMetrics.track_validation(
                    rule_key=validation.rule_key,
                    passed=validation.passed,
                    severity=validation.severity.value
                )

            return payload

        except Exception as e:
            ocr_status = "error"
            registry.inc("castor_ocr_errors_total", 1, {"error_type": type(e).__name__})
            raise

        finally:
            # Registrar duración total del OCR
            ocr_duration = time.time() - start_time
            registry.observe("castor_ocr_duration_seconds", ocr_duration, {"status": ocr_status})
            registry.inc("castor_ocr_requests_total", 1, {"status": ocr_status})

    def _call_claude_vision_v2(
        self,
        images: List[str],
        corporacion_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Llama a Claude Vision API con prompt v2.

        Args:
            images: Lista de imágenes en base64
            corporacion_hint: Tipo de corporación si se conoce

        Returns:
            Diccionario con el resultado parseado
        """
        # Construir contenido con todas las imágenes
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
            content.append({
                "type": "text",
                "text": f"[Página {i + 1} de {len(images)}]"
            })

        # Agregar prompt de extracción v2
        content.append({
            "type": "text",
            "text": build_extraction_prompt_v2(len(images), corporacion_hint)
        })

        # Llamar a la API
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": SYSTEM_PROMPT_V2,
            "messages": [
                {"role": "user", "content": content}
            ]
        }

        logger.info(f"Llamando a Claude Vision v2 con {len(images)} imágenes...")

        api_start_time = time.time()
        api_status = "success"
        input_tokens = 0
        output_tokens = 0

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                if response.status_code != 200:
                    api_status = "error"
                    logger.error(f"Error de API Anthropic: {response.status_code} - {response.text[:500]}")
                    raise ValueError(f"Error de API: {response.status_code} - {response.text[:200]}")

            result = response.json()

            # Extraer tokens del response para métricas
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)

        except Exception as e:
            api_status = "error"
            raise
        finally:
            # Registrar métricas de Anthropic API
            api_duration = time.time() - api_start_time
            total_tokens = input_tokens + output_tokens

            # Costo estimado: $3/MTok input, $15/MTok output para Claude Sonnet
            cost_usd = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

            OCRMetrics.track_anthropic_request(
                model=self.model,
                status=api_status,
                cost_usd=cost_usd,
                tokens=total_tokens
            )

            # Registrar duración de la llamada API
            registry = get_metrics_registry()
            registry.observe("castor_anthropic_latency_seconds", api_duration, {"model": self.model})

            logger.info(f"Claude Vision v2: {api_status}, {total_tokens} tokens, ${cost_usd:.4f} USD, {api_duration:.2f}s")

        # Extraer texto de la respuesta
        response_text = result['content'][0]['text']

        # Parsear JSON (limpiar markdown code blocks)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON v2 de Claude: {e}")
            logger.debug(f"Respuesta raw: {response_text[:1000]}")
            raise ValueError(f"Claude no retornó JSON válido: {e}")

    def _build_v2_payload(
        self,
        raw_result: Dict[str, Any],
        extraction_id: str,
        source_file: str,
        source_type: SourceType,
        sha256: str,
        total_pages: int,
        processing_time_ms: int
    ) -> E14PayloadV2:
        """Construye el payload v2 completo desde el resultado de Claude."""

        header_data = raw_result.get('header', {})
        nivelacion_data = raw_result.get('nivelacion', {})
        ocr_fields_data = raw_result.get('ocr_fields', [])
        page_mapping = raw_result.get('page_mapping', [])
        metadata = raw_result.get('metadata', {})

        # ============================================================
        # PASO 1: Procesar QR/Barcode como LLAVE PRIMARIA
        # ============================================================
        barcode = header_data.get('barcode') or header_data.get('qr_code')
        qr_data = None
        qr_ocr_mismatches = []

        if barcode:
            qr_data = parse_qr_barcode(barcode)
            logger.info(f"QR parsed: status={qr_data.parse_status.value}, polling_table_id={qr_data.polling_table_id}")

            # Si el QR es válido, usarlo como fuente primaria de identificadores
            if qr_data.parse_status == QRParseStatus.SUCCESS:
                # Sobrescribir header con datos del QR (fuente confiable)
                if qr_data.dept_code:
                    header_data['dept_code'] = qr_data.dept_code
                if qr_data.muni_code:
                    header_data['muni_code'] = qr_data.muni_code
                if qr_data.zone_code:
                    header_data['zone_code'] = qr_data.zone_code
                if qr_data.station_code:
                    header_data['station_code'] = qr_data.station_code
                if qr_data.table_number is not None:
                    header_data['table_number'] = qr_data.table_number

                logger.info(f"Using QR as primary key: {qr_data.polling_table_id}")

            elif qr_data.parse_status == QRParseStatus.PARTIAL:
                # QR parcial - validar contra OCR
                is_valid, qr_ocr_mismatches = validate_qr_against_ocr(qr_data, header_data)
                if not is_valid:
                    logger.warning(f"QR-OCR mismatches detected: {qr_ocr_mismatches}")

        # ============================================================
        # PASO 2: Procesar campos OCR con Alfabeto Electoral
        # ============================================================
        for field in ocr_fields_data:
            raw_text = field.get('raw_text')
            confidence = field.get('confidence', 0.0)

            # Aplicar alfabeto electoral para normalizar
            if raw_text is not None and field.get('value_int') is None:
                parsed = parse_cell_value(raw_text, confidence)
                field['value_int'] = parsed.value
                field['raw_mark'] = parsed.raw_mark or field.get('raw_mark')
                field['needs_review'] = parsed.needs_review or field.get('needs_review', False)

                # Si hay alternativas, guardarlas
                if parsed.alternatives:
                    field['alternatives'] = parsed.alternatives

            # Aplicar umbral de confianza
            if confidence < CONFIDENCE_THRESHOLDS['needs_review'] and not field.get('needs_review'):
                field['needs_review'] = True
                field['notes'] = field.get('notes', '') + f' [confidence={confidence:.2f}]'

        # Determinar tipo de proceso y contienda
        corporacion = header_data.get('corporacion', 'CONSULTA').upper()
        process_type, contest_type, contest_scope = self._determine_process_type(corporacion)

        # Construir pipeline_context
        pipeline_context = PipelineContext(
            target_process=TargetProcess(
                process_type=process_type,
                process_date=header_data.get('election_date', '2026-03-08'),
                contest_type=contest_type,
                contest_scope=contest_scope
            ),
            template_family="E14",
            template_version=self._determine_template_version(corporacion, total_pages),
            ruleset_version="VALIDATION_CORE_V1"
        )

        # Construir input_document
        pages = []
        for pm in page_mapping:
            pages.append(PageInfo(
                page_no=pm.get('page_no', 1),
                political_group_code=pm.get('political_group_code'),
                description=pm.get('description')
            ))
        # Si no hay page_mapping, crear páginas básicas
        if not pages:
            for i in range(1, total_pages + 1):
                pages.append(PageInfo(page_no=i))

        input_document = InputDocument(
            source_file=source_file,
            form_type="E14",
            copy_type=self._parse_copy_type(header_data.get('copy_type', 'CLAVEROS')),
            source_type=source_type,
            sha256=sha256,
            total_pages=total_pages,
            pages=pages
        )

        # Construir document_header_extracted
        document_header = DocumentHeaderExtracted(
            reported_election_date=header_data.get('election_date', '2026-03-08'),
            reported_election_label=header_data.get('election_label', ''),
            corporacion=self._parse_corporacion(corporacion),
            dept_code=header_data.get('dept_code', '00'),
            dept_name=header_data.get('dept_name', 'DESCONOCIDO'),
            muni_code=header_data.get('muni_code', '000'),
            muni_name=header_data.get('muni_name', 'DESCONOCIDO'),
            zone_code=header_data.get('zone_code', '00'),
            station_code=header_data.get('station_code', '00'),
            table_number=int(header_data.get('table_number', 0)),
            place_name=header_data.get('place_name'),
            page_count_reported=header_data.get('page_count_reported')
        )

        # Convertir ocr_fields
        ocr_fields = []
        for field in ocr_fields_data:
            ocr_field = OCRField(
                field_key=field.get('field_key', 'UNKNOWN'),
                page_no=field.get('page_no', 1),
                value_int=field.get('value_int'),
                value_bool=field.get('value_bool'),
                raw_text=field.get('raw_text'),
                raw_mark=field.get('raw_mark'),
                ballot_option_type=self._parse_ballot_option_type(field.get('ballot_option_type')),
                political_group_code=field.get('political_group_code'),
                political_group_name=field.get('political_group_name'),
                candidate_ordinal=field.get('candidate_ordinal'),
                candidate_name=field.get('candidate_name'),
                list_type=self._parse_list_type(field.get('list_type')) if field.get('list_type') else None,
                confidence=field.get('confidence', 0.0),
                needs_review=field.get('needs_review', False),
                notes=field.get('notes')
            )
            ocr_fields.append(ocr_field)

        # Construir normalized_tallies
        normalized_tallies = self._build_normalized_tallies(ocr_fields)

        # Construir validations
        validations = self._build_validations_v2(
            nivelacion_data,
            ocr_fields,
            normalized_tallies,
            metadata
        )

        # Construir db_write_plan
        needs_review_count = sum(1 for f in ocr_fields if f.needs_review)
        db_write_plan = DBWritePlan(
            form_instance={
                "extraction_id": extraction_id,
                "mesa_id": document_header.mesa_id,
                "form_type": "E14",
                "source_type": source_type.value,
                "copy_type": input_document.copy_type.value,
                "total_pages": total_pages,
                "status": "OCR_COMPLETED",
                "processing_time_ms": processing_time_ms
            },
            form_page_rows=f"INSERT {total_pages} rows (una por página)",
            ocr_field_rows=f"INSERT {len(ocr_fields)} rows",
            vote_tally_rows=f"INSERT rows from normalized_tallies",
            validation_result_rows=f"INSERT {len(validations)} rows",
            alert_rows=[
                AlertRow(
                    type="OCR_LOW_CONF",
                    severity=ValidationSeverity.MEDIUM,
                    status="OPEN",
                    evidence={"needs_review_count": needs_review_count}
                )
            ] if needs_review_count > 0 else []
        )

        # ============================================================
        # PASO 3: Crear items de revisión HITL si es necesario
        # ============================================================
        review_items = []
        cells_for_review = [
            {
                'cell_id': f.field_key,
                'field_key': f.field_key,
                'value': f.value_int,
                'confidence': f.confidence,
                'raw_text': f.raw_text,
                'raw_mark': f.raw_mark,
                'page_no': f.page_no,
                'party_code': f.political_group_code,
                'candidate_ordinal': f.candidate_ordinal,
            }
            for f in ocr_fields
        ]

        # Review por baja confianza
        low_conf_review = create_review_item_for_low_confidence(
            form_instance_id=extraction_id,
            mesa_id=document_header.mesa_id,
            cells=cells_for_review,
            threshold=CONFIDENCE_THRESHOLDS['needs_review'],
            department=document_header.dept_code,
            municipality=document_header.muni_code,
            corporacion=corporacion
        )
        if low_conf_review:
            review_items.append(low_conf_review)

        # Review por marcas especiales (**, ***)
        special_marks_review = create_review_item_for_special_marks(
            form_instance_id=extraction_id,
            mesa_id=document_header.mesa_id,
            cells=cells_for_review,
            department=document_header.dept_code,
            municipality=document_header.muni_code,
            corporacion=corporacion
        )
        if special_marks_review:
            review_items.append(special_marks_review)

        # Review por errores aritméticos
        for validation in validations:
            if not validation.passed and validation.rule_key in ['SUM_EQUALS_TOTAL', 'E11_EQUALS_URNA']:
                arith_review = create_review_item_for_arithmetic_mismatch(
                    form_instance_id=extraction_id,
                    mesa_id=document_header.mesa_id,
                    expected_sum=validation.details.get('reported_total', 0) if validation.details else 0,
                    actual_sum=validation.details.get('sum_total', 0) if validation.details else 0,
                    cells=cells_for_review,
                    validation_name=validation.rule_key,
                    department=document_header.dept_code,
                    municipality=document_header.muni_code,
                    corporacion=corporacion
                )
                review_items.append(arith_review)
                break  # Solo crear uno por errores aritméticos

        # Construir payload final
        return E14PayloadV2(
            event_type="ocr.completed",
            schema_version="1.3.0",  # Versión actualizada con QR y HITL
            produced_at=datetime.utcnow(),
            pipeline_context=pipeline_context,
            input_document=input_document,
            document_header_extracted=document_header,
            ocr_fields=ocr_fields,
            normalized_tallies=normalized_tallies,
            validations=validations,
            db_write_plan=db_write_plan,
            meta={
                "extraction_id": extraction_id,
                "model_version": self.model,
                "processing_time_ms": processing_time_ms,
                "overall_confidence": metadata.get('overall_confidence', 0.0),
                "fields_needing_review": needs_review_count,
                "notes": metadata.get('notes'),
                # QR Data
                "qr_parsed": qr_data is not None and qr_data.parse_status == QRParseStatus.SUCCESS,
                "qr_polling_table_id": qr_data.polling_table_id if qr_data else None,
                "qr_ocr_mismatches": qr_ocr_mismatches if qr_ocr_mismatches else None,
                # HITL Review
                "review_items_count": len(review_items),
                "review_items": [
                    {
                        "review_id": r.review_id,
                        "priority": r.priority.name,
                        "reason": r.reason.name,
                        "cells_count": len(r.cells)
                    }
                    for r in review_items
                ] if review_items else None
            }
        )

    def _determine_process_type(self, corporacion: str) -> Tuple[ProcessType, ContestType, ContestScope]:
        """Determina tipo de proceso, contienda y alcance según corporación."""
        mapping = {
            'CONSULTA': (ProcessType.CONSULTA, ContestType.CONSULTA, ContestScope.NATIONAL),
            'PRESIDENCIA': (ProcessType.NACIONAL, ContestType.PRESIDENCY, ContestScope.NATIONAL),
            'SENADO': (ProcessType.NACIONAL, ContestType.SENATE, ContestScope.NATIONAL),
            'CAMARA': (ProcessType.NACIONAL, ContestType.CHAMBER, ContestScope.DEPARTMENTAL),
            'GOBERNACION': (ProcessType.TERRITORIAL, ContestType.GOVERNOR, ContestScope.DEPARTMENTAL),
            'ALCALDIA': (ProcessType.TERRITORIAL, ContestType.MAYOR, ContestScope.MUNICIPAL),
            'ASAMBLEA': (ProcessType.TERRITORIAL, ContestType.ASSEMBLY, ContestScope.DEPARTMENTAL),
            'CONCEJO': (ProcessType.TERRITORIAL, ContestType.COUNCIL, ContestScope.MUNICIPAL),
            'JAL': (ProcessType.TERRITORIAL, ContestType.JAL, ContestScope.LOCAL),
        }
        return mapping.get(corporacion, (ProcessType.CONSULTA, ContestType.CONSULTA, ContestScope.NATIONAL))

    def _determine_template_version(self, corporacion: str, total_pages: int) -> str:
        """Determina la versión de template según corporación y páginas."""
        if corporacion in ['CONSULTA', 'PRESIDENCIA', 'GOBERNACION', 'ALCALDIA']:
            return "E14_CONSULTA_SIMPLE_V1"
        elif corporacion in ['CAMARA', 'SENADO']:
            return f"E14_{corporacion}_MULTIPAGINA_V1"
        elif corporacion in ['ASAMBLEA', 'CONCEJO']:
            return f"E14_{corporacion}_MULTIPAGINA_V1"
        elif total_pages > 2:
            return "E14_MULTIPAGINA_V1"
        else:
            return "E14_SIMPLE_V1"

    def _parse_ballot_option_type(self, value: Optional[str]) -> Optional[BallotOptionType]:
        """Parsea el tipo de opción de boleta."""
        if not value:
            return None
        mapping = {
            'CANDIDATE': BallotOptionType.CANDIDATE,
            'LIST_ONLY': BallotOptionType.LIST_ONLY,
            'LIST_CANDIDATE': BallotOptionType.LIST_CANDIDATE,
            'BLANK': BallotOptionType.BLANK,
            'NULL': BallotOptionType.NULL,
            'UNMARKED': BallotOptionType.UNMARKED,
            'TOTAL': BallotOptionType.TOTAL,
        }
        return mapping.get(value.upper())

    def _build_normalized_tallies(self, ocr_fields: List[OCRField]) -> List[Union[PoliticalGroupTally, SpecialsTally, Dict]]:
        """Construye los tallies normalizados desde los campos OCR."""
        tallies = []

        # Agrupar por political_group_code
        groups: Dict[str, List[OCRField]] = {}
        specials: List[OCRField] = []

        for field in ocr_fields:
            if field.ballot_option_type in [BallotOptionType.BLANK, BallotOptionType.NULL,
                                             BallotOptionType.UNMARKED, BallotOptionType.TOTAL]:
                specials.append(field)
            elif field.political_group_code and field.value_int is not None:
                if field.political_group_code not in groups:
                    groups[field.political_group_code] = []
                groups[field.political_group_code].append(field)

        # Construir tallies por grupo político
        for group_code, fields in groups.items():
            tally_entries = []
            party_total = 0

            for field in fields:
                if field.ballot_option_type == BallotOptionType.LIST_ONLY:
                    tally_entries.append(TallyEntry(
                        subject_type=BallotOptionType.LIST_ONLY,
                        votes=field.value_int or 0
                    ))
                    party_total += field.value_int or 0
                elif field.ballot_option_type == BallotOptionType.LIST_CANDIDATE:
                    tally_entries.append(TallyEntry(
                        subject_type=BallotOptionType.LIST_CANDIDATE,
                        candidate_ordinal=field.candidate_ordinal,
                        votes=field.value_int or 0
                    ))
                    party_total += field.value_int or 0
                elif field.ballot_option_type == BallotOptionType.CANDIDATE:
                    tally_entries.append(TallyEntry(
                        subject_type=BallotOptionType.CANDIDATE,
                        candidate_ordinal=field.candidate_ordinal,
                        votes=field.value_int or 0
                    ))
                    party_total += field.value_int or 0

            if tally_entries:
                tallies.append(PoliticalGroupTally(
                    political_group_code=group_code,
                    tallies=tally_entries,
                    party_total=party_total
                ))

        # Construir tallies especiales
        special_entries = []
        for field in specials:
            if field.value_int is not None:
                special_entries.append(TallyEntry(
                    subject_type=field.ballot_option_type,
                    votes=field.value_int
                ))

        if special_entries:
            tallies.append(SpecialsTally(specials=special_entries))

        return tallies

    def _build_validations_v2(
        self,
        nivelacion_data: Dict,
        ocr_fields: List[OCRField],
        normalized_tallies: List,
        metadata: Dict
    ) -> List[ValidationResultV2]:
        """Construye las validaciones v2."""
        validations = []

        # Obtener valores de nivelación
        sufragantes = nivelacion_data.get('total_sufragantes_e11', 0)
        urna = nivelacion_data.get('total_votos_urna', 0)

        # Regla 1: E11_EQUALS_URNA
        delta = urna - sufragantes
        validations.append(ValidationResultV2(
            rule_key="E11_EQUALS_URNA",
            passed=abs(delta) <= 5,  # Tolerancia de 5 votos
            severity=ValidationSeverity.HIGH if abs(delta) > 5 else ValidationSeverity.INFO,
            details={
                "total_sufragantes_e11": sufragantes,
                "total_urna": urna,
                "delta": delta,
                "note": "Diferencia aceptable" if abs(delta) <= 5 else "Diferencia significativa"
            }
        ))

        # Regla 2: SUM_EQUALS_TOTAL
        sum_parties = 0
        blank = 0
        null_votes = 0
        unmarked = 0
        reported_total = 0

        for tally in normalized_tallies:
            if isinstance(tally, PoliticalGroupTally):
                sum_parties += tally.party_total
            elif isinstance(tally, SpecialsTally):
                for entry in tally.specials:
                    if entry.subject_type == BallotOptionType.BLANK:
                        blank = entry.votes
                    elif entry.subject_type == BallotOptionType.NULL:
                        null_votes = entry.votes
                    elif entry.subject_type == BallotOptionType.UNMARKED:
                        unmarked = entry.votes
                    elif entry.subject_type == BallotOptionType.TOTAL:
                        reported_total = entry.votes

        computed_total = sum_parties + blank + null_votes + unmarked
        sum_passed = computed_total == reported_total or (reported_total == 0 and computed_total == urna)

        validations.append(ValidationResultV2(
            rule_key="SUM_EQUALS_TOTAL",
            passed=sum_passed,
            severity=ValidationSeverity.HIGH if not sum_passed else ValidationSeverity.INFO,
            details={
                "sum_all_parties": sum_parties,
                "blank": blank,
                "null": null_votes,
                "unmarked": unmarked,
                "sum_total": computed_total,
                "reported_total": reported_total if reported_total else urna
            }
        ))

        # Regla 3: LOW_CONFIDENCE_REVIEW_REQUIRED
        needs_review_fields = [f for f in ocr_fields if f.needs_review]
        fields_with_marks = [f.field_key for f in ocr_fields if f.raw_mark]

        validations.append(ValidationResultV2(
            rule_key="LOW_CONFIDENCE_REVIEW_REQUIRED",
            passed=len(needs_review_fields) == 0,
            severity=ValidationSeverity.MEDIUM if needs_review_fields else ValidationSeverity.INFO,
            details={
                "needs_review_count": len(needs_review_fields),
                "fields_with_marks": fields_with_marks,
                "threshold": 0.70
            }
        ))

        return validations

    # ============================================================
    # Método original (V1) - Mantener compatibilidad
    # ============================================================

    def process_pdf(
        self,
        pdf_path: Optional[str] = None,
        pdf_url: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
    ) -> E14ExtractionResult:
        """
        Procesa un PDF de E-14 y extrae datos estructurados.

        Args:
            pdf_path: Ruta local al archivo PDF
            pdf_url: URL del PDF
            pdf_bytes: Bytes del PDF

        Returns:
            E14ExtractionResult con todos los datos extraídos
        """
        start_time = time.time()
        extraction_id = str(uuid.uuid4())
        registry = get_metrics_registry()
        ocr_status = "success"

        try:
            # 1. Obtener el PDF
            if pdf_path:
                pdf_data = Path(pdf_path).read_bytes()
                source_file = pdf_path
            elif pdf_url:
                pdf_data = self._download_pdf(pdf_url)
                source_file = pdf_url
            elif pdf_bytes:
                pdf_data = pdf_bytes
                source_file = "uploaded_bytes"
            else:
                raise ValueError("Debe proporcionar pdf_path, pdf_url o pdf_bytes")

            # Registrar tamaño de archivo
            registry.observe("castor_ocr_file_size_bytes", len(pdf_data))

            # 2. Calcular hash
            sha256 = hashlib.sha256(pdf_data).hexdigest()

            # 3. Convertir PDF a imágenes
            images = self._pdf_to_images(pdf_data)
            logger.info(f"PDF convertido a {len(images)} imágenes")

            # Registrar páginas procesadas
            registry.observe("castor_ocr_pages_total", len(images))

            # 4. Llamar a Claude Vision
            raw_result = self._call_claude_vision(images)

            # 5. Parsear resultado
            extraction = self._parse_extraction_result(
                raw_result=raw_result,
                extraction_id=extraction_id,
                source_file=source_file,
                sha256=sha256,
                total_pages=len(images),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

            # Registrar métricas de confianza
            registry.observe("castor_ocr_confidence", extraction.overall_confidence, {"field_type": "overall"})

            # Registrar campos que necesitan revisión
            if extraction.fields_needing_review > 0:
                for partido in extraction.partidos:
                    if partido.needs_review:
                        OCRMetrics.track_needs_review(f"party_{partido.party_code}", "low_confidence")
                    for candidato in partido.votos_candidatos:
                        if candidato.needs_review:
                            OCRMetrics.track_needs_review(
                                f"candidate_{candidato.candidate_number}",
                                "low_confidence"
                            )

            return extraction

        except Exception as e:
            ocr_status = "error"
            registry.inc("castor_ocr_errors_total", 1, {"error_type": type(e).__name__})
            raise

        finally:
            # Registrar duración total del OCR
            ocr_duration = time.time() - start_time
            registry.observe("castor_ocr_duration_seconds", ocr_duration, {"status": ocr_status})
            registry.inc("castor_ocr_requests_total", 1, {"status": ocr_status})

    def _download_pdf(self, url: str) -> bytes:
        """Descarga un PDF desde una URL."""
        logger.info(f"Descargando PDF desde: {url}")
        with httpx.Client(timeout=60) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    def _pdf_to_images(self, pdf_data: bytes) -> List[str]:
        """
        Convierte PDF a lista de imágenes en base64 con preprocesamiento.

        Pipeline mejorado basado en TySE:
        1. PDF → Imagen con DPI optimizado
        2. Preprocesamiento: contraste, brillo, nitidez, edge enhance
        3. Conversión a base64

        Returns:
            Lista de strings base64 (una por página)
        """
        try:
            from pdf2image import convert_from_bytes
            import io

            # Convertir PDF a imágenes PIL con DPI optimizado
            pil_images = convert_from_bytes(
                pdf_data,
                dpi=200,  # Optimizado para OCR de dígitos manuscritos
                fmt='PNG'
            )

            # Convertir a base64 con preprocesamiento
            base64_images = []
            for img in pil_images:
                # Aplicar preprocesamiento
                processed_img = self._preprocess_image(img)

                buffer = io.BytesIO()
                processed_img.save(buffer, format='PNG', optimize=True)
                base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                base64_images.append(base64_str)

            return base64_images

        except ImportError:
            logger.error("pdf2image no instalado. Ejecutar: pip install pdf2image")
            raise
        except Exception as e:
            logger.error(f"Error convirtiendo PDF a imágenes: {e}")
            raise

    def _preprocess_image(self, img) -> 'Image.Image':
        """
        Preprocesamiento de imagen para mejorar OCR de dígitos manuscritos.

        Pipeline basado en TySE:
        - Contraste +30% (dígitos más definidos)
        - Brillo +10% (fondo más claro)
        - Nitidez +50% (bordes más nítidos)
        - Edge enhance (definir trazos)

        Args:
            img: PIL Image

        Returns:
            PIL Image preprocesada
        """
        from PIL import Image, ImageEnhance, ImageFilter

        # 1. Convertir a RGB si es necesario
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 2. Aumentar contraste (30%) - hace los dígitos más oscuros
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)

        # 3. Aumentar brillo (10%) - aclara el fondo
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

        # 4. Aumentar nitidez (50%) - define bordes de dígitos
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)

        # 5. Edge enhance - resalta trazos manuscritos
        img = img.filter(ImageFilter.EDGE_ENHANCE)

        return img

    def _call_claude_vision(self, images: List[str]) -> Dict[str, Any]:
        """
        Llama a Claude Vision API con las imágenes del E-14.

        Args:
            images: Lista de imágenes en base64

        Returns:
            Diccionario con el resultado parseado
        """
        # Construir contenido con todas las imágenes
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
            content.append({
                "type": "text",
                "text": f"[Página {i + 1} de {len(images)}]"
            })

        # Agregar prompt de extracción
        content.append({
            "type": "text",
            "text": build_extraction_prompt(len(images))
        })

        # Llamar a la API
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": content}
            ]
        }

        logger.info(f"Llamando a Claude Vision con {len(images)} imágenes...")

        api_start_time = time.time()
        api_status = "success"
        input_tokens = 0
        output_tokens = 0

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                if response.status_code != 200:
                    api_status = "error"
                    logger.error(f"Error de API Anthropic: {response.status_code} - {response.text[:500]}")
                    raise ValueError(f"Error de API: {response.status_code} - {response.text[:200]}")

            result = response.json()

            # Extraer tokens del response para métricas
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)

        except Exception as e:
            api_status = "error"
            raise
        finally:
            # Registrar métricas de Anthropic API
            api_duration = time.time() - api_start_time
            total_tokens = input_tokens + output_tokens

            # Costo estimado: $3/MTok input, $15/MTok output para Claude Sonnet
            cost_usd = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

            OCRMetrics.track_anthropic_request(
                model=self.model,
                status=api_status,
                cost_usd=cost_usd,
                tokens=total_tokens
            )

            # Registrar duración de la llamada API
            registry = get_metrics_registry()
            registry.observe("castor_anthropic_latency_seconds", api_duration, {"model": self.model})

            logger.info(f"Claude Vision v1: {api_status}, {total_tokens} tokens, ${cost_usd:.4f} USD, {api_duration:.2f}s")

        # Extraer texto de la respuesta
        response_text = result['content'][0]['text']

        # Parsear JSON
        # Limpiar posibles markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Claude: {e}")
            logger.debug(f"Respuesta raw: {response_text[:1000]}")
            raise ValueError(f"Claude no retornó JSON válido: {e}")

    def _parse_extraction_result(
        self,
        raw_result: Dict[str, Any],
        extraction_id: str,
        source_file: str,
        sha256: str,
        total_pages: int,
        processing_time_ms: int
    ) -> E14ExtractionResult:
        """Convierte el resultado raw de Claude a E14ExtractionResult."""

        header_data = raw_result.get('header', {})
        nivelacion_data = raw_result.get('nivelacion', {})
        partidos_data = raw_result.get('partidos', [])
        especiales_data = raw_result.get('votos_especiales', {})
        constancias_data = raw_result.get('constancias', {})
        metadata = raw_result.get('metadata', {})

        # Parsear header
        header = E14Header(
            barcode=header_data.get('barcode'),
            version=header_data.get('version'),
            page_info=header_data.get('page_info'),
            copy_type=self._parse_copy_type(header_data.get('copy_type', 'CLAVEROS')),
            election_name=header_data.get('election_name'),
            election_date=header_data.get('election_date'),
            corporacion=self._parse_corporacion(header_data.get('corporacion', 'CAMARA')),
            departamento_code=header_data.get('departamento_code', '00'),
            departamento_name=header_data.get('departamento_name', 'DESCONOCIDO'),
            municipio_code=header_data.get('municipio_code', '000'),
            municipio_name=header_data.get('municipio_name', 'DESCONOCIDO'),
            lugar=header_data.get('lugar'),
            zona=header_data.get('zona', '00'),
            puesto=header_data.get('puesto', '00'),
            mesa=header_data.get('mesa', '000')
        )

        # Parsear nivelación
        nivelacion = NivelacionMesa(
            total_sufragantes_e11=nivelacion_data.get('total_sufragantes_e11', 0),
            total_votos_urna=nivelacion_data.get('total_votos_urna', 0),
            total_votos_incinerados=nivelacion_data.get('total_votos_incinerados'),
            confidence_sufragantes=nivelacion_data.get('confidence_sufragantes'),
            confidence_urna=nivelacion_data.get('confidence_urna')
        )

        # Parsear partidos
        partidos = []
        for p in partidos_data:
            candidatos = []
            for c in p.get('votos_candidatos', []):
                candidatos.append(CandidateVotes(
                    candidate_number=str(c.get('candidate_number', '0')),
                    votes=c.get('votes', 0),
                    confidence=c.get('confidence'),
                    needs_review=c.get('needs_review', False)
                ))

            partidos.append(PartyVotes(
                party_code=p.get('party_code', '0000'),
                party_name=p.get('party_name', 'DESCONOCIDO'),
                list_type=self._parse_list_type(p.get('list_type', 'SIN_VOTO_PREFERENTE')),
                circunscripcion=self._parse_circunscripcion(p.get('circunscripcion', 'TERRITORIAL')),
                votos_agrupacion=p.get('votos_agrupacion', 0),
                votos_candidatos=candidatos,
                total_votos=p.get('total_votos', 0),
                confidence_total=p.get('confidence_total'),
                needs_review=p.get('needs_review', False)
            ))

        # Parsear votos especiales
        votos_especiales = VotosEspeciales(
            votos_blanco=especiales_data.get('votos_blanco', 0),
            votos_nulos=especiales_data.get('votos_nulos', 0),
            votos_no_marcados=especiales_data.get('votos_no_marcados', 0),
            confidence_blanco=especiales_data.get('confidence_blanco'),
            confidence_nulos=especiales_data.get('confidence_nulos'),
            confidence_no_marcados=especiales_data.get('confidence_no_marcados')
        )

        # Parsear constancias
        constancias = None
        if constancias_data:
            constancias = ConstanciasMesa(
                hubo_recuento=constancias_data.get('hubo_recuento'),
                recuento_solicitado_por=constancias_data.get('recuento_solicitado_por'),
                otras_constancias=constancias_data.get('otras_constancias'),
                num_jurados_firmantes=constancias_data.get('num_jurados_firmantes', 0)
            )

        return E14ExtractionResult(
            extraction_id=extraction_id,
            source_file=source_file,
            source_sha256=sha256,
            extracted_at=datetime.utcnow(),
            model_version=self.model,
            processing_time_ms=processing_time_ms,
            header=header,
            nivelacion=nivelacion,
            partidos=partidos,
            votos_especiales=votos_especiales,
            constancias=constancias,
            overall_confidence=metadata.get('overall_confidence', 0.0),
            fields_needing_review=metadata.get('fields_needing_review', 0),
            total_pages=total_pages,
            pages_processed=metadata.get('pages_with_data', total_pages)
        )

    def _parse_copy_type(self, value: str) -> CopyType:
        """Parsea el tipo de copia."""
        mapping = {
            'CLAVEROS': CopyType.CLAVEROS,
            'DELEGADOS': CopyType.DELEGADOS,
            'TRANSMISION': CopyType.TRANSMISION,
        }
        return mapping.get(value.upper(), CopyType.CLAVEROS)

    def _parse_corporacion(self, value: str) -> Corporacion:
        """Parsea la corporación."""
        mapping = {
            'CAMARA': Corporacion.CAMARA,
            'CÁMARA': Corporacion.CAMARA,
            'SENADO': Corporacion.SENADO,
            'PRESIDENCIA': Corporacion.PRESIDENCIA,
            'GOBERNACION': Corporacion.GOBERNACION,
            'GOBERNACIÓN': Corporacion.GOBERNACION,
            'ALCALDIA': Corporacion.ALCALDIA,
            'ALCALDÍA': Corporacion.ALCALDIA,
            'ASAMBLEA': Corporacion.ASAMBLEA,
            'CONCEJO': Corporacion.CONCEJO,
            'JAL': Corporacion.JAL,
            'CONSULTA': Corporacion.CONSULTA,
        }
        return mapping.get(value.upper(), Corporacion.CAMARA)

    def _parse_list_type(self, value: str) -> ListType:
        """Parsea el tipo de lista."""
        if 'CON' in value.upper():
            return ListType.CON_VOTO_PREFERENTE
        return ListType.SIN_VOTO_PREFERENTE

    def _parse_circunscripcion(self, value: str) -> CircunscripcionType:
        """Parsea la circunscripción."""
        value_upper = value.upper()
        if 'INDIGENA' in value_upper or 'INDÍGENA' in value_upper:
            return CircunscripcionType.ESPECIAL_INDIGENA
        if 'AFRO' in value_upper:
            return CircunscripcionType.ESPECIAL_AFRO
        return CircunscripcionType.TERRITORIAL

    def validate_extraction(self, extraction: E14ExtractionResult) -> E14ValidationReport:
        """
        Valida la consistencia del E-14 extraído.

        Args:
            extraction: Resultado de extracción a validar

        Returns:
            E14ValidationReport con todas las validaciones
        """
        start_time = time.time()
        validations = []

        # Regla 1: Nivelación (sufragantes vs urna)
        validations.append(self._validate_nivelacion(extraction))

        # Regla 2: Suma de votos = total urna
        validations.append(self._validate_sum_total(extraction))

        # Regla 3: Total por partido = agrupación + candidatos
        for partido in extraction.partidos:
            validations.append(self._validate_party_sum(partido))

        # Regla 4: Votos no exceden sufragantes
        validations.append(self._validate_not_exceeds_voters(extraction))

        # Calcular métricas
        all_passed = all(v.passed for v in validations)
        critical_failures = sum(1 for v in validations if not v.passed and v.severity == ValidationSeverity.CRITICAL)
        high_failures = sum(1 for v in validations if not v.passed and v.severity == ValidationSeverity.HIGH)
        medium_failures = sum(1 for v in validations if not v.passed and v.severity == ValidationSeverity.MEDIUM)
        low_failures = sum(1 for v in validations if not v.passed and v.severity == ValidationSeverity.LOW)

        # Generar alertas
        alerts = []
        for v in validations:
            if not v.passed:
                alerts.append(f"{v.severity.value}: {v.rule_name} - {v.message}")

        # Registrar métricas de validación
        for v in validations:
            ValidationMetrics.track_validation(
                rule_key=v.rule_id,
                passed=v.passed,
                severity=v.severity.value
            )

        # Registrar alertas generadas
        department = extraction.header.departamento_code
        for v in validations:
            if not v.passed:
                ValidationMetrics.track_alert(
                    alert_type=v.rule_name,
                    severity=v.severity.value,
                    department=department
                )

        # Registrar duración de validación
        validation_duration = time.time() - start_time
        registry = get_metrics_registry()
        registry.observe("castor_validation_duration_seconds", validation_duration)

        return E14ValidationReport(
            extraction_id=extraction.extraction_id,
            mesa_id=extraction.header.mesa_id,
            validations=validations,
            all_passed=all_passed,
            critical_failures=critical_failures,
            high_failures=high_failures,
            medium_failures=medium_failures,
            low_failures=low_failures,
            alerts_generated=alerts
        )

    def _validate_nivelacion(self, extraction: E14ExtractionResult) -> ValidationResult:
        """Valida que sufragantes E-11 >= votos en urna."""
        sufragantes = extraction.nivelacion.total_sufragantes_e11
        urna = extraction.nivelacion.total_votos_urna

        passed = sufragantes >= urna
        delta = urna - sufragantes if not passed else 0

        return ValidationResult(
            rule_id="NIV_001",
            rule_name="NIVELACION_SUFRAGANTES_VS_URNA",
            passed=passed,
            severity=ValidationSeverity.HIGH if not passed else ValidationSeverity.INFO,
            message=f"Sufragantes E-11 ({sufragantes}) {'≥' if passed else '<'} Votos urna ({urna})",
            expected_value=sufragantes,
            actual_value=urna,
            delta=delta
        )

    def _validate_sum_total(self, extraction: E14ExtractionResult) -> ValidationResult:
        """Valida que suma de todos los votos = total urna."""
        total_urna = extraction.nivelacion.total_votos_urna
        total_computado = extraction.total_computado

        passed = total_computado == total_urna
        delta = total_computado - total_urna

        severity = ValidationSeverity.INFO if passed else (
            ValidationSeverity.HIGH if abs(delta) > 5 else ValidationSeverity.MEDIUM
        )

        return ValidationResult(
            rule_id="SUM_001",
            rule_name="SUMA_VOTOS_IGUAL_URNA",
            passed=passed,
            severity=severity,
            message=f"Suma computada ({total_computado}) {'=' if passed else '≠'} Urna ({total_urna}). Delta: {delta}",
            expected_value=total_urna,
            actual_value=total_computado,
            delta=delta,
            details={
                "total_partidos": extraction.total_votos_partidos,
                "votos_blanco": extraction.votos_especiales.votos_blanco,
                "votos_nulos": extraction.votos_especiales.votos_nulos,
                "votos_no_marcados": extraction.votos_especiales.votos_no_marcados
            }
        )

    def _validate_party_sum(self, partido: PartyVotes) -> ValidationResult:
        """Valida que total partido = agrupación + candidatos."""
        expected = partido.votos_agrupacion + sum(c.votes for c in partido.votos_candidatos)
        actual = partido.total_votos

        passed = expected == actual
        delta = actual - expected

        return ValidationResult(
            rule_id=f"PARTY_{partido.party_code}",
            rule_name=f"SUMA_PARTIDO_{partido.party_code}",
            passed=passed,
            severity=ValidationSeverity.MEDIUM if not passed else ValidationSeverity.INFO,
            message=f"{partido.party_name}: Agrupación + Candidatos ({expected}) {'=' if passed else '≠'} Total ({actual})",
            expected_value=expected,
            actual_value=actual,
            delta=delta
        )

    def _validate_not_exceeds_voters(self, extraction: E14ExtractionResult) -> ValidationResult:
        """Valida que ningún partido tenga más votos que sufragantes."""
        sufragantes = extraction.nivelacion.total_sufragantes_e11
        exceeds = []

        for partido in extraction.partidos:
            if partido.total_votos > sufragantes:
                exceeds.append(f"{partido.party_name}: {partido.total_votos}")

        passed = len(exceeds) == 0

        return ValidationResult(
            rule_id="EXCEED_001",
            rule_name="VOTOS_NO_EXCEDEN_SUFRAGANTES",
            passed=passed,
            severity=ValidationSeverity.CRITICAL if not passed else ValidationSeverity.INFO,
            message=f"{'Ningún partido excede sufragantes' if passed else f'Partidos exceden: {exceeds}'}",
            details={"partidos_exceden": exceeds} if exceeds else None
        )


# ============================================================
# Singleton para el servicio
# ============================================================

_e14_ocr_service: Optional[E14OCRService] = None


def get_e14_ocr_service() -> E14OCRService:
    """Obtiene instancia singleton del servicio E14 OCR."""
    global _e14_ocr_service
    if _e14_ocr_service is None:
        _e14_ocr_service = E14OCRService()
    return _e14_ocr_service


# ============================================================
# Utilidades para exportar payloads v2
# ============================================================

def save_payload_v2_json(payload: E14PayloadV2, output_path: str) -> str:
    """
    Guarda un payload v2 como archivo JSON.

    Args:
        payload: E14PayloadV2 a guardar
        output_path: Ruta de salida

    Returns:
        Ruta del archivo guardado
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(
            payload.dict(by_alias=True, exclude_none=True),
            f,
            indent=2,
            ensure_ascii=False,
            default=str  # Para datetime y enums
        )

    logger.info(f"Payload v2 guardado en: {output_file}")
    return str(output_file)


def _determine_process_type_static(corporacion: str) -> Tuple[ProcessType, ContestType, ContestScope]:
    """Determina tipo de proceso, contienda y alcance según corporación (versión estática)."""
    mapping = {
        'CONSULTA': (ProcessType.CONSULTA, ContestType.CONSULTA, ContestScope.NATIONAL),
        'PRESIDENCIA': (ProcessType.NACIONAL, ContestType.PRESIDENCY, ContestScope.NATIONAL),
        'SENADO': (ProcessType.NACIONAL, ContestType.SENATE, ContestScope.NATIONAL),
        'CAMARA': (ProcessType.NACIONAL, ContestType.CHAMBER, ContestScope.DEPARTMENTAL),
        'GOBERNACION': (ProcessType.TERRITORIAL, ContestType.GOVERNOR, ContestScope.DEPARTMENTAL),
        'ALCALDIA': (ProcessType.TERRITORIAL, ContestType.MAYOR, ContestScope.MUNICIPAL),
        'ASAMBLEA': (ProcessType.TERRITORIAL, ContestType.ASSEMBLY, ContestScope.DEPARTMENTAL),
        'CONCEJO': (ProcessType.TERRITORIAL, ContestType.COUNCIL, ContestScope.MUNICIPAL),
        'JAL': (ProcessType.TERRITORIAL, ContestType.JAL, ContestScope.LOCAL),
    }
    return mapping.get(corporacion, (ProcessType.CONSULTA, ContestType.CONSULTA, ContestScope.NATIONAL))


def _determine_template_version_static(corporacion: str, total_pages: int) -> str:
    """Determina la versión de template según corporación y páginas (versión estática)."""
    if corporacion in ['CONSULTA', 'PRESIDENCIA', 'GOBERNACION', 'ALCALDIA']:
        return "E14_CONSULTA_SIMPLE_V1"
    elif corporacion in ['CAMARA', 'SENADO']:
        return f"E14_{corporacion}_MULTIPAGINA_V1"
    elif corporacion in ['ASAMBLEA', 'CONCEJO']:
        return f"E14_{corporacion}_MULTIPAGINA_V1"
    elif total_pages > 2:
        return "E14_MULTIPAGINA_V1"
    else:
        return "E14_SIMPLE_V1"


def _build_normalized_tallies_static(ocr_fields: List[OCRField]) -> List[Union[PoliticalGroupTally, SpecialsTally, Dict]]:
    """Construye los tallies normalizados desde los campos OCR (versión estática)."""
    tallies = []

    # Agrupar por political_group_code
    groups: Dict[str, List[OCRField]] = {}
    specials: List[OCRField] = []

    for field in ocr_fields:
        if field.ballot_option_type in [BallotOptionType.BLANK, BallotOptionType.NULL,
                                         BallotOptionType.UNMARKED, BallotOptionType.TOTAL]:
            specials.append(field)
        elif field.political_group_code and field.value_int is not None:
            if field.political_group_code not in groups:
                groups[field.political_group_code] = []
            groups[field.political_group_code].append(field)

    # Construir tallies por grupo político
    for group_code, fields in groups.items():
        tally_entries = []
        party_total = 0

        for field in fields:
            if field.ballot_option_type == BallotOptionType.LIST_ONLY:
                tally_entries.append(TallyEntry(
                    subject_type=BallotOptionType.LIST_ONLY,
                    votes=field.value_int or 0
                ))
                party_total += field.value_int or 0
            elif field.ballot_option_type == BallotOptionType.LIST_CANDIDATE:
                tally_entries.append(TallyEntry(
                    subject_type=BallotOptionType.LIST_CANDIDATE,
                    candidate_ordinal=field.candidate_ordinal,
                    votes=field.value_int or 0
                ))
                party_total += field.value_int or 0
            elif field.ballot_option_type == BallotOptionType.CANDIDATE:
                tally_entries.append(TallyEntry(
                    subject_type=BallotOptionType.CANDIDATE,
                    candidate_ordinal=field.candidate_ordinal,
                    votes=field.value_int or 0
                ))
                party_total += field.value_int or 0

        if tally_entries:
            tallies.append(PoliticalGroupTally(
                political_group_code=group_code,
                tallies=tally_entries,
                party_total=party_total
            ))

    # Construir tallies especiales
    special_entries = []
    for field in specials:
        if field.value_int is not None:
            special_entries.append(TallyEntry(
                subject_type=field.ballot_option_type,
                votes=field.value_int
            ))

    if special_entries:
        tallies.append(SpecialsTally(specials=special_entries))

    return tallies


def _build_validations_v2_static(
    nivelacion_data: Dict,
    ocr_fields: List[OCRField],
    normalized_tallies: List,
    metadata: Dict
) -> List[ValidationResultV2]:
    """Construye las validaciones v2 (versión estática)."""
    validations = []

    # Obtener valores de nivelación
    sufragantes = nivelacion_data.get('total_sufragantes_e11', 0)
    urna = nivelacion_data.get('total_votos_urna', 0)

    # Regla 1: E11_EQUALS_URNA
    delta = urna - sufragantes
    validations.append(ValidationResultV2(
        rule_key="E11_EQUALS_URNA",
        passed=abs(delta) <= 5,  # Tolerancia de 5 votos
        severity=ValidationSeverity.HIGH if abs(delta) > 5 else ValidationSeverity.INFO,
        details={
            "total_sufragantes_e11": sufragantes,
            "total_urna": urna,
            "delta": delta,
            "note": "Diferencia aceptable" if abs(delta) <= 5 else "Diferencia significativa"
        }
    ))

    # Regla 2: SUM_EQUALS_TOTAL
    sum_parties = 0
    blank = 0
    null_votes = 0
    unmarked = 0
    reported_total = 0

    for tally in normalized_tallies:
        if isinstance(tally, PoliticalGroupTally):
            sum_parties += tally.party_total
        elif isinstance(tally, SpecialsTally):
            for entry in tally.specials:
                if entry.subject_type == BallotOptionType.BLANK:
                    blank = entry.votes
                elif entry.subject_type == BallotOptionType.NULL:
                    null_votes = entry.votes
                elif entry.subject_type == BallotOptionType.UNMARKED:
                    unmarked = entry.votes
                elif entry.subject_type == BallotOptionType.TOTAL:
                    reported_total = entry.votes

    computed_total = sum_parties + blank + null_votes + unmarked
    sum_passed = computed_total == reported_total or (reported_total == 0 and computed_total == urna)

    validations.append(ValidationResultV2(
        rule_key="SUM_EQUALS_TOTAL",
        passed=sum_passed,
        severity=ValidationSeverity.HIGH if not sum_passed else ValidationSeverity.INFO,
        details={
            "sum_all_parties": sum_parties,
            "blank": blank,
            "null": null_votes,
            "unmarked": unmarked,
            "sum_total": computed_total,
            "reported_total": reported_total if reported_total else urna
        }
    ))

    # Regla 3: LOW_CONFIDENCE_REVIEW_REQUIRED
    needs_review_fields = [f for f in ocr_fields if f.needs_review]
    fields_with_marks = [f.field_key for f in ocr_fields if f.raw_mark]

    validations.append(ValidationResultV2(
        rule_key="LOW_CONFIDENCE_REVIEW_REQUIRED",
        passed=len(needs_review_fields) == 0,
        severity=ValidationSeverity.MEDIUM if needs_review_fields else ValidationSeverity.INFO,
        details={
            "needs_review_count": len(needs_review_fields),
            "fields_with_marks": fields_with_marks,
            "threshold": 0.70
        }
    ))

    return validations


def convert_v1_to_v2(extraction: E14ExtractionResult) -> E14PayloadV2:
    """
    Convierte un resultado de extracción v1 a payload v2.

    Args:
        extraction: E14ExtractionResult (v1)

    Returns:
        E14PayloadV2
    """
    # Determinar tipo de proceso (sin necesitar el servicio)
    corporacion = extraction.header.corporacion.value
    process_type, contest_type, contest_scope = _determine_process_type_static(corporacion)

    # Construir pipeline_context
    pipeline_context = PipelineContext(
        target_process=TargetProcess(
            process_type=process_type,
            process_date=extraction.header.election_date or "2026-03-08",
            contest_type=contest_type,
            contest_scope=contest_scope
        ),
        template_family="E14",
        template_version=_determine_template_version_static(corporacion, extraction.total_pages),
        ruleset_version="VALIDATION_CORE_V1"
    )

    # Construir input_document
    pages = [PageInfo(page_no=i) for i in range(1, extraction.total_pages + 1)]
    input_document = InputDocument(
        source_file=extraction.source_file,
        form_type="E14",
        copy_type=extraction.header.copy_type,
        source_type=SourceType.WITNESS_UPLOAD,
        sha256=extraction.source_sha256,
        total_pages=extraction.total_pages,
        pages=pages
    )

    # Construir document_header
    document_header = DocumentHeaderExtracted(
        reported_election_date=extraction.header.election_date or "2026-03-08",
        reported_election_label=extraction.header.election_name or "",
        corporacion=extraction.header.corporacion,
        dept_code=extraction.header.departamento_code,
        dept_name=extraction.header.departamento_name,
        muni_code=extraction.header.municipio_code,
        muni_name=extraction.header.municipio_name,
        zone_code=extraction.header.zona,
        station_code=extraction.header.puesto,
        table_number=int(extraction.header.mesa) if extraction.header.mesa.isdigit() else 0,
        place_name=extraction.header.lugar
    )

    # Construir ocr_fields desde v1
    ocr_fields = []

    # Nivelación
    ocr_fields.append(OCRField(
        field_key="TOTAL_SUFRAGANTES_E11",
        page_no=1,
        value_int=extraction.nivelacion.total_sufragantes_e11,
        confidence=extraction.nivelacion.confidence_sufragantes or 0.9,
        needs_review=False
    ))
    ocr_fields.append(OCRField(
        field_key="TOTAL_VOTOS_URNA",
        page_no=1,
        value_int=extraction.nivelacion.total_votos_urna,
        confidence=extraction.nivelacion.confidence_urna or 0.9,
        needs_review=False
    ))

    # Partidos
    for partido in extraction.partidos:
        page_no = 1  # Simplificado para v1->v2

        # Si tiene voto preferente
        if partido.list_type == ListType.CON_VOTO_PREFERENTE:
            # LIST_ONLY votes
            ocr_fields.append(OCRField(
                field_key="LIST_ONLY_VOTES",
                page_no=page_no,
                ballot_option_type=BallotOptionType.LIST_ONLY,
                political_group_code=partido.party_code,
                political_group_name=partido.party_name,
                value_int=partido.votos_agrupacion,
                confidence=partido.confidence_total or 0.9,
                needs_review=partido.needs_review
            ))

            # Candidatos
            for candidato in partido.votos_candidatos:
                ordinal = int(candidato.candidate_number) if candidato.candidate_number.isdigit() else 0
                ocr_fields.append(OCRField(
                    field_key=f"CANDIDATE_{ordinal}",
                    page_no=page_no,
                    ballot_option_type=BallotOptionType.LIST_CANDIDATE,
                    political_group_code=partido.party_code,
                    candidate_ordinal=ordinal,
                    value_int=candidato.votes,
                    confidence=candidato.confidence or 0.9,
                    needs_review=candidato.needs_review
                ))
        else:
            # Sin voto preferente - solo total
            ocr_fields.append(OCRField(
                field_key=f"CANDIDATE_{partido.party_code}",
                page_no=page_no,
                ballot_option_type=BallotOptionType.CANDIDATE,
                political_group_code=partido.party_code,
                political_group_name=partido.party_name,
                value_int=partido.total_votos,
                confidence=partido.confidence_total or 0.9,
                needs_review=partido.needs_review
            ))

    # Votos especiales
    last_page = extraction.total_pages
    ocr_fields.append(OCRField(
        field_key="VOTOS_EN_BLANCO",
        page_no=last_page,
        ballot_option_type=BallotOptionType.BLANK,
        value_int=extraction.votos_especiales.votos_blanco,
        confidence=extraction.votos_especiales.confidence_blanco or 0.9,
        needs_review=False
    ))
    ocr_fields.append(OCRField(
        field_key="VOTOS_NULOS",
        page_no=last_page,
        ballot_option_type=BallotOptionType.NULL,
        value_int=extraction.votos_especiales.votos_nulos,
        confidence=extraction.votos_especiales.confidence_nulos or 0.9,
        needs_review=False
    ))
    ocr_fields.append(OCRField(
        field_key="VOTOS_NO_MARCADOS",
        page_no=last_page,
        ballot_option_type=BallotOptionType.UNMARKED,
        value_int=extraction.votos_especiales.votos_no_marcados,
        confidence=extraction.votos_especiales.confidence_no_marcados or 0.9,
        needs_review=False
    ))
    ocr_fields.append(OCRField(
        field_key="TOTAL_VOTOS_MESA",
        page_no=last_page,
        ballot_option_type=BallotOptionType.TOTAL,
        value_int=extraction.total_computado,
        confidence=0.9,
        needs_review=False
    ))

    # Construir normalized_tallies (usando función estática)
    normalized_tallies = _build_normalized_tallies_static(ocr_fields)

    # Construir validations (usando función estática)
    validations = _build_validations_v2_static(
        {
            'total_sufragantes_e11': extraction.nivelacion.total_sufragantes_e11,
            'total_votos_urna': extraction.nivelacion.total_votos_urna
        },
        ocr_fields,
        normalized_tallies,
        {'overall_confidence': extraction.overall_confidence}
    )

    # DB Write Plan
    needs_review_count = extraction.fields_needing_review
    db_write_plan = DBWritePlan(
        form_instance={
            "extraction_id": extraction.extraction_id,
            "mesa_id": extraction.header.mesa_id,
            "form_type": "E14",
            "source_type": "WITNESS_UPLOAD",
            "copy_type": extraction.header.copy_type.value,
            "total_pages": extraction.total_pages,
            "status": "OCR_COMPLETED",
            "processing_time_ms": extraction.processing_time_ms
        },
        form_page_rows=f"INSERT {extraction.total_pages} rows",
        ocr_field_rows=f"INSERT {len(ocr_fields)} rows",
        vote_tally_rows="INSERT rows from normalized_tallies",
        validation_result_rows=f"INSERT {len(validations)} rows",
        alert_rows=[
            AlertRow(
                type="OCR_LOW_CONF",
                severity=ValidationSeverity.MEDIUM,
                status="OPEN",
                evidence={"needs_review_count": needs_review_count}
            )
        ] if needs_review_count > 0 else []
    )

    return E14PayloadV2(
        event_type="ocr.completed",
        schema_version="1.2.0",
        produced_at=extraction.extracted_at,
        pipeline_context=pipeline_context,
        input_document=input_document,
        document_header_extracted=document_header,
        ocr_fields=ocr_fields,
        normalized_tallies=normalized_tallies,
        validations=validations,
        db_write_plan=db_write_plan,
        meta={
            "extraction_id": extraction.extraction_id,
            "model_version": extraction.model_version,
            "processing_time_ms": extraction.processing_time_ms,
            "overall_confidence": extraction.overall_confidence,
            "fields_needing_review": extraction.fields_needing_review,
            "converted_from": "v1"
        }
    )


def batch_process_pdfs_v2(
    pdf_paths: List[str],
    output_dir: str,
    source_type: SourceType = SourceType.WITNESS_UPLOAD
) -> Dict[str, Any]:
    """
    Procesa múltiples PDFs y genera payloads v2.

    Args:
        pdf_paths: Lista de rutas a PDFs
        output_dir: Directorio de salida para JSONs
        source_type: Tipo de origen

    Returns:
        Diccionario con resultados del batch
    """
    service = get_e14_ocr_service()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {
        "total": len(pdf_paths),
        "success": 0,
        "failed": 0,
        "files": []
    }

    for pdf_path in pdf_paths:
        try:
            logger.info(f"Procesando: {pdf_path}")
            payload = service.process_pdf_v2(
                pdf_path=pdf_path,
                source_type=source_type
            )

            # Guardar payload
            pdf_name = Path(pdf_path).stem
            output_file = output_path / f"{pdf_name}_v2.json"
            save_payload_v2_json(payload, str(output_file))

            results["success"] += 1
            results["files"].append({
                "input": pdf_path,
                "output": str(output_file),
                "mesa_id": payload.document_header_extracted.mesa_id,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Error procesando {pdf_path}: {e}")
            results["failed"] += 1
            results["files"].append({
                "input": pdf_path,
                "output": None,
                "error": str(e),
                "status": "failed"
            })

    return results
