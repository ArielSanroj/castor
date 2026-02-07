#!/usr/bin/env python3
"""
Batch OCR Processing for all E-14 PDFs.
Processes PDFs using Tesseract and updates the database.
"""
import glob
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.e14_tesseract_ocr import E14TesseractOCR, TesseractOCRResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PDF_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/actas_e14_masivo/pdfs_congreso_2022")
DB_PATH = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")
OUTPUT_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/batch_ocr_results")


class BatchOCRProcessor:
    """Process all E-14 PDFs through Tesseract OCR."""

    def __init__(self):
        self.ocr = E14TesseractOCR()
        self.db_path = DB_PATH
        self.stats = {
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'errors': []
        }

    def get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_pending_pdfs(self) -> list:
        """Get list of PDFs that need OCR processing."""
        # Get all PDFs in directory
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {PDF_DIR}")

        # Get already processed from database
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename FROM e14_scraper_forms
            WHERE ocr_processed = 1
        """)
        processed_files = {row['filename'] for row in cursor.fetchall()}
        conn.close()

        logger.info(f"Already processed: {len(processed_files)} files")

        # Filter to pending
        pending = []
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            if filename not in processed_files:
                pending.append(pdf_path)

        logger.info(f"Pending OCR: {len(pending)} files")
        return pending

    def parse_filename(self, filename: str) -> dict:
        """Parse E-14 metadata from filename."""
        # Format: {MESA_ID}_E14_{CORP}_X_{DEPT}_{MUNI}_{...}.pdf
        try:
            clean_name = filename.replace('.pdf', '').replace(' (1)', '').replace(' (2)', '')
            parts = clean_name.split('_')
            if len(parts) >= 6:
                return {
                    'mesa_id': f"{parts[2]}-{parts[4]}-{parts[5]}-{parts[0]}",
                    'corporacion': 'SEN' if parts[2] == 'SEN' else 'CAM',
                    'dept_code': parts[4],
                    'muni_code': parts[5],
                }
        except Exception:
            pass
        return {}

    def update_database(self, pdf_path: str, result: TesseractOCRResult):
        """Update database with OCR results."""
        conn = self.get_db()
        cursor = conn.cursor()
        filename = os.path.basename(pdf_path)

        try:
            # Check if record exists
            cursor.execute(
                "SELECT id FROM e14_scraper_forms WHERE filename = ?",
                (filename,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE e14_scraper_forms SET
                        ocr_processed = 1,
                        ocr_confidence = ?,
                        total_votos = ?,
                        votos_blancos = ?,
                        votos_nulos = ?,
                        ocr_at = ?
                    WHERE filename = ?
                """, (
                    result.confidence,
                    result.total_votos,
                    result.votos_blancos,
                    result.votos_nulos,
                    datetime.utcnow().isoformat(),
                    filename
                ))
                form_id = existing['id']
            else:
                # Parse metadata from filename
                meta = self.parse_filename(filename)
                mesa_id = f"{result.corporacion or 'UNK'}-{result.departamento or 'UNK'}-{result.municipio or 'UNK'}-{result.mesa or filename[:10]}"

                # Insert new record
                cursor.execute("""
                    INSERT INTO e14_scraper_forms (
                        mesa_id, pdf_path, filename, corporacion, departamento,
                        municipio, zona_cod, puesto_cod, mesa_num,
                        ocr_processed, ocr_confidence, total_votos,
                        votos_blancos, votos_nulos, ocr_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (
                    mesa_id,
                    pdf_path,
                    filename,
                    result.corporacion or meta.get('corporacion', 'UNK'),
                    result.departamento or 'UNKNOWN',
                    result.municipio or 'UNKNOWN',
                    result.zona or '',
                    result.puesto or '',
                    result.mesa or '',
                    result.confidence,
                    result.total_votos,
                    result.votos_blancos,
                    result.votos_nulos,
                    datetime.utcnow().isoformat()
                ))
                form_id = cursor.lastrowid

            # Insert party votes
            if result.partidos and form_id:
                # Delete existing votes
                cursor.execute(
                    "DELETE FROM e14_scraper_votes WHERE form_id = ?",
                    (form_id,)
                )

                # Insert new votes
                for partido in result.partidos:
                    cursor.execute("""
                        INSERT INTO e14_scraper_votes (
                            form_id, party_name, party_code, votes,
                            confidence, needs_review
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        form_id,
                        partido.get('party_name', ''),
                        partido.get('party_code', ''),
                        partido.get('votes', 0),
                        partido.get('confidence', 0.0),
                        1 if partido.get('needs_review', False) else 0
                    ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Database error for {filename}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def process_pdf(self, pdf_path: str) -> bool:
        """Process a single PDF file."""
        filename = os.path.basename(pdf_path)
        try:
            result = self.ocr.process_pdf(pdf_path)

            if result.success:
                # Update database
                if self.update_database(pdf_path, result):
                    self.stats['success'] += 1
                    logger.info(
                        f"✓ {filename}: conf={result.confidence:.2f}, "
                        f"votos={result.total_votos}, partidos={len(result.partidos)}"
                    )
                    return True
                else:
                    self.stats['failed'] += 1
                    return False
            else:
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'file': filename,
                    'error': result.error or 'Unknown error'
                })
                logger.warning(f"✗ {filename}: {result.error}")
                return False

        except Exception as e:
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'file': filename,
                'error': str(e)
            })
            logger.error(f"✗ {filename}: {e}")
            return False

    def run(self, limit: int = None):
        """Run batch processing."""
        self.stats['start_time'] = datetime.utcnow()

        # Get pending PDFs
        pending_pdfs = self.get_pending_pdfs()
        if limit:
            pending_pdfs = pending_pdfs[:limit]

        self.stats['total'] = len(pending_pdfs)

        if not pending_pdfs:
            logger.info("No pending PDFs to process")
            return self.stats

        logger.info(f"Starting batch OCR of {len(pending_pdfs)} PDFs...")
        print("=" * 60)
        print(f"BATCH OCR PROCESSING - {len(pending_pdfs)} files")
        print("=" * 60)

        for i, pdf_path in enumerate(pending_pdfs, 1):
            self.stats['processed'] += 1

            # Progress update
            if i % 10 == 0 or i == len(pending_pdfs):
                elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds()
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(pending_pdfs) - i) / rate if rate > 0 else 0
                print(f"\nProgress: {i}/{len(pending_pdfs)} ({i/len(pending_pdfs)*100:.1f}%) "
                      f"| Rate: {rate:.1f}/s | ETA: {eta/60:.1f}min")

            self.process_pdf(pdf_path)

        # Final stats
        elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        self.stats['elapsed_seconds'] = elapsed
        self.stats['rate_per_minute'] = (self.stats['processed'] / elapsed * 60) if elapsed > 0 else 0

        print("\n" + "=" * 60)
        print("BATCH OCR COMPLETE")
        print("=" * 60)
        print(f"Total files:     {self.stats['total']}")
        print(f"Processed:       {self.stats['processed']}")
        print(f"Success:         {self.stats['success']}")
        print(f"Failed:          {self.stats['failed']}")
        print(f"Time:            {elapsed/60:.1f} minutes")
        print(f"Rate:            {self.stats['rate_per_minute']:.1f} files/min")
        print("=" * 60)

        # Save stats
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        stats_file = os.path.join(OUTPUT_DIR, f"batch_stats_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)
        print(f"Stats saved to: {stats_file}")

        return self.stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Batch OCR processing for E-14 PDFs')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
    args = parser.parse_args()

    processor = BatchOCRProcessor()

    if args.dry_run:
        pending = processor.get_pending_pdfs()
        print(f"\nDRY RUN: Would process {len(pending)} PDFs")
        for pdf in pending[:10]:
            print(f"  - {os.path.basename(pdf)}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
        return

    processor.run(limit=args.limit)


if __name__ == "__main__":
    main()
