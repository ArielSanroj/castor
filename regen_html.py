#!/usr/bin/env python3
"""Regenera el HTML desde el JSON guardado."""
import json
from pathlib import Path
from datetime import datetime

def get_confidence_class(conf):
    if conf >= 0.8:
        return "high"
    elif conf >= 0.6:
        return "medium"
    return "low"

def generate_result_card(r):
    if r["status"] == "error":
        return f"""
            <div class="result-card error">
                <div class="result-header">
                    <span class="result-filename">{r['filename']}</span>
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
                        </table>
                    </div>
                </div>
"""

    if partidos:
        html += f"""
                <div class="data-section" style="margin-top: 20px;">
                    <h4>🏛 Partidos y Candidatos ({len(partidos)} partidos)</h4>
                    <table>
                        <thead><tr><th>Código</th><th>Partido/Lista</th><th>Votos</th><th>Confianza</th><th>Candidatos</th></tr></thead>
                        <tbody>
"""
        for i, partido in enumerate(partidos[:20]):
            candidatos = partido.get('candidatos', [])
            conf = partido.get('confidence', 0) or 0
            conf_class = get_confidence_class(conf)
            cand_id = f"cand_{card_id}_{i}"
            btn = f'<button class="expand-btn" onclick="toggleCandidatos(\'{cand_id}\')">Ver {len(candidatos)}</button>' if candidatos else '-'
            nombre_partido = partido.get('nombre') or 'N/A'
            html += f"""
                            <tr class="partido-row">
                                <td>{partido.get('codigo', 'N/A')}</td>
                                <td class="partido-name">{nombre_partido[:50]}</td>
                                <td class="votos">{partido.get('votos', 0)}</td>
                                <td><span class="confidence {conf_class}">{conf:.0%}</span></td>
                                <td>{btn}</td>
                            </tr>
"""
            if candidatos:
                html += f'<tr><td colspan="5"><div id="{cand_id}" class="candidatos-list hidden">'
                for cand in candidatos[:15]:
                    cand_nombre = cand.get('nombre') or 'N/A'
                    cand_nombre = str(cand_nombre)[:40]
                    html += f'<div class="candidato"><span>#{cand.get("numero", "?")} {cand_nombre}</span><span class="votos">{cand.get("votos", 0)}</span></div>'
                if len(candidatos) > 15:
                    html += f"<div class='candidato'>... y {len(candidatos) - 15} más</div>"
                html += '</div></td></tr>'
        html += "</tbody></table></div>"
    html += "</div>"
    return html


def generate_html(results, output_path):
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
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; padding: 40px 20px; background: rgba(255,255,255,0.05); border-radius: 20px; margin-bottom: 30px; }}
        h1 {{ font-size: 2.5em; background: linear-gradient(90deg, #00d4ff, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }}
        .subtitle {{ color: #888; font-size: 1.1em; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: rgba(255,255,255,0.08); border-radius: 15px; padding: 25px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #00d4ff; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .section {{ background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px; margin-bottom: 30px; }}
        .section-title {{ font-size: 1.5em; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid rgba(255,255,255,0.1); display: flex; align-items: center; gap: 10px; }}
        .badge {{ background: #7c3aed; padding: 5px 15px; border-radius: 20px; font-size: 0.7em; }}
        .badge.camara {{ background: #0891b2; }}
        .badge.senado {{ background: #7c3aed; }}
        .result-card {{ background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #00d4ff; }}
        .result-card.error {{ border-left-color: #ef4444; }}
        .result-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }}
        .result-filename {{ font-weight: bold; font-size: 1.2em; }}
        .result-meta {{ display: flex; gap: 15px; color: #888; font-size: 0.9em; flex-wrap: wrap; }}
        .data-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
        .data-section {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; }}
        .data-section h4 {{ color: #00d4ff; margin-bottom: 10px; font-size: 0.9em; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: #888; font-weight: normal; }}
        .partido-row {{ background: rgba(255,255,255,0.03); }}
        .partido-name {{ font-weight: bold; }}
        .votos {{ font-weight: bold; color: #10b981; font-size: 1.1em; }}
        .confidence {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }}
        .confidence.high {{ background: #10b981; color: #fff; }}
        .confidence.medium {{ background: #f59e0b; color: #000; }}
        .confidence.low {{ background: #ef4444; color: #fff; }}
        .candidatos-list {{ margin-left: 20px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-top: 10px; }}
        .candidato {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        .candidato:last-child {{ border-bottom: none; }}
        .error-msg {{ background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 10px; padding: 15px; color: #fca5a5; }}
        .timestamp {{ text-align: center; color: #666; margin-top: 30px; font-size: 0.9em; }}
        .expand-btn {{ background: rgba(255,255,255,0.1); border: none; color: #fff; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 0.8em; }}
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
            <div class="stat-card"><div class="stat-value">{len(results)}</div><div class="stat-label">PDFs Procesados</div></div>
            <div class="stat-card"><div class="stat-value">{successful}</div><div class="stat-label">Exitosos</div></div>
            <div class="stat-card"><div class="stat-value">{total_tokens:,}</div><div class="stat-label">Tokens Totales</div></div>
            <div class="stat-card"><div class="stat-value">${total_cost:.2f}</div><div class="stat-label">Costo Total USD</div></div>
        </div>
"""

    if camara_results:
        html += '<div class="section"><h2 class="section-title"><span class="badge camara">CÁMARA</span>Formularios E-14 Cámara de Representantes</h2>'
        for r in camara_results:
            html += generate_result_card(r)
        html += "</div>"

    if senado_results:
        html += '<div class="section"><h2 class="section-title"><span class="badge senado">SENADO</span>Formularios E-14 Senado de la República</h2>'
        for r in senado_results:
            html += generate_result_card(r)
        html += "</div>"

    html += f"""
        <p class="timestamp">Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | CASTOR ELECCIONES</p>
    </div>
    <script>function toggleCandidatos(id) {{ document.getElementById(id).classList.toggle('hidden'); }}</script>
</body>
</html>
"""
    Path(output_path).write_text(html, encoding='utf-8')
    print(f"HTML generado: {output_path}")


if __name__ == "__main__":
    with open('test_ocr_congreso_2022.json', 'r') as f:
        results = json.load(f)
    generate_html(results, 'test_ocr_congreso_2022.html')
