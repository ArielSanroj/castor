#!/usr/bin/env python3
"""
Test OCR Congreso 2022 - Procesa PDFs de Cámara y Senado
Genera un HTML con los resultados del procesamiento OCR.
"""
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Configuración
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
DOWNLOADS_DIR = Path.home() / "Downloads"
OUTPUT_DIR = Path(__file__).parent


SYSTEM_PROMPT = """Eres un sistema experto de OCR especializado en formularios electorales colombianos E-14 (Acta de Escrutinio de Jurados de Votación).

Tu tarea es extraer TODOS los datos del formulario E-14 con MÁXIMA PRECISIÓN.

=== ESTRUCTURA VISUAL CRÍTICA ===

El formulario E-14 tiene una TABLA donde cada FILA es un candidato/partido.
La columna de VOTACIÓN está a la DERECHA de cada fila.
Cada celda de votación tiene 3 casillas para dígitos: [Centenas][Decenas][Unidades]

EJEMPLO DE LECTURA:
- Si ves escrito "0 4 8" en las 3 casillas → el número es 48
- Si ves escrito "1 3 6" en las 3 casillas → el número es 136
- Si ves "- - -" o casillas vacías → el número es 0

=== REGLAS CRÍTICAS ===

1. NO CONFUNDAS dígitos similares:
   - "4" vs "9" - El 4 tiene línea horizontal, el 9 tiene círculo arriba
   - "1" vs "7" - El 1 es vertical simple, el 7 tiene línea horizontal arriba

2. Lee de IZQUIERDA a DERECHA las 3 casillas: [C][D][U]

3. Si un dígito es ambiguo, indica confidence bajo (< 0.7) y needs_review=true

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional."""


def build_extraction_prompt(pages_count: int, corporacion: str) -> str:
    """Construye el prompt de extracción."""
    return f"""Analiza este formulario E-14 de {corporacion} ({pages_count} página(s)) y extrae TODOS los datos en el siguiente formato JSON:

{{
  "header": {{
    "corporacion": "{corporacion}",
    "departamento": "nombre del departamento",
    "municipio": "nombre del municipio",
    "zona": "número",
    "puesto": "nombre del puesto de votación",
    "mesa": "número"
  }},
  "nivelacion": {{
    "total_sufragantes": número o null,
    "total_votos_urna": número o null
  }},
  "partidos": [
    {{
      "codigo": "código del partido",
      "nombre": "nombre del partido/lista",
      "votos": número,
      "candidatos": [
        {{"numero": 1, "nombre": "nombre", "votos": número}}
      ],
      "confidence": 0.0-1.0,
      "needs_review": true/false
    }}
  ],
  "votos_especiales": {{
    "votos_blanco": número,
    "votos_nulos": número,
    "votos_no_marcados": número
  }},
  "metadata": {{
    "total_partidos": número,
    "total_candidatos": número,
    "overall_confidence": 0.0-1.0,
    "fields_needing_review": número
  }}
}}

Extrae TODOS los partidos y candidatos visibles en TODAS las páginas. Sé muy preciso con los números."""


def pdf_to_images(pdf_path: Path) -> List[str]:
    """Convierte PDF a imágenes base64."""
    try:
        from pdf2image import convert_from_path
        from PIL import ImageEnhance, ImageFilter
        import io

        pil_images = convert_from_path(str(pdf_path), dpi=200, fmt='PNG')

        base64_images = []
        for img in pil_images:
            # Preprocesamiento
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Contraste +30%
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)

            # Brillo +10%
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)

            # Nitidez +50%
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)

            # Edge enhance
            img = img.filter(ImageFilter.EDGE_ENHANCE)

            # Base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            base64_images.append(base64_str)

        return base64_images

    except ImportError:
        print("ERROR: Instalar pdf2image: pip install pdf2image")
        print("También necesitas poppler: brew install poppler")
        sys.exit(1)


