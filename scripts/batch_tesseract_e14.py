#!/usr/bin/env python3
"""
Batch Tesseract OCR Processing for E-14 PDFs.

Processes the 486 PDFs using Tesseract (free, offline OCR).
Lower accuracy than Vision API but good for initial data population.

Usage:
    python scripts/batch_tesseract_e14.py                    # Process all
    python scripts/batch_tesseract_e14.py --limit 10         # Process 10
    python scripts/batch_tesseract_e14.py --resume           # Resume
"""
import argparse
import glob
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.e14_tesseract_ocr import E14TesseractOCR, TesseractOCRResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('batch_tesseract_e14.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PDF_DIR = os.path.expanduser("~/actas_e14_masivo/pdfs_congreso_2022")
OUTPUT_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/tesseract_results")
PROGRESS_FILE = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/tesseract_progress.json")


class BatchTesseractProcessor:
    """Batch processor for E-14 PDFs using Tesseract."""

    def __init__(self, pdf_dir: str, output_dir: str):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        self.ocr = E14TesseractOCR()

        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Load progress
        self.progress = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        """Load processing progress."""
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        return {
            "processed": [],
            "failed": [],
            "started_at": None,
            "completed_at": None,
        }

    def _save_progress(self):
        """Save processing progress."""
        Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2, default=str)

    def get_pdf_files(self) -> List[str]:
        """Get list of PDF files."""
        pattern = os.path.join(self.pdf_dir, "*.pdf")
        files = sorted(glob.glob(pattern))
        logger.info(f"Found {len(files)} PDF files")
        return files

    def process_single(self, pdf_path: str) -> TesseractOCRResult:
        """Process a single PDF."""
        return self.ocr.process_pdf(pdf_path)

    def process_batch(
        self,
        limit: Optional[int] = None,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        Process PDFs in batch.

        Args:
            limit: Max PDFs to process
            resume: Resume from last position

        Returns:
            Summary statistics
        """
        pdf_files = self.get_pdf_files()

        # Handle resume
        if resume and self.progress.get("processed"):
            processed_set = set(self.progress["processed"])
            pdf_files = [f for f in pdf_files if os.path.basename(f) not in processed_set]
            logger.info(f"Resuming - {len(pdf_files)} remaining")

        # Apply limit
        if limit:
            pdf_files = pdf_files[:limit]

        total_files = len(pdf_files)
        if total_files == 0:
            logger.info("No files to process")
            return {"processed": 0}

        logger.info(f"Processing {total_files} PDFs with Tesseract...")
        self.progress["started_at"] = datetime.now().isoformat()

        results = []
        success_count = 0
        failed_count = 0
        total_time = 0

        for i, pdf_path in enumerate(pdf_files):
            filename = os.path.basename(pdf_path)

            # Skip already processed
            if filename in self.progress.get("processed", []):
                continue

            logger.info(f"[{i+1}/{total_files}] Processing: {filename}")

            try:
                result = self.process_single(pdf_path)
                results.append(result)

                if result.success:
                    success_count += 1
                    self.progress["processed"].append(filename)

                    # Save result JSON
                    output_file = os.path.join(
                        self.output_dir,
                        filename.replace('.pdf', '_tesseract.json')
                    )
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(asdict(result), f, ensure_ascii=False, indent=2, default=str)

                    logger.info(
                        f"  ✓ Confidence: {result.confidence:.2f} | "
                        f"Partidos: {len(result.partidos)} | "
                        f"Time: {result.processing_time_ms/1000:.1f}s"
                    )
                else:
                    failed_count += 1
                    self.progress["failed"].append({
                        "filename": filename,
                        "error": result.error
                    })
                    logger.warning(f"  ✗ Failed: {result.error}")

                total_time += result.processing_time_ms / 1000

            except Exception as e:
                failed_count += 1
                self.progress["failed"].append({
                    "filename": filename,
                    "error": str(e)
                })
                logger.error(f"  ✗ Error: {e}")

            # Save progress every 10 files
            if (i + 1) % 10 == 0:
                self._save_progress()
                avg_time = total_time / (i + 1)
                remaining = total_files - (i + 1)
                eta_min = (remaining * avg_time) / 60
                logger.info(f"Progress: {i+1}/{total_files} | ETA: {eta_min:.1f} min")

        # Final save
        self.progress["completed_at"] = datetime.now().isoformat()
        self._save_progress()

        # Summary
        summary = {
            "total_processed": len(results),
            "success": success_count,
            "failed": failed_count,
            "total_time_seconds": total_time,
            "avg_time_per_pdf": total_time / max(len(results), 1),
        }

        # Confidence stats
        confidences = [r.confidence for r in results if r.success]
        if confidences:
            summary["avg_confidence"] = sum(confidences) / len(confidences)
            summary["min_confidence"] = min(confidences)
            summary["max_confidence"] = max(confidences)

        # Party stats
        party_counts = [len(r.partidos) for r in results if r.success]
        if party_counts:
            summary["avg_partidos"] = sum(party_counts) / len(party_counts)

        # Save summary
        summary_path = os.path.join(self.output_dir, "tesseract_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Total: {summary['total_processed']} | Success: {success_count} | Failed: {failed_count}")
        logger.info(f"Time: {total_time/60:.1f} minutes ({summary['avg_time_per_pdf']:.1f}s per PDF)")
        if 'avg_confidence' in summary:
            logger.info(f"Avg confidence: {summary['avg_confidence']:.2f}")
        if 'avg_partidos' in summary:
            logger.info(f"Avg partidos found: {summary['avg_partidos']:.1f}")
        logger.info(f"Results saved to: {self.output_dir}")
        logger.info("=" * 60)

        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Batch Tesseract OCR for E-14 PDFs"
    )
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--limit", type=int, help="Max PDFs to process")
    parser.add_argument("--resume", action="store_true", help="Resume from last")

    args = parser.parse_args()

    if not os.path.isdir(args.pdf_dir):
        logger.error(f"PDF directory not found: {args.pdf_dir}")
        sys.exit(1)

    processor = BatchTesseractProcessor(
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
    )

    try:
        summary = processor.process_batch(
            limit=args.limit,
            resume=args.resume,
        )

        if summary.get("failed", 0) > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nInterrupted. Progress saved.")
        sys.exit(130)


if __name__ == "__main__":
    main()
