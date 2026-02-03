#!/usr/bin/env python3
"""
Script de prueba para el servicio E-14 OCR.
Uso: python scripts/test_e14_ocr.py <ruta_pdf_o_url>
"""
import sys
import json
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_e14_ocr(source: str):
    """Prueba el servicio E-14 OCR con un PDF."""
    from services.e14_ocr_service import get_e14_ocr_service

    print(f"\n{'='*60}")
    print("CASTOR ELECCIONES - E-14 OCR Test")
    print(f"{'='*60}\n")

    # Inicializar servicio
    print("Inicializando servicio OCR...")
    try:
        ocr_service = get_e14_ocr_service()
        print(f"✓ Servicio inicializado con modelo: {ocr_service.model}")
    except Exception as e:
        print(f"✗ Error inicializando servicio: {e}")
        return

    # Procesar E-14
    print(f"\nProcesando: {source}")
    print("-" * 40)

    try:
        if source.startswith('http'):
            extraction = ocr_service.process_pdf(pdf_url=source)
        else:
            extraction = ocr_service.process_pdf(pdf_path=source)

        print(f"✓ Extracción completada en {extraction.processing_time_ms}ms")

        # Mostrar header
        print(f"\n📋 HEADER")
        print(f"   Mesa ID: {extraction.header.mesa_id}")
        print(f"   Corporación: {extraction.header.corporacion.value}")
        print(f"   Departamento: {extraction.header.departamento_code} - {extraction.header.departamento_name}")
        print(f"   Municipio: {extraction.header.municipio_code} - {extraction.header.municipio_name}")
        print(f"   Zona/Puesto/Mesa: {extraction.header.zona}/{extraction.header.puesto}/{extraction.header.mesa}")
        print(f"   Tipo copia: {extraction.header.copy_type.value}")

        # Mostrar nivelación
        print(f"\n📊 NIVELACIÓN")
        print(f"   Sufragantes E-11: {extraction.nivelacion.total_sufragantes_e11}")
        print(f"   Votos en urna: {extraction.nivelacion.total_votos_urna}")
        print(f"   Votos incinerados: {extraction.nivelacion.total_votos_incinerados or 0}")

        # Mostrar partidos
        print(f"\n🗳️ PARTIDOS ({len(extraction.partidos)} encontrados)")
        for p in extraction.partidos[:10]:  # Mostrar primeros 10
            print(f"   [{p.party_code}] {p.party_name[:40]}: {p.total_votos} votos")
        if len(extraction.partidos) > 10:
            print(f"   ... y {len(extraction.partidos) - 10} más")

        # Mostrar votos especiales
        print(f"\n📝 VOTOS ESPECIALES")
        print(f"   En blanco: {extraction.votos_especiales.votos_blanco}")
        print(f"   Nulos: {extraction.votos_especiales.votos_nulos}")
        print(f"   No marcados: {extraction.votos_especiales.votos_no_marcados}")

        # Mostrar totales
        print(f"\n📈 TOTALES")
        print(f"   Total partidos: {extraction.total_votos_partidos}")
        print(f"   Total computado: {extraction.total_computado}")
        print(f"   Delta (urna - computado): {extraction.nivelacion.total_votos_urna - extraction.total_computado}")

        # Validar
        print(f"\n🔍 VALIDACIÓN")
        validation = ocr_service.validate_extraction(extraction)
        print(f"   Todas pasaron: {'✓' if validation.all_passed else '✗'}")
        print(f"   Críticas: {validation.critical_failures}")
        print(f"   Altas: {validation.high_failures}")
        print(f"   Medias: {validation.medium_failures}")

        if validation.alerts_generated:
            print(f"\n⚠️ ALERTAS:")
            for alert in validation.alerts_generated:
                print(f"   - {alert}")

        # Metadata
        print(f"\n📊 METADATA")
        print(f"   Confianza global: {extraction.overall_confidence:.2%}")
        print(f"   Campos para revisión: {extraction.fields_needing_review}")
        print(f"   Páginas procesadas: {extraction.pages_processed}/{extraction.total_pages}")

        # Guardar resultado
        output_file = f"e14_extraction_{extraction.extraction_id[:8]}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extraction.dict(), f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Resultado guardado en: {output_file}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_e14_ocr.py <ruta_pdf_o_url>")
        print("\nEjemplos:")
        print("  python scripts/test_e14_ocr.py /path/to/e14.pdf")
        print("  python scripts/test_e14_ocr.py https://example.com/e14.pdf")
        sys.exit(1)

    test_e14_ocr(sys.argv[1])


if __name__ == "__main__":
    main()
