#!/usr/bin/env python3
"""
Script de ingesta directa de E-14 al RAG.
Usa Claude Vision API directamente para OCR y luego indexa en el RAG.

Uso:
    python ingest_e14_direct.py --test --limit 2
    python ingest_e14_direct.py --file /path/to/e14.pdf
"""
import argparse
import base64
import json
import os
import sys
import time
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

try:
    import anthropic
except ImportError:
    print("❌ Instala anthropic: pip install anthropic")
    sys.exit(1)

# Configuración
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DASHBOARD_SERVICE_URL = os.getenv("DASHBOARD_SERVICE_URL", "http://localhost:5003")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Prompt para OCR de E-14 - Soporta SENADO/CAMARA con voto preferente
E14_OCR_PROMPT = """Analiza estas imágenes de un formulario E-14 (Acta de Escrutinio Electoral de Colombia) y extrae TODOS los datos en formato JSON.

TIPOS DE E-14:
1. SENADO/CÁMARA (Congreso 2022): Múltiples páginas, voto preferente por candidato
2. GOBERNACIÓN/ALCALDÍA (Territoriales): Candidatos únicos por partido
3. PRESIDENCIA: Candidatos únicos

ESTRUCTURA DEL E-14 SENADO/CÁMARA:
- Página 1: Encabezado + Nivelación + Primer partido (Circunscripción Nacional)
- Páginas 2-9: Partidos con LISTA CON/SIN VOTO PREFERENTE
  - SIN VOTO PREFERENTE: Solo votos por agrupación política (→)
  - CON VOTO PREFERENTE: Votos agrupación (←) + votos por candidato (números 1-100)
- Página 10: Votos especiales + Circunscripción Especial Comunidades Indígenas
- Página 11: Más partidos indígenas + Constancias + Firmas jurados

CÓMO LEER LOS VOTOS:
- Casilla de 3 dígitos con números escritos A MANO
- Casilla vacía, con "-" o con "—" = 0
- TOTAL = VOTOS AGRUPACIÓN + VOTOS CANDIDATOS (suma de candidatos marcados)
- Los candidatos se numeran del 1 al 100, solo extraer los que tienen votos

CIRCUNSCRIPCIONES:
- NACIONAL: Partidos tradicionales (códigos 0001-1200)
- ESPECIAL COMUNIDADES INDÍGENAS: Partidos indígenas (códigos 0151-0200)

Responde SOLO con JSON válido:
{
  "header": {
    "corporacion": "SENADO|CAMARA|PRESIDENCIA|GOBERNACION|ALCALDIA|ASAMBLEA|CONCEJO",
    "eleccion": "ELECCIONES CONGRESO 13 DE MARZO DE 2022",
    "departamento_code": "XX",
    "departamento_name": "NOMBRE",
    "municipio_code": "XXX",
    "municipio_name": "NOMBRE",
    "zona": "XX",
    "puesto": "XX",
    "mesa": "XXX",
    "lugar": "nombre del puesto de votación",
    "barcode": "codigo de barras si visible"
  },
  "nivelacion": {
    "total_sufragantes_e11": numero,
    "total_votos_urna": numero,
    "total_votos_incinerados": numero_o_null
  },
  "circunscripcion_nacional": {
    "partidos": [
      {
        "party_code": "XXXX",
        "party_name": "NOMBRE PARTIDO",
        "tipo_lista": "CON_VOTO_PREFERENTE|SIN_VOTO_PREFERENTE",
        "votos_agrupacion": numero,
        "votos_candidatos": [
          {"numero": 1, "votos": numero},
          {"numero": 10, "votos": numero}
        ],
        "total_votos": numero
      }
    ]
  },
  "circunscripcion_indigena": {
    "partidos": [
      {
        "party_code": "XXXX",
        "party_name": "NOMBRE PARTIDO INDIGENA",
        "tipo_lista": "CON_VOTO_PREFERENTE|SIN_VOTO_PREFERENTE",
        "votos_agrupacion": numero,
        "votos_candidatos": [],
        "total_votos": numero
      }
    ]
  },
  "votos_especiales": {
    "votos_blanco": numero,
    "votos_nulos": numero,
    "votos_no_marcados": numero
  },
  "constancias": {
    "hubo_recuento": true|false,
    "num_jurados_firmantes": numero
  }
}

IMPORTANTE:
- Extrae TODOS los partidos de TODAS las páginas
- Solo incluye candidatos que tienen votos > 0
- Para partidos SIN VOTO PREFERENTE, votos_candidatos = []
- El total debe coincidir: total_votos = votos_agrupacion + sum(votos_candidatos)"""


