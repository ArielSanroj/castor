#!/usr/bin/env python3
"""
Batch OCR Processing for E-14 PDFs

Processes the 486 PDFs from ~/actas_e14_masivo/pdfs_congreso_2022/
using Castor's E14 OCR service (Claude Vision).

Usage:
    python scripts/batch_ocr_e14.py                    # Process all PDFs
    python scripts/batch_ocr_e14.py --limit 10         # Process first 10
    python scripts/batch_ocr_e14.py --dry-run          # Test without processing
    python scripts/batch_ocr_e14.py --resume           # Resume from last position

Cost estimate: ~$0.10 per PDF = ~$50 for 486 PDFs
"""
import argparse
import glob
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('batch_ocr_e14.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PDF_DIR = os.path.expanduser("~/actas_e14_masivo/pdfs_congreso_2022")
OUTPUT_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/batch_ocr_results")
PROGRESS_FILE = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/batch_ocr_progress.json")
BATCH_SIZE = 50


@dataclass
class PDFMetadata:
    """Metadata extracted from PDF filename."""
    filename: str
    filepath: str
    mesa_id: str
    corporacion: str  # SEN or CAM
    dept_code: str
    muni_code: str
    zone_code: str
    station_code: str

    @classmethod
    def from_filename(cls, filepath: str) -> "PDFMetadata":
        """
        Parse metadata from E-14 PDF filename.

        Format: {MESA_ID}_E14_{CORP}_X_{DEPT}_{MUNI}_{ZONE}_XX_{ZONE2}_{STATION}_X_XXX.pdf
        Example: 2043318_E14_SEN_X_01_001_003_XX_02_026_X_XXX.pdf
        """
        filename = os.path.basename(filepath)
        parts = filename.replace('.pdf', '').split('_')

        # Extract mesa ID (first part)
        mesa_id = parts[0] if len(parts) > 0 else ""

        # Extract corporacion (third part: SEN or CAM)
        corporacion = parts[2] if len(parts) > 2 else ""

        # Extract location codes
        # Pattern: ..._X_01_001_003_XX_02_026_...
        # Dept is typically position 4, Muni is 5, Zone is 6
        dept_code = parts[4] if len(parts) > 4 else ""
        muni_code = parts[5] if len(parts) > 5 else ""
        zone_code = parts[6] if len(parts) > 6 else ""

        # Station code is typically after XX
        station_code = ""
        try:
            xx_idx = parts.index('XX')
            if len(parts) > xx_idx + 2:
                station_code = parts[xx_idx + 2]
        except (ValueError, IndexError):
            pass

        return cls(
            filename=filename,
            filepath=filepath,
            mesa_id=mesa_id,
            corporacion=corporacion,
            dept_code=dept_code,
            muni_code=muni_code,
            zone_code=zone_code,
            station_code=station_code,
        )


@dataclass
class ProcessingResult:
    """Result of processing a single PDF."""
    filename: str
    success: bool
    processing_time_seconds: float
    error_message: Optional[str] = None
    extraction_id: Optional[str] = None
    confidence: Optional[float] = None
    needs_review_count: int = 0
    total_votos: Optional[int] = None
    output_path: Optional[str] = None


class BatchOCRProcessor:
    """Batch processor for E-14 PDFs."""

    def __init__(
        self,
        pdf_dir: str = DEFAULT_PDF_DIR,
        output_dir: str = OUTPUT_DIR,
        dry_run: bool = False,
    ):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.ocr_service = None

        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Load progress
        self.progress = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        """Load processing progress from file."""
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        return {
            "processed": [],
            "failed": [],
            "skipped": [],
            "last_index": 0,
            "started_at": None,
            "completed_at": None,
        }

    def _save_progress(self):
        """Save processing progress to file."""
        Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f, indent=2, default=str)

    def get_pdf_files(self) -> List[str]:
        """Get list of PDF files to process."""
        pattern = os.path.join(self.pdf_dir, "*.pdf")
        files = sorted(glob.glob(pattern))
        logger.info(f"Found {len(files)} PDF files in {self.pdf_dir}")
        return files

    def _init_ocr_service(self):
        """Initialize OCR service lazily."""
        if self.ocr_service is None and not self.dry_run:
            from services.e14_ocr_service import get_e14_ocr_service
            self.ocr_service = get_e14_ocr_service()
            logger.info("OCR service initialized")

    def process_single_pdf(self, pdf_path: str) -> ProcessingResult:
        """Process a single PDF file."""
        metadata = PDFMetadata.from_filename(pdf_path)
        start_time = time.time()

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would process: {metadata.filename}")
            return ProcessingResult(
                filename=metadata.filename,
                success=True,
                processing_time_seconds=0,
            )

        try:
            self._init_ocr_service()

            # Read PDF bytes
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            logger.info(f"Processing: {metadata.filename} ({len(pdf_bytes) / 1024:.1f} KB)")

            # Determine corporacion hint
            corp_hint = "SENADO" if metadata.corporacion == "SEN" else "CAMARA"

            # Process with OCR service (v2)
            payload = self.ocr_service.process_pdf_v2(
                pdf_bytes=pdf_bytes,
                corporacion_hint=corp_hint,
            )

            # Extract summary info
            overall_confidence = payload.meta.get('overall_confidence', 0.0) if payload.meta else 0.0
            needs_review_count = sum(1 for f in payload.ocr_fields if f.needs_review)

            # Get total votes if available
            total_votos = None
            for field in payload.ocr_fields:
                if field.field_key == "TOTAL_VOTOS_MESA" and field.value_int is not None:
                    total_votos = field.value_int
                    break

            # Save result JSON
            output_filename = f"{metadata.mesa_id}_{metadata.corporacion}_result.json"
            output_path = os.path.join(self.output_dir, output_filename)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(
                    payload.dict(by_alias=True, exclude_none=True),
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                )

            processing_time = time.time() - start_time

            logger.info(
                f"Processed: {metadata.filename} | "
                f"Confidence: {overall_confidence:.2f} | "
                f"Review: {needs_review_count} fields | "
                f"Time: {processing_time:.1f}s"
            )

            return ProcessingResult(
                filename=metadata.filename,
                success=True,
                processing_time_seconds=processing_time,
                extraction_id=payload.context.extraction_id if payload.context else None,
                confidence=overall_confidence,
                needs_review_count=needs_review_count,
                total_votos=total_votos,
                output_path=output_path,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to process {metadata.filename}: {e}")

            return ProcessingResult(
                filename=metadata.filename,
                success=False,
                processing_time_seconds=processing_time,
                error_message=str(e),
            )

    def process_batch(
        self,
        limit: Optional[int] = None,
        resume: bool = False,
        batch_size: int = BATCH_SIZE,
    ) -> Dict[str, Any]:
        """
        Process PDFs in batches.

        Args:
            limit: Maximum number of PDFs to process
            resume: Resume from last position
            batch_size: Number of PDFs per batch (for progress reporting)

        Returns:
            Summary statistics
        """
        pdf_files = self.get_pdf_files()

        # Handle resume
        start_index = 0
        if resume and self.progress.get("processed"):
            processed_files = set(self.progress["processed"])
            start_index = len(processed_files)
            pdf_files = [f for f in pdf_files if os.path.basename(f) not in processed_files]
            logger.info(f"Resuming from index {start_index}, {len(pdf_files)} remaining")

        # Apply limit
        if limit:
            pdf_files = pdf_files[:limit]

        total_files = len(pdf_files)
        if total_files == 0:
            logger.info("No files to process")
            return {"processed": 0, "success": 0, "failed": 0}

        logger.info(f"Processing {total_files} PDFs...")
        logger.info(f"Estimated cost: ${total_files * 0.10:.2f}")

        if not self.dry_run:
            # Confirm before processing
            confirm = input(f"\nProceed with processing {total_files} PDFs? [y/N]: ")
            if confirm.lower() != 'y':
                logger.info("Aborted by user")
                return {"aborted": True}

        # Initialize progress
        self.progress["started_at"] = datetime.now().isoformat()

        results = []
        success_count = 0
        failed_count = 0
        total_time = 0

        for i, pdf_path in enumerate(pdf_files):
            filename = os.path.basename(pdf_path)

            # Skip already processed
            if filename in self.progress.get("processed", []):
                logger.info(f"[{i+1}/{total_files}] Skipping (already processed): {filename}")
                continue

            # Process
            logger.info(f"[{i+1}/{total_files}] Processing: {filename}")
            result = self.process_single_pdf(pdf_path)
            results.append(result)

            if result.success:
                success_count += 1
                self.progress["processed"].append(filename)
            else:
                failed_count += 1
                self.progress["failed"].append({
                    "filename": filename,
                    "error": result.error_message,
                })

            total_time += result.processing_time_seconds
            self.progress["last_index"] = start_index + i + 1

            # Save progress every batch
            if (i + 1) % batch_size == 0:
                self._save_progress()
                avg_time = total_time / (i + 1)
                remaining = total_files - (i + 1)
                eta_seconds = remaining * avg_time
                logger.info(
                    f"Batch complete: {i+1}/{total_files} | "
                    f"Success: {success_count} | Failed: {failed_count} | "
                    f"ETA: {eta_seconds/60:.1f} min"
                )

            # Rate limiting (avoid overwhelming the API)
            if not self.dry_run and i < len(pdf_files) - 1:
                time.sleep(1)  # 1 second between requests

        # Final save
        self.progress["completed_at"] = datetime.now().isoformat()
        self._save_progress()

        # Generate summary
        summary = {
            "processed": len(results),
            "success": success_count,
            "failed": failed_count,
            "total_time_seconds": total_time,
            "avg_time_per_pdf_seconds": total_time / max(len(results), 1),
            "estimated_cost_usd": success_count * 0.10,
        }

        # Calculate confidence stats
        confidences = [r.confidence for r in results if r.confidence is not None]
        if confidences:
            summary["avg_confidence"] = sum(confidences) / len(confidences)
            summary["min_confidence"] = min(confidences)
            summary["max_confidence"] = max(confidences)

        # Count fields needing review
        review_counts = [r.needs_review_count for r in results if r.success]
        if review_counts:
            summary["total_fields_needing_review"] = sum(review_counts)
            summary["pdfs_needing_review"] = sum(1 for c in review_counts if c > 0)

        # Save summary
        summary_path = os.path.join(self.output_dir, "processing_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Total: {summary['processed']} | Success: {summary['success']} | Failed: {summary['failed']}")
        logger.info(f"Total time: {summary['total_time_seconds']/60:.1f} minutes")
        logger.info(f"Estimated cost: ${summary['estimated_cost_usd']:.2f}")
        if 'avg_confidence' in summary:
            logger.info(f"Avg confidence: {summary['avg_confidence']:.2f}")
        logger.info(f"Results saved to: {self.output_dir}")
        logger.info("=" * 60)

        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Batch OCR processing for E-14 PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_ocr_e14.py                     # Process all PDFs
  python batch_ocr_e14.py --limit 5           # Process first 5 PDFs
  python batch_ocr_e14.py --dry-run           # Test without processing
  python batch_ocr_e14.py --resume            # Resume from last position
  python batch_ocr_e14.py --pdf-dir /path     # Custom PDF directory
        """
    )

    parser.add_argument(
        "--pdf-dir",
        default=DEFAULT_PDF_DIR,
        help=f"Directory containing PDF files (default: {DEFAULT_PDF_DIR})"
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"Output directory for results (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of PDFs to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actual processing"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last processing position"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for progress reporting (default: {BATCH_SIZE})"
    )

    args = parser.parse_args()

    # Validate PDF directory
    if not os.path.isdir(args.pdf_dir):
        logger.error(f"PDF directory not found: {args.pdf_dir}")
        sys.exit(1)

    # Create processor
    processor = BatchOCRProcessor(
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    # Process
    try:
        summary = processor.process_batch(
            limit=args.limit,
            resume=args.resume,
            batch_size=args.batch_size,
        )

        # Exit with error code if there were failures
        if summary.get("failed", 0) > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Progress has been saved.")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
