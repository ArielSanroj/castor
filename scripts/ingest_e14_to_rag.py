#!/usr/bin/env python3
"""
Script de ingesta masiva de E-14 al RAG.
Procesa PDFs con OCR y los indexa automáticamente.

Uso:
    python ingest_e14_to_rag.py --dir /path/to/pdfs
    python ingest_e14_to_rag.py --file /path/to/e14.pdf
    python ingest_e14_to_rag.py --test  # Procesa los PDFs de training_data
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

# Configuración de servicios
E14_SERVICE_URL = os.getenv("E14_SERVICE_URL", "http://localhost:5002")
DASHBOARD_SERVICE_URL = os.getenv("DASHBOARD_SERVICE_URL", "http://localhost:5003")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://localhost:5001")

# Credenciales para autenticación (si es necesario)
AUTH_EMAIL = os.getenv("AUTH_EMAIL", "admin@castor.com")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin123")


def get_auth_token() -> Optional[str]:
    """Obtiene token JWT del servicio core."""
    try:
        response = requests.post(
            f"{CORE_SERVICE_URL}/api/auth/login",
            json={"email": AUTH_EMAIL, "password": AUTH_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
    except Exception as e:
        print(f"⚠️  No se pudo obtener token de autenticación: {e}")
    return None


def process_e14_with_ocr(pdf_path: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Procesa un PDF E-14 con el servicio OCR.

    Args:
        pdf_path: Ruta al archivo PDF
        token: Token JWT opcional

    Returns:
        Resultado del OCR o error
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}

            response = requests.post(
                f"{E14_SERVICE_URL}/api/e14/process",
                files=files,
                headers=headers,
                timeout=120  # OCR puede tardar
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Intentar sin autenticación si falla
                response = requests.post(
                    f"{E14_SERVICE_URL}/api/e14/process",
                    files={"file": (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf")},
                    timeout=120
                )
                return response.json() if response.status_code == 200 else {"error": response.text}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}

    except requests.exceptions.Timeout:
        return {"error": "Timeout procesando PDF"}
    except Exception as e:
        return {"error": str(e)}


def index_e14_to_rag(extraction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Indexa un E-14 procesado en el RAG.

    Args:
        extraction_data: Datos del E-14 extraídos por OCR

    Returns:
        Resultado de la indexación
    """
    try:
        # Extraer la extracción del response
        extraction = extraction_data.get("extraction", extraction_data)
        extraction_id = extraction.get("extraction_id", f"e14-{int(time.time())}")

        # Convertir a formato esperado por el RAG
        payload = {
            "extraction_id": extraction_id,
            "extraction_data": extraction if isinstance(extraction, dict) else extraction_data,
            "metadata": {
                "source": "batch_ingest",
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


def process_and_index_pdf(pdf_path: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Procesa un PDF con OCR e indexa en RAG.

    Args:
        pdf_path: Ruta al PDF
        token: Token JWT opcional

    Returns:
        Resultado completo
    """
    result = {
        "file": pdf_path,
        "ocr_success": False,
        "rag_success": False,
        "mesa_id": None,
        "documents_indexed": 0,
        "errors": []
    }

    print(f"\n📄 Procesando: {os.path.basename(pdf_path)}")

    # 1. OCR
    print("   🔍 Ejecutando OCR...")
    ocr_result = process_e14_with_ocr(pdf_path, token)

    if "error" in ocr_result:
        result["errors"].append(f"OCR: {ocr_result['error']}")
        print(f"   ❌ Error OCR: {ocr_result['error']}")
        return result

    if not ocr_result.get("success", False):
        result["errors"].append(f"OCR fallido: {ocr_result.get('error_message', 'Unknown')}")
        print(f"   ❌ OCR fallido")
        return result

    result["ocr_success"] = True
    result["mesa_id"] = ocr_result.get("mesa_id")
    print(f"   ✅ OCR exitoso - Mesa: {result['mesa_id']}")

    # 2. Indexar en RAG
    print("   📚 Indexando en RAG...")
    rag_result = index_e14_to_rag(ocr_result)

    if "error" in rag_result:
        result["errors"].append(f"RAG: {rag_result['error']}")
        print(f"   ❌ Error RAG: {rag_result['error']}")
        return result

    if rag_result.get("success", False):
        result["rag_success"] = True
        result["documents_indexed"] = rag_result.get("documents_indexed", 0)
        print(f"   ✅ Indexado: {result['documents_indexed']} documentos")
    else:
        result["errors"].append("RAG indexación fallida")
        print(f"   ❌ Indexación fallida")

    return result


def find_pdf_files(directory: str) -> List[str]:
    """Encuentra todos los PDFs en un directorio."""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    return sorted(pdf_files)


def print_summary(results: List[Dict[str, Any]]):
    """Imprime resumen de la ingesta."""
    total = len(results)
    ocr_success = sum(1 for r in results if r["ocr_success"])
    rag_success = sum(1 for r in results if r["rag_success"])
    total_docs = sum(r["documents_indexed"] for r in results)

    print("\n" + "=" * 60)
    print("📊 RESUMEN DE INGESTA")
    print("=" * 60)
    print(f"   Total PDFs procesados: {total}")
    print(f"   OCR exitosos: {ocr_success}/{total}")
    print(f"   RAG indexados: {rag_success}/{total}")
    print(f"   Documentos totales indexados: {total_docs}")

    if any(r["errors"] for r in results):
        print("\n⚠️  Errores encontrados:")
        for r in results:
            if r["errors"]:
                print(f"   - {os.path.basename(r['file'])}: {', '.join(r['errors'])}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Ingesta masiva de E-14 al RAG")
    parser.add_argument("--dir", "-d", help="Directorio con PDFs de E-14")
    parser.add_argument("--file", "-f", help="Archivo PDF individual")
    parser.add_argument("--test", action="store_true", help="Procesar PDFs de training_data")
    parser.add_argument("--limit", "-l", type=int, default=0, help="Límite de PDFs a procesar")
    parser.add_argument("--no-auth", action="store_true", help="No usar autenticación")

    args = parser.parse_args()

    # Determinar archivos a procesar
    pdf_files = []

    if args.test:
        # Usar PDFs de training_data
        training_dir = "/Users/arielsanroj/castor/backend/training_data/e14_source"
        if os.path.exists(training_dir):
            pdf_files = find_pdf_files(training_dir)
        else:
            print(f"❌ Directorio no encontrado: {training_dir}")
            sys.exit(1)
    elif args.dir:
        pdf_files = find_pdf_files(args.dir)
    elif args.file:
        if os.path.exists(args.file):
            pdf_files = [args.file]
        else:
            print(f"❌ Archivo no encontrado: {args.file}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    if not pdf_files:
        print("❌ No se encontraron archivos PDF")
        sys.exit(1)

    # Aplicar límite
    if args.limit > 0:
        pdf_files = pdf_files[:args.limit]

    print(f"\n🚀 INGESTA DE E-14 AL RAG")
    print(f"   PDFs encontrados: {len(pdf_files)}")

    # Obtener token de autenticación
    token = None
    if not args.no_auth:
        print("   🔐 Obteniendo token de autenticación...")
        token = get_auth_token()
        if token:
            print("   ✅ Token obtenido")
        else:
            print("   ⚠️  Sin autenticación (continuando sin token)")

    # Procesar cada PDF
    results = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}]", end="")
        result = process_and_index_pdf(pdf_path, token)
        results.append(result)

        # Pequeña pausa para no sobrecargar el servicio
        if i < len(pdf_files):
            time.sleep(1)

    # Mostrar resumen
    print_summary(results)

    # Verificar estado del RAG
    print("\n📈 Estado actual del RAG:")
    try:
        response = requests.get(f"{DASHBOARD_SERVICE_URL}/api/chat/rag/e14/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total documentos E-14: {stats.get('total_e14_documents', 0)}")
            print(f"   Por departamento: {json.dumps(stats.get('by_departamento', {}), indent=6)}")
    except Exception as e:
        print(f"   ⚠️  No se pudo obtener estadísticas: {e}")


if __name__ == "__main__":
    main()