def load_env():
    """Carga variables de entorno desde .env si existe."""
    env_file = Path("/Users/arielsanroj/castor/.env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value


def pdf_to_base64_images(pdf_path: str) -> List[str]:
    """
    Convierte un PDF a imágenes base64.
    Requiere pdf2image y poppler instalados.
    """
    try:
        from pdf2image import convert_from_path
        import io

        images = convert_from_path(pdf_path, dpi=150)
        base64_images = []

        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_images.append(b64)

        return base64_images

    except ImportError:
        print("⚠️  pdf2image no instalado. Intentando con PyMuPDF...")
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            base64_images = []

            for page in doc:
                pix = page.get_pixmap(dpi=150)
                b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                base64_images.append(b64)

            return base64_images

        except ImportError:
            print("❌ Instala pdf2image o PyMuPDF: pip install pdf2image pymupdf")
            return []


def process_e14_with_claude(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    Procesa un E-14 usando Claude Vision API directamente.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Convertir PDF a imágenes
    print("   📸 Convirtiendo PDF a imágenes...")
    images = pdf_to_base64_images(pdf_path)

    if not images:
        return {"error": "No se pudo convertir el PDF a imágenes"}

    print(f"   📄 {len(images)} página(s) detectada(s)")

    # Procesar todas las páginas (Senado puede tener hasta 11)
    print("   🔍 Procesando con Claude Vision...")

    # Construir mensaje con imágenes - máximo 20 páginas para E-14 complejos
    content = []
    max_pages = min(len(images), 20)
    for i, img_b64 in enumerate(images[:max_pages]):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64
            }
        })

    content.append({
        "type": "text",
        "text": E14_OCR_PROMPT
    })

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8192,  # Más tokens para E-14 con muchos partidos
            messages=[{"role": "user", "content": content}]
        )

        # Extraer JSON de la respuesta
        response_text = response.content[0].text

        # Buscar JSON en la respuesta
        try:
            # Intentar parsear directamente
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Buscar JSON entre ```json y ```
            import re
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Buscar cualquier JSON válido
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    return {"error": f"No se encontró JSON válido en respuesta: {response_text[:200]}"}

        # Agregar metadata
        data["extraction_id"] = f"e14-{uuid.uuid4().hex[:8]}"
        data["source_file"] = os.path.basename(pdf_path)
        data["overall_confidence"] = 0.85  # Estimado
        data["fields_needing_review"] = 0
        data["total_pages"] = len(images)

        # Generar mesa_id si no existe
        header = data.get("header", {})
        if header and "mesa_id" not in header:
            header["mesa_id"] = f"{header.get('departamento_code', '00')}-{header.get('municipio_code', '000')}-{header.get('zona', '00')}-{header.get('puesto', '000')}-{header.get('mesa', '000')}"

        return data

    except anthropic.APIError as e:
        return {"error": f"Error de API Claude: {e}"}
    except Exception as e:
        return {"error": f"Error procesando: {e}"}


