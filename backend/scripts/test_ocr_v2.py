#!/usr/bin/env python3
"""
Test del servicio E14 OCR v2.
Verifica que el procesamiento genere payloads v2 correctamente.

Uso:
    python scripts/test_ocr_v2.py [pdf_path]
"""
import json
import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_field(name: str, value, indent: int = 0):
    spaces = "  " * indent
    print(f"{spaces}{YELLOW}{name}:{RESET} {value}")


def test_v2_payload_structure():
    """Test de estructura del payload v2."""
    print_section("TEST: Estructura del Payload V2")

    from app.schemas.e14 import (
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
        CopyType,
        Corporacion,
    )

    # Crear un payload de ejemplo
    pipeline = PipelineContext(
        target_process=TargetProcess(
            process_type=ProcessType.CONSULTA,
            process_date="2026-03-08",
            contest_type=ContestType.CONSULTA,
            contest_scope=ContestScope.NATIONAL
        ),
        template_family="E14",
        template_version="E14_CONSULTA_SIMPLE_V1",
        ruleset_version="VALIDATION_CORE_V1"
    )

    input_doc = InputDocument(
        source_file="test.pdf",
        form_type="E14",
        copy_type=CopyType.DELEGADOS,
        source_type=SourceType.WITNESS_UPLOAD,
        sha256="abc123",
        total_pages=1,
        pages=[PageInfo(page_no=1)]
    )

    header = DocumentHeaderExtracted(
        reported_election_date="2026-03-08",
        reported_election_label="GRAN CONSULTA NACIONAL MARZO 8 2026",
        corporacion=Corporacion.CONSULTA,
        dept_code="11",
        dept_name="BOGOTA",
        muni_code="001",
        muni_name="BOGOTA",
        zone_code="01",
        station_code="01",
        table_number=1,
        place_name="COLEGIO TEST"
    )

    print(f"  {GREEN}✓{RESET} PipelineContext creado")
    print(f"  {GREEN}✓{RESET} InputDocument creado")
    print(f"  {GREEN}✓{RESET} DocumentHeaderExtracted creado")
    print(f"  Mesa ID: {header.mesa_id}")

    # Test OCRField con raw_mark
    field_with_mark = OCRField(
        field_key="CANDIDATE_01",
        page_no=1,
        value_int=150,
        raw_text="*150",
        raw_mark="*",
        ballot_option_type=BallotOptionType.CANDIDATE,
        political_group_code="0001",
        political_group_name="PARTIDO TEST",
        candidate_ordinal=1,
        candidate_name="CANDIDATO PRUEBA",
        confidence=0.65,
        needs_review=True
    )

    print(f"  {GREEN}✓{RESET} OCRField con raw_mark='*' creado")
    print(f"    - field_key: {field_with_mark.field_key}")
    print(f"    - raw_mark: {field_with_mark.raw_mark}")
    print(f"    - needs_review: {field_with_mark.needs_review}")

    print(f"\n  {GREEN}✓ Estructura V2 válida{RESET}")


def test_v2_enums():
    """Test de los nuevos enums v2."""
    print_section("TEST: Enums V2")

    from app.schemas.e14 import (
        ProcessType,
        ContestType,
        ContestScope,
        BallotOptionType,
        SourceType,
    )

    print("  ProcessType:")
    for pt in ProcessType:
        print(f"    - {pt.value}")

    print("\n  ContestType:")
    for ct in ContestType:
        print(f"    - {ct.value}")

    print("\n  BallotOptionType:")
    for bot in BallotOptionType:
        print(f"    - {bot.value}")

    print(f"\n  {GREEN}✓ Todos los enums v2 disponibles{RESET}")


def test_service_initialization():
    """Test de inicialización del servicio."""
    print_section("TEST: Inicialización del Servicio OCR")

    try:
        from services.e14_ocr_service import get_e14_ocr_service
        service = get_e14_ocr_service()
        print(f"  {GREEN}✓{RESET} Servicio inicializado")
        print(f"    - Modelo: {service.model}")
        print(f"    - Max tokens: {service.max_tokens}")
        print(f"    - Timeout: {service.timeout}s")
    except ValueError as e:
        print(f"  {YELLOW}⚠{RESET} API Key no configurada: {e}")
    except Exception as e:
        print(f"  {RED}✗{RESET} Error: {e}")