def call_claude_vision(images: List[str], corporacion: str) -> Dict[str, Any]:
    """Llama a Claude Vision API."""
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

    content.append({
        "type": "text",
        "text": build_extraction_prompt(len(images), corporacion)
    })

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": content}]
    }

    with httpx.Client(timeout=300) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            raise ValueError(f"Error API: {response.status_code} - {response.text[:500]}")

    result = response.json()

    # Extraer métricas
    usage = result.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)

    # Parsear respuesta
    response_text = result['content'][0]['text']

    # Limpiar markdown
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        parsed = {"error": f"JSON parse error: {e}", "raw": response_text[:1000]}

    return {
        "data": parsed,
        "tokens": {"input": input_tokens, "output": output_tokens},
        "cost_usd": (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
    }


def process_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Procesa un PDF completo."""
    filename = pdf_path.name.lower()
    corporacion = "CAMARA" if "camara" in filename else "SENADO"

    print(f"  Procesando: {pdf_path.name} ({corporacion})")

    start_time = time.time()

    try:
        # Convertir a imágenes
        images = pdf_to_images(pdf_path)
        print(f"    -> {len(images)} páginas")

        # OCR con Claude
        result = call_claude_vision(images, corporacion)

        processing_time = time.time() - start_time

        return {
            "filename": pdf_path.name,
            "corporacion": corporacion,
            "pages": len(images),
            "status": "success",
            "processing_time_s": round(processing_time, 2),
            "tokens": result["tokens"],
            "cost_usd": round(result["cost_usd"], 4),
            "data": result["data"]
        }

    except Exception as e:
        return {
            "filename": pdf_path.name,
            "corporacion": corporacion,
            "status": "error",
            "error": str(e),
            "processing_time_s": round(time.time() - start_time, 2)
        }


def generate_html(results: List[Dict[str, Any]], output_path: Path):
    """Genera el HTML con los resultados."""

    total_cost = sum(r.get("cost_usd", 0) for r in results)
    total_tokens = sum(r.get("tokens", {}).get("input", 0) + r.get("tokens", {}).get("output", 0) for r in results)
    successful = sum(1 for r in results if r["status"] == "success")

    camara_results = [r for r in results if r["corporacion"] == "CAMARA"]
    senado_results = [r for r in results if r["corporacion"] == "SENADO"]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test OCR - Congreso 2022</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}

        header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .subtitle {{ color: #888; font-size: 1.1em; }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #00d4ff;
        }}
        .stat-label {{ color: #888; margin-top: 5px; }}

        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge {{
            background: #7c3aed;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.7em;
        }}
        .badge.camara {{ background: #0891b2; }}
        .badge.senado {{ background: #7c3aed; }}

        .result-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #00d4ff;
        }}
        .result-card.error {{ border-left-color: #ef4444; }}

        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .result-filename {{
            font-weight: bold;
            font-size: 1.2em;
        }}
        .result-meta {{
            display: flex;
            gap: 15px;
            color: #888;
            font-size: 0.9em;
        }}
        .result-meta span {{ display: flex; align-items: center; gap: 5px; }}

        .data-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .data-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 15px;
        }}
        .data-section h4 {{
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ color: #888; font-weight: normal; }}

        .partido-row {{
            background: rgba(255,255,255,0.03);
        }}
        .partido-row td {{ padding: 12px; }}
        .partido-name {{ font-weight: bold; }}
        .votos {{
            font-weight: bold;
            color: #10b981;
            font-size: 1.1em;
        }}
        .confidence {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }}
        .confidence.high {{ background: #10b981; color: #fff; }}
        .confidence.medium {{ background: #f59e0b; color: #000; }}
        .confidence.low {{ background: #ef4444; color: #fff; }}

        .candidatos-list {{
            margin-left: 20px;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-top: 10px;
        }}
        .candidato {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .candidato:last-child {{ border-bottom: none; }}

        .error-msg {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            border-radius: 10px;
            padding: 15px;
            color: #fca5a5;
        }}

        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}

        .expand-btn {{
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            padding: 5px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8em;
        }}
        .expand-btn:hover {{ background: rgba(255,255,255,0.2); }}

        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Test OCR - Congreso 2022</h1>
            <p class="subtitle">Procesamiento de Formularios E-14 con Claude Vision</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(results)}</div>
                <div class="stat-label">PDFs Procesados</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{successful}</div>
                <div class="stat-label">Exitosos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_tokens:,}</div>
                <div class="stat-label">Tokens Totales</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${total_cost:.2f}</div>
                <div class="stat-label">Costo Total USD</div>
            </div>
        </div>
"""

    # Sección Cámara
    if camara_results:
        html += """
        <div class="section">
            <h2 class="section-title">
                <span class="badge camara">CÁMARA</span>
                Formularios E-14 Cámara de Representantes
            </h2>
"""
        for r in camara_results:
            html += generate_result_card(r)
        html += "</div>"

    # Sección Senado
    if senado_results:
        html += """
        <div class="section">
            <h2 class="section-title">
                <span class="badge senado">SENADO</span>
                Formularios E-14 Senado de la República
            </h2>
"""
        for r in senado_results:
            html += generate_result_card(r)
        html += "</div>"

    html += f"""
        <p class="timestamp">Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | CASTOR ELECCIONES</p>
    </div>

    <script>
        function toggleCandidatos(id) {{
            const el = document.getElementById(id);
            el.classList.toggle('hidden');
        }}
    </script>
</body>
</html>
"""

    output_path.write_text(html, encoding='utf-8')
    print(f"\nHTML generado: {output_path}")


def generate_result_card(r: Dict[str, Any]) -> str:
    """Genera el HTML de una tarjeta de resultado."""

    if r["status"] == "error":
        return f"""
            <div class="result-card error">
                <div class="result-header">
                    <span class="result-filename">{r['filename']}</span>
                    <div class="result-meta">
                        <span>⏱ {r.get('processing_time_s', 0)}s</span>
                    </div>
                </div>
                <div class="error-msg">Error: {r.get('error', 'Unknown')}</div>
            </div>
"""

    data = r.get("data", {})
    header = data.get("header", {})
    nivelacion = data.get("nivelacion", {})
    partidos = data.get("partidos", [])
    especiales = data.get("votos_especiales", {})
    metadata = data.get("metadata", {})

    card_id = r['filename'].replace('.', '_').replace(' ', '_')

    # Header info
    html = f"""
            <div class="result-card">
                <div class="result-header">
                    <span class="result-filename">{r['filename']}</span>
                    <div class="result-meta">
                        <span>📄 {r.get('pages', 0)} páginas</span>
                        <span>⏱ {r.get('processing_time_s', 0)}s</span>
                        <span>🔢 {r.get('tokens', {}).get('input', 0) + r.get('tokens', {}).get('output', 0):,} tokens</span>
                        <span>💰 ${r.get('cost_usd', 0):.4f}</span>
                    </div>
                </div>

                <div class="data-grid">
                    <div class="data-section">
                        <h4>📍 Ubicación</h4>
                        <table>
                            <tr><th>Departamento</th><td>{header.get('departamento', 'N/A')}</td></tr>
                            <tr><th>Municipio</th><td>{header.get('municipio', 'N/A')}</td></tr>
                            <tr><th>Puesto</th><td>{header.get('puesto', 'N/A')}</td></tr>
                            <tr><th>Mesa</th><td>{header.get('mesa', 'N/A')}</td></tr>
                        </table>
                    </div>

                    <div class="data-section">
                        <h4>📊 Nivelación</h4>
                        <table>
                            <tr><th>Total Sufragantes</th><td class="votos">{nivelacion.get('total_sufragantes', 'N/A')}</td></tr>
                            <tr><th>Total Votos Urna</th><td class="votos">{nivelacion.get('total_votos_urna', 'N/A')}</td></tr>
                        </table>
                    </div>

                    <div class="data-section">
                        <h4>🗳 Votos Especiales</h4>
                        <table>
                            <tr><th>Votos en Blanco</th><td>{especiales.get('votos_blanco', 0)}</td></tr>
                            <tr><th>Votos Nulos</th><td>{especiales.get('votos_nulos', 0)}</td></tr>
                            <tr><th>No Marcados</th><td>{especiales.get('votos_no_marcados', 0)}</td></tr>
                        </table>
                    </div>

                    <div class="data-section">
                        <h4>📈 Metadata OCR</h4>
                        <table>
                            <tr><th>Partidos</th><td>{metadata.get('total_partidos', len(partidos))}</td></tr>
                            <tr><th>Candidatos</th><td>{metadata.get('total_candidatos', 'N/A')}</td></tr>
                            <tr><th>Confianza</th><td><span class="confidence {get_confidence_class(metadata.get('overall_confidence', 0))}">{metadata.get('overall_confidence', 0):.0%}</span></td></tr>
                            <tr><th>Campos a revisar</th><td>{metadata.get('fields_needing_review', 0)}</td></tr>
                        </table>
                    </div>
                </div>
"""

    # Partidos
    if partidos:
        html += f"""
                <div class="data-section" style="margin-top: 20px;">
                    <h4>🏛 Partidos y Candidatos ({len(partidos)} partidos)</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Código</th>
                                <th>Partido/Lista</th>
                                <th>Votos</th>
                                <th>Confianza</th>
                                <th>Candidatos</th>
                            </tr>
                        </thead>
                        <tbody>
"""
        for i, partido in enumerate(partidos[:20]):  # Limitar a 20
            candidatos = partido.get('candidatos', [])
            conf = partido.get('confidence', 0)
            conf_class = get_confidence_class(conf)

            cand_id = f"cand_{card_id}_{i}"
            btn_html = f'<button class="expand-btn" onclick="toggleCandidatos(\'{cand_id}\')">Ver {len(candidatos)} candidatos</button>' if candidatos else '-'
            html += f"""
                            <tr class="partido-row">
                                <td>{partido.get('codigo', 'N/A')}</td>
                                <td class="partido-name">{partido.get('nombre', 'N/A')[:50]}</td>
                                <td class="votos">{partido.get('votos', 0)}</td>
                                <td><span class="confidence {conf_class}">{conf:.0%}</span></td>
                                <td>{btn_html}</td>
                            </tr>
"""
            if candidatos:
                html += f"""
                            <tr>
                                <td colspan="5">
                                    <div id="cand_{card_id}_{i}" class="candidatos-list hidden">
"""
                for cand in candidatos[:15]:  # Limitar
                    cand_nombre = cand.get('nombre') or 'N/A'
                    cand_nombre = cand_nombre[:40] if cand_nombre else 'N/A'
                    html += f"""
                                        <div class="candidato">
                                            <span>#{cand.get('numero', '?')} {cand_nombre}</span>
                                            <span class="votos">{cand.get('votos', 0)}</span>
                                        </div>
"""
                if len(candidatos) > 15:
                    html += f"<div class='candidato'>... y {len(candidatos) - 15} candidatos más</div>"
                html += """
                                    </div>
                                </td>
                            </tr>
"""

        if len(partidos) > 20:
            html += f"<tr><td colspan='5'>... y {len(partidos) - 20} partidos más</td></tr>"

        html += """
                        </tbody>
                    </table>
                </div>
"""

    html += "</div>"
    return html


def get_confidence_class(conf: float) -> str:
    """Retorna la clase CSS según confianza."""
    if conf >= 0.8:
        return "high"
    elif conf >= 0.6:
        return "medium"
    return "low"


def main():
    """Función principal."""
    print("=" * 60)
    print("  TEST OCR CONGRESO 2022 - CASTOR ELECCIONES")
    print("=" * 60)
    print()

    # Buscar PDFs
    pdf_files = []
    for pattern in ["camara*.pdf", "senado*.pdf"]:
        pdf_files.extend(DOWNLOADS_DIR.glob(pattern))

    pdf_files = sorted(set(pdf_files))

    if not pdf_files:
        print("ERROR: No se encontraron PDFs de Cámara o Senado en Downloads")
        sys.exit(1)

    print(f"Encontrados {len(pdf_files)} PDFs:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()

    # Procesar cada PDF
    results = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] ", end="")
        result = process_pdf(pdf_path)
        results.append(result)

        if result["status"] == "success":
            print(f"    ✓ {result['processing_time_s']}s, ${result['cost_usd']:.4f}")
        else:
            print(f"    ✗ Error: {result.get('error', 'Unknown')[:50]}")
        print()

    # Generar HTML
    output_html = OUTPUT_DIR / "test_ocr_congreso_2022.html"
    generate_html(results, output_html)

    # Guardar JSON con resultados completos
    output_json = OUTPUT_DIR / "test_ocr_congreso_2022.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"JSON guardado: {output_json}")

    # Resumen
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    successful = sum(1 for r in results if r["status"] == "success")
    total_cost = sum(r.get("cost_usd", 0) for r in results)
    print(f"  Procesados: {len(results)} PDFs")
    print(f"  Exitosos: {successful}")
    print(f"  Costo total: ${total_cost:.4f} USD")
    print()
    print(f"  Abrir: file://{output_html}")


if __name__ == "__main__":
    main()