def index_to_rag(extraction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Indexa los datos extraídos en el RAG."""
    try:
        payload = {
            "extraction_id": extraction_data.get("extraction_id", str(uuid.uuid4())),
            "extraction_data": extraction_data,
            "metadata": {
                "source": "direct_ocr",
                "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }

        response = requests.post(
            f"{DASHBOARD_SERVICE_URL}/api/chat/rag/e14/index",
            json=payload,
            timeout=30
        )

        if response.status_code in (200, 201):
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}

    except Exception as e:
        return {"error": str(e)}


def process_and_index(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """Procesa un PDF y lo indexa en el RAG."""
    result = {
        "file": pdf_path,
        "ocr_success": False,
        "rag_success": False,
        "mesa_id": None,
        "documents_indexed": 0,
        "errors": []
    }

    print(f"\n📄 Procesando: {os.path.basename(pdf_path)}")

    # 1. OCR con Claude
    ocr_result = process_e14_with_claude(pdf_path, api_key)

    if "error" in ocr_result:
        result["errors"].append(f"OCR: {ocr_result['error']}")
        print(f"   ❌ Error: {ocr_result['error']}")
        return result

    result["ocr_success"] = True
    result["mesa_id"] = ocr_result.get("header", {}).get("mesa_id")
    print(f"   ✅ OCR exitoso - Mesa: {result['mesa_id']}")

    # Mostrar resumen
    header = ocr_result.get("header", {})
    partidos = ocr_result.get("partidos", [])
    print(f"   📍 {header.get('municipio_name', '?')}, {header.get('departamento_name', '?')}")
    print(f"   🗳️  {len(partidos)} partidos/candidatos detectados")

    # 2. Indexar en RAG
    print("   📚 Indexando en RAG...")
    rag_result = index_to_rag(ocr_result)

    if "error" in rag_result:
        result["errors"].append(f"RAG: {rag_result['error']}")
        print(f"   ❌ Error RAG: {rag_result['error']}")
        return result

    if rag_result.get("success"):
        result["rag_success"] = True
        result["documents_indexed"] = rag_result.get("documents_indexed", 0)
        print(f"   ✅ Indexado: {result['documents_indexed']} documentos")

    return result


def find_pdfs(directory: str) -> List[str]:
    """Encuentra PDFs en un directorio."""
    pdfs = []
    for f in os.listdir(directory):
        if f.lower().endswith(".pdf"):
            pdfs.append(os.path.join(directory, f))
    return sorted(pdfs)


def main():
    parser = argparse.ArgumentParser(description="Ingesta directa de E-14 con Claude OCR")
    parser.add_argument("--test", action="store_true", help="Usar PDFs de training_data")
    parser.add_argument("--file", "-f", help="Archivo PDF individual")
    parser.add_argument("--dir", "-d", help="Directorio con PDFs")
    parser.add_argument("--limit", "-l", type=int, default=0, help="Límite de PDFs")

    args = parser.parse_args()

    # Cargar .env
    load_env()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY no configurada")
        sys.exit(1)

    # Determinar archivos
    pdf_files = []
    if args.test:
        training_dir = "/Users/arielsanroj/castor/backend/training_data/e14_source"
        if os.path.exists(training_dir):
            pdf_files = find_pdfs(training_dir)
    elif args.dir:
        pdf_files = find_pdfs(args.dir)
    elif args.file:
        if os.path.exists(args.file):
            pdf_files = [args.file]

    if not pdf_files:
        print("❌ No se encontraron PDFs")
        parser.print_help()
        sys.exit(1)

    if args.limit > 0:
        pdf_files = pdf_files[:args.limit]

    print(f"\n🚀 INGESTA DIRECTA DE E-14")
    print(f"   PDFs a procesar: {len(pdf_files)}")
    print(f"   Modelo: {CLAUDE_MODEL}")

    # Procesar
    results = []
    for i, pdf in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}]", end="")
        result = process_and_index(pdf, api_key)
        results.append(result)
        if i < len(pdf_files):
            time.sleep(2)  # Rate limiting

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    ocr_ok = sum(1 for r in results if r["ocr_success"])
    rag_ok = sum(1 for r in results if r["rag_success"])
    total_docs = sum(r["documents_indexed"] for r in results)
    print(f"   OCR exitosos: {ocr_ok}/{len(results)}")
    print(f"   RAG indexados: {rag_ok}/{len(results)}")
    print(f"   Documentos totales: {total_docs}")

    # Stats del RAG
    print("\n📈 Estado del RAG:")
    try:
        resp = requests.get(f"{DASHBOARD_SERVICE_URL}/api/chat/rag/e14/stats", timeout=10)
        if resp.ok:
            stats = resp.json()
            print(f"   Total docs E-14: {stats.get('total_e14_documents', 0)}")
            print(f"   Por departamento: {stats.get('by_departamento', {})}")
    except:
        pass


if __name__ == "__main__":
    main()
