#!/usr/bin/env python3
"""
Script para generar datos de entrenamiento de E-14.
Usa Claude para crear ground truth que luego se usa para fine-tuning de modelo local.

Uso:
    # Procesar un PDF
    python scripts/generate_training_data.py process /path/to/e14.pdf

    # Procesar desde URL
    python scripts/generate_training_data.py process-url https://...

    # Procesar múltiples PDFs de un directorio
    python scripts/generate_training_data.py batch /path/to/pdfs/

    # Ver estadísticas
    python scripts/generate_training_data.py stats

    # Listar samples pendientes de validación
    python scripts/generate_training_data.py list --pending

    # Validar un sample (marcarlo como listo para training)
    python scripts/generate_training_data.py validate <sample_id>

    # Exportar para fine-tuning
    python scripts/generate_training_data.py export --format llava
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')


def process_single(args):
    """Procesa un solo PDF."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    result = service.process_and_save(pdf_path=args.pdf_path)

    print(f"\n{'='*50}")
    print(f"Resultado: {result['status']}")
    print(f"Sample ID: {result.get('sample_id')}")
    print(f"Páginas: {result.get('pages')}")
    print(f"OCR: {'✓' if result.get('ocr_success') else '✗'}")
    print(f"Validación: {'✓' if result.get('validation_passed') else '✗'}")
    print(f"Label: {result.get('label_path')}")
    print(f"{'='*50}\n")

    # Mostrar stats actualizadas
    stats = service.get_stats()
    print(f"Dataset total: {stats['total_samples']} samples, {stats['total_pages']} páginas")
    print(f"Validados: {stats['validated']} | Pendientes: {stats['pending_validation']}")


def process_url(args):
    """Procesa un PDF desde URL."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    result = service.process_and_save(pdf_url=args.url)

    print(f"\n{'='*50}")
    print(f"Resultado: {result['status']}")
    print(f"Sample ID: {result.get('sample_id')}")
    print(f"Páginas: {result.get('pages')}")
    print(f"OCR: {'✓' if result.get('ocr_success') else '✗'}")
    print(f"Validación: {'✓' if result.get('validation_passed') else '✗'}")
    print(f"{'='*50}\n")


def process_batch(args):
    """Procesa múltiples PDFs de un directorio."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    pdf_dir = Path(args.directory)

    if not pdf_dir.exists():
        print(f"Error: Directorio {pdf_dir} no existe")
        return

    pdfs = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
    print(f"Encontrados {len(pdfs)} PDFs en {pdf_dir}")

    if args.limit:
        pdfs = pdfs[:args.limit]
        print(f"Procesando primeros {args.limit}")

    results = {"success": 0, "duplicate": 0, "failed": 0}

    for i, pdf_path in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] Procesando: {pdf_path.name}")
        try:
            result = service.process_and_save(pdf_path=str(pdf_path))
            results[result["status"]] = results.get(result["status"], 0) + 1
            print(f"  → {result['status']} (ID: {result.get('sample_id', 'N/A')})")
        except Exception as e:
            results["failed"] += 1
            print(f"  → ERROR: {e}")

    print(f"\n{'='*50}")
    print(f"Resumen: {results}")
    print(f"{'='*50}")


def show_stats(args):
    """Muestra estadísticas del dataset."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    stats = service.get_stats()

    print(f"\n{'='*50}")
    print(f"📊 ESTADÍSTICAS DEL DATASET E-14")
    print(f"{'='*50}")
    print(f"Total samples:        {stats['total_samples']}")
    print(f"Total páginas:        {stats['total_pages']}")
    print(f"Validados:            {stats['validated']}")
    print(f"Corregidos:           {stats['corrected']}")
    print(f"Pendientes validar:   {stats['pending_validation']}")
    print(f"Fallidos OCR:         {stats['failed_ocr']}")
    print(f"{'='*50}")
    print(f"Directorio:           {stats['data_dir']}")
    print(f"{'='*50}\n")

    # Costo estimado
    estimated_cost = stats['total_samples'] * 0.10
    print(f"💰 Costo estimado API: ~${estimated_cost:.2f}")
    print(f"   (${0.10} por E-14 con Claude Vision)\n")


def list_samples(args):
    """Lista los samples."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    samples = service.list_samples(only_pending=args.pending)

    print(f"\n{'='*60}")
    print(f"{'PENDIENTES' if args.pending else 'TODOS LOS'} SAMPLES ({len(samples)})")
    print(f"{'='*60}")

    for s in samples:
        status = "✓" if s.get("is_validated") else "○"
        ocr = "OCR:OK" if s.get("ocr_success") else "OCR:FAIL"
        print(f"{status} [{s['sample_id']}] {s['pages']}p | {ocr} | {s.get('source', 'N/A')[:40]}")

    print(f"{'='*60}\n")