def test_process_pdf_v2(pdf_path: str):
    """Test de procesamiento de PDF con v2."""
    print_section(f"TEST: Procesamiento V2 - {Path(pdf_path).name}")

    from services.e14_ocr_service import (
        get_e14_ocr_service,
        save_payload_v2_json,
        SourceType
    )

    if not Path(pdf_path).exists():
        print(f"  {RED}✗{RESET} Archivo no encontrado: {pdf_path}")
        return

    try:
        service = get_e14_ocr_service()

        print(f"  Procesando PDF...")
        payload = service.process_pdf_v2(
            pdf_path=pdf_path,
            source_type=SourceType.WITNESS_UPLOAD
        )

        print(f"  {GREEN}✓{RESET} PDF procesado exitosamente\n")

        # Mostrar resumen del payload
        print_field("event_type", payload.event_type)
        print_field("schema_version", payload.schema_version)
        print_field("produced_at", payload.produced_at)

        print(f"\n  {YELLOW}Pipeline Context:{RESET}")
        print_field("process_type", payload.pipeline_context.target_process.process_type.value, 2)
        print_field("contest_type", payload.pipeline_context.target_process.contest_type.value, 2)
        print_field("template_version", payload.pipeline_context.template_version, 2)

        print(f"\n  {YELLOW}Document Header:{RESET}")
        header = payload.document_header_extracted
        print_field("mesa_id", header.mesa_id, 2)
        print_field("corporacion", header.corporacion.value, 2)
        print_field("dept", f"{header.dept_code} - {header.dept_name}", 2)
        print_field("muni", f"{header.muni_code} - {header.muni_name}", 2)
        print_field("table_number", header.table_number, 2)

        print(f"\n  {YELLOW}OCR Fields:{RESET}")
        print_field("total_fields", len(payload.ocr_fields), 2)
        needs_review = [f for f in payload.ocr_fields if f.needs_review]
        print_field("fields_needing_review", len(needs_review), 2)
        with_marks = [f for f in payload.ocr_fields if f.raw_mark]
        print_field("fields_with_marks", len(with_marks), 2)

        # Mostrar campos con marcas
        if with_marks:
            print(f"\n    Campos con raw_mark:")
            for f in with_marks[:5]:
                print(f"      - {f.field_key}: raw_mark='{f.raw_mark}', value={f.value_int}")

        print(f"\n  {YELLOW}Normalized Tallies:{RESET}")
        print_field("groups", len(payload.normalized_tallies), 2)

        print(f"\n  {YELLOW}Validations:{RESET}")
        for v in payload.validations:
            status = f"{GREEN}✓{RESET}" if v.passed else f"{RED}✗{RESET}"
            print(f"    {status} {v.rule_key}: {v.severity.value}")

        # Guardar payload
        output_dir = Path(__file__).parent.parent / "output" / "v2_payloads"
        output_file = output_dir / f"{Path(pdf_path).stem}_v2.json"
        save_payload_v2_json(payload, str(output_file))
        print(f"\n  {GREEN}✓{RESET} Payload guardado en: {output_file}")

    except ValueError as e:
        print(f"  {RED}✗{RESET} Error de valor: {e}")
    except Exception as e:
        print(f"  {RED}✗{RESET} Error: {e}")
        import traceback
        traceback.print_exc()


def test_convert_v1_to_v2():
    """Test de conversión v1 a v2."""
    print_section("TEST: Conversión V1 → V2")

    from services.e14_ocr_service import convert_v1_to_v2
    from app.schemas.e14 import (
        E14ExtractionResult,
        E14Header,
        NivelacionMesa,
        PartyVotes,
        VotosEspeciales,
        CopyType,
        Corporacion,
        ListType,
    )

    # Crear un resultado v1 de ejemplo
    v1_result = E14ExtractionResult(
        extraction_id="test-v1-001",
        source_file="test.pdf",
        source_sha256="abc123",
        model_version="claude-sonnet-4-20250514",
        processing_time_ms=5000,
        header=E14Header(
            copy_type=CopyType.DELEGADOS,
            corporacion=Corporacion.CONSULTA,
            departamento_code="11",
            departamento_name="BOGOTA",
            municipio_code="001",
            municipio_name="BOGOTA",
            zona="01",
            puesto="01",
            mesa="001"
        ),
        nivelacion=NivelacionMesa(
            total_sufragantes_e11=500,
            total_votos_urna=498
        ),
        partidos=[
            PartyVotes(
                party_code="0001",
                party_name="CANDIDATO A",
                list_type=ListType.SIN_VOTO_PREFERENTE,
                total_votos=200
            ),
            PartyVotes(
                party_code="0002",
                party_name="CANDIDATO B",
                list_type=ListType.SIN_VOTO_PREFERENTE,
                total_votos=280
            )
        ],
        votos_especiales=VotosEspeciales(
            votos_blanco=10,
            votos_nulos=5,
            votos_no_marcados=3
        ),
        overall_confidence=0.92,
        fields_needing_review=0,
        total_pages=1,
        pages_processed=1
    )

    print(f"  V1 Result creado: {v1_result.extraction_id}")

    # Convertir a v2
    v2_payload = convert_v1_to_v2(v1_result)

    print(f"  {GREEN}✓{RESET} Convertido a V2")
    print_field("schema_version", v2_payload.schema_version)
    print_field("mesa_id", v2_payload.document_header_extracted.mesa_id)
    print_field("ocr_fields", len(v2_payload.ocr_fields))
    print_field("normalized_tallies", len(v2_payload.normalized_tallies))
    print_field("meta.converted_from", v2_payload.meta.get("converted_from"))

    print(f"\n  {GREEN}✓ Conversión V1→V2 exitosa{RESET}")


def main():
    """Ejecuta todos los tests."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  E14 OCR SERVICE V2 - Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Tests de estructura
    test_v2_payload_structure()
    test_v2_enums()
    test_service_initialization()
    test_convert_v1_to_v2()

    # Test de procesamiento real si se proporciona PDF
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        test_process_pdf_v2(pdf_path)
    else:
        # Buscar PDF de prueba
        test_pdfs = [
            "/Users/arielsanroj/Downloads/document.pdf",
            "/Users/arielsanroj/Downloads/1.pdf",
        ]
        for pdf in test_pdfs:
            if Path(pdf).exists():
                print(f"\n{YELLOW}¿Desea procesar {Path(pdf).name}? [s/N]:{RESET} ", end="")
                try:
                    resp = input().strip().lower()
                    if resp == 's':
                        test_process_pdf_v2(pdf)
                except:
                    pass
                break

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{GREEN}✓ TESTS COMPLETADOS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
