#!/usr/bin/env python3
"""
Test script para E-14 OCR con el PDF de prueba.
"""
import os
import sys
import json
from pathlib import Path

# Set env vars before imports
# API key must be set via environment variable ANTHROPIC_API_KEY

from services.e14_ocr_service import E14OCRService
from app.schemas.e14 import PoliticalGroupTally, SpecialsTally

def main():
    pdf_path = Path('/Users/arielsanroj/Downloads/pruebaclaude.pdf')

    if not pdf_path.exists():
        print(f"❌ No se encontró el archivo: {pdf_path}")
        return

    print("=" * 60)
    print("🗳️  PROCESAMIENTO E-14 OCR")
    print("=" * 60)
    print(f"📄 Archivo: {pdf_path.name}")
    print()

    # Crear servicio OCR
    ocr_service = E14OCRService()

    # Procesar E-14
    print("⏳ Procesando con Claude Vision API...")
    result = ocr_service.process_pdf_v2(str(pdf_path))

    if not result:
        print("❌ No se obtuvo resultado del procesamiento")
        return

    # Mostrar resultados
    print()
    print("=" * 60)
    print("✅ EXTRACCIÓN COMPLETADA")
    print("=" * 60)

    # Header
    header = result.document_header_extracted
    print(f"\n📋 HEADER:")
    print(f"   Corporación: {header.corporacion.value}")
    print(f"   Departamento: {header.dept_code} - {header.dept_name}")
    print(f"   Municipio: {header.muni_code} - {header.muni_name}")
    print(f"   Mesa ID: {header.mesa_id}")
    print(f"   Fecha Elección: {header.reported_election_date}")

    # Documento
    doc = result.input_document
    print(f"\n📄 DOCUMENTO: {doc.total_pages} páginas, {doc.copy_type.value}")

    # Campos OCR
    print(f"\n🔍 CAMPOS OCR: {len(result.ocr_fields)} total")
    needs_review = [f for f in result.ocr_fields if f.needs_review]
    print(f"   Necesitan revisión: {len(needs_review)}")

    # Mostrar algunos campos de ejemplo
    print("\n   Ejemplos de campos extraídos:")
    for field in result.ocr_fields[:10]:
        val = field.value_int if field.value_int is not None else field.raw_text
        review_mark = " ⚠️" if field.needs_review else ""
        print(f"   - {field.field_key}: {val} (conf: {field.confidence:.2f}){review_mark}")

    if len(result.ocr_fields) > 10:
        print(f"   ... y {len(result.ocr_fields) - 10} campos más")

    # Tallies normalizados
    print(f"\n📊 CONTEOS NORMALIZADOS: {len(result.normalized_tallies)} grupos")

    for tally in result.normalized_tallies:
        if isinstance(tally, dict):
            # Handle dict case
            if 'political_group_code' in tally:
                print(f"   Grupo {tally['political_group_code']}: {tally.get('party_total', 'N/A')} votos")
            elif 'specials' in tally:
                print(f"   Especiales: {len(tally['specials'])} entradas")
        elif isinstance(tally, PoliticalGroupTally):
            print(f"   Grupo {tally.political_group_code}: {tally.party_total} votos")
            for entry in tally.tallies[:3]:  # First 3 entries
                print(f"      - {entry.subject_type.value}: {entry.votes}")
            if len(tally.tallies) > 3:
                print(f"      ... y {len(tally.tallies) - 3} más")
        elif isinstance(tally, SpecialsTally):
            print(f"   Votos especiales:")
            for entry in tally.specials:
                print(f"      - {entry.subject_type.value}: {entry.votes}")
        elif hasattr(tally, 'political_group_code'):
            print(f"   Grupo {tally.political_group_code}: {tally.party_total} votos")
        elif hasattr(tally, 'specials'):
            print(f"   Especiales: {len(tally.specials)} entradas")

    # Validaciones
    print(f"\n✓ VALIDACIONES: {len(result.validations)} reglas")
    passed = sum(1 for v in result.validations if v.passed)
    failed = len(result.validations) - passed
    print(f"   Pasaron: {passed}, Fallaron: {failed}")

    for v in result.validations:
        icon = "✅" if v.passed else "❌"
        print(f"   {icon} {v.rule_key}: {v.severity.value}")

    # Guardar resultado completo en JSON
    output_path = Path('/Users/arielsanroj/Downloads/pruebaclaude_extraction_result.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 Resultado guardado en: {output_path}")
    print()
    print("=" * 60)
    print("🎉 PROCESAMIENTO EXITOSO")
    print("=" * 60)

if __name__ == "__main__":
    main()