def validate_sample(args):
    """Marca un sample como validado."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()
    success = service.validate_sample(args.sample_id)

    if success:
        print(f"✓ Sample {args.sample_id} validado")
    else:
        print(f"✗ Error validando sample {args.sample_id}")


def export_data(args):
    """Exporta datos para fine-tuning."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()

    try:
        export_path = service.export_for_finetuning(
            output_format=args.format,
            only_validated=not args.all
        )
        print(f"\n✓ Exportado a: {export_path}")
        print(f"  Formato: {args.format}")
        print(f"  Solo validados: {not args.all}\n")
    except ValueError as e:
        print(f"✗ Error: {e}")


def correct_sample(args):
    """Aplica correcciones a un sample."""
    from services.e14_training_service import get_e14_training_service

    service = get_e14_training_service()

    # Parsear correcciones del formato "path=value,path2=value2"
    corrections = {}
    for corr in args.corrections.split(','):
        path, value = corr.split('=')
        # Intentar parsear como número
        try:
            value = int(value)
        except ValueError:
            pass
        corrections[path.strip()] = value

    success = service.correct_sample(args.sample_id, corrections)

    if success:
        print(f"✓ Correcciones aplicadas a {args.sample_id}")
    else:
        print(f"✗ Error aplicando correcciones")


def main():
    parser = argparse.ArgumentParser(
        description="Generador de datos de entrenamiento E-14",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # process
    p_process = subparsers.add_parser("process", help="Procesa un PDF")
    p_process.add_argument("pdf_path", help="Ruta al PDF")
    p_process.set_defaults(func=process_single)

    # process-url
    p_url = subparsers.add_parser("process-url", help="Procesa PDF desde URL")
    p_url.add_argument("url", help="URL del PDF")
    p_url.set_defaults(func=process_url)

    # batch
    p_batch = subparsers.add_parser("batch", help="Procesa directorio de PDFs")
    p_batch.add_argument("directory", help="Directorio con PDFs")
    p_batch.add_argument("--limit", type=int, help="Límite de PDFs a procesar")
    p_batch.set_defaults(func=process_batch)

    # stats
    p_stats = subparsers.add_parser("stats", help="Muestra estadísticas")
    p_stats.set_defaults(func=show_stats)

    # list
    p_list = subparsers.add_parser("list", help="Lista samples")
    p_list.add_argument("--pending", action="store_true", help="Solo pendientes")
    p_list.set_defaults(func=list_samples)

    # validate
    p_val = subparsers.add_parser("validate", help="Valida un sample")
    p_val.add_argument("sample_id", help="ID del sample")
    p_val.set_defaults(func=validate_sample)

    # correct
    p_corr = subparsers.add_parser("correct", help="Corrige un sample")
    p_corr.add_argument("sample_id", help="ID del sample")
    p_corr.add_argument("corrections", help="Correcciones: 'path=value,path2=value2'")
    p_corr.set_defaults(func=correct_sample)

    # export
    p_exp = subparsers.add_parser("export", help="Exporta para fine-tuning")
    p_exp.add_argument("--format", choices=["llava", "qwen", "jsonl"], default="llava")
    p_exp.add_argument("--all", action="store_true", help="Incluir no validados")
    p_exp.set_defaults(func=export_data)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
