#!/usr/bin/env python3
"""
Load E-14 PDFs from scraper output to CASTOR database.

Fast initial load:
1. Scans all PDFs and extracts metadata from paths
2. Registers forms in database with location info
3. Queues for OCR processing in background

Usage:
    python scripts/load_e14_from_scraper.py                    # Register all
    python scripts/load_e14_from_scraper.py --ocr --workers 8  # With OCR
    python scripts/load_e14_from_scraper.py --limit 100        # Test with 100
"""
import argparse
import concurrent.futures
import json
import logging
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('load_e14_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

# Paths
SCRAPER_OUTPUT = os.path.expanduser("~/e14_scraper/output_e14")
CASTOR_DB = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")
PROGRESS_FILE = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/e14_load_progress.json")


@dataclass
class E14Form:
    """E-14 form metadata extracted from file path."""
    pdf_path: str
    filename: str
    corporacion: str  # SEN or CAM
    departamento: str
    municipio: str
    zona_cod: str
    puesto_cod: str
    mesa_num: str

    # OCR data (filled later)
    ocr_processed: bool = False
    ocr_confidence: float = 0.0
    total_votos: int = 0
    votos_blancos: int = 0
    votos_nulos: int = 0
    partidos: List[Dict] = None

    def __post_init__(self):
        if self.partidos is None:
            self.partidos = []

    @property
    def mesa_id(self) -> str:
        """Generate unique mesa ID."""
        return f"{self.corporacion}-{self.departamento}-{self.municipio}-{self.zona_cod}-{self.puesto_cod}-{self.mesa_num}"


def parse_pdf_path(pdf_path: str) -> Optional[E14Form]:
    """
    Parse E-14 metadata from file path.

    Expected structure:
        output_e14/{CORP}/{DEPTO}/{MPIO}/{zona}_{puesto}_mesa{N}.pdf

    Example:
        output_e14/SEN/ANTIOQUIA/MEDELLIN/01_001_mesa1.pdf
    """
    try:
        parts = Path(pdf_path).parts
        filename = parts[-1]

        # Find index of output_e14
        try:
            idx = parts.index('output_e14')
        except ValueError:
            # Try alternative path patterns
            idx = len(parts) - 5 if len(parts) >= 5 else 0

        if len(parts) < idx + 5:
            return None

        corp = parts[idx + 1]  # SEN or CAM
        depto = parts[idx + 2]
        mpio = parts[idx + 3]

        # Parse filename: zona_puesto_mesaN.pdf
        match = re.match(r'(\d+)_(\d+)_mesa(\d+)\.pdf', filename, re.IGNORECASE)
        if not match:
            # Try alternative format
            match = re.match(r'(\w+)_(\w+)_mesa(\d+)\.pdf', filename, re.IGNORECASE)
            if not match:
                return None

        zona_cod = match.group(1)
        puesto_cod = match.group(2)
        mesa_num = match.group(3)

        return E14Form(
            pdf_path=pdf_path,
            filename=filename,
            corporacion=corp,
            departamento=depto,
            municipio=mpio,
            zona_cod=zona_cod,
            puesto_cod=puesto_cod,
            mesa_num=mesa_num,
        )
    except Exception as e:
        logger.warning(f"Failed to parse {pdf_path}: {e}")
        return None


def scan_pdfs(base_dir: str) -> List[E14Form]:
    """Scan all PDFs and extract metadata."""
    forms = []

    logger.info(f"Scanning PDFs in {base_dir}...")

    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, filename)
                form = parse_pdf_path(pdf_path)
                if form:
                    forms.append(form)

    logger.info(f"Found {len(forms):,} valid E-14 PDFs")
    return forms


def init_database(db_path: str):
    """Initialize SQLite database with E-14 tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        -- E-14 Forms (mesas) from scraper
        CREATE TABLE IF NOT EXISTS e14_scraper_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_id TEXT UNIQUE NOT NULL,
            pdf_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            corporacion TEXT NOT NULL,
            departamento TEXT NOT NULL,
            municipio TEXT NOT NULL,
            zona_cod TEXT,
            puesto_cod TEXT,
            mesa_num TEXT,
            ocr_processed INTEGER DEFAULT 0,
            ocr_confidence REAL DEFAULT 0,
            total_votos INTEGER DEFAULT 0,
            votos_blancos INTEGER DEFAULT 0,
            votos_nulos INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ocr_at TIMESTAMP
        );

        -- E-14 Party Votes from scraper
        CREATE TABLE IF NOT EXISTS e14_scraper_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id INTEGER REFERENCES e14_scraper_forms(id) ON DELETE CASCADE,
            party_name TEXT NOT NULL,
            party_code TEXT,
            votes INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0,
            needs_review INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_scraper_forms_dept ON e14_scraper_forms(departamento);
        CREATE INDEX IF NOT EXISTS idx_scraper_forms_mpio ON e14_scraper_forms(municipio);
        CREATE INDEX IF NOT EXISTS idx_scraper_forms_corp ON e14_scraper_forms(corporacion);
        CREATE INDEX IF NOT EXISTS idx_scraper_forms_ocr ON e14_scraper_forms(ocr_processed);
        CREATE INDEX IF NOT EXISTS idx_scraper_votes_form ON e14_scraper_votes(form_id);
        CREATE INDEX IF NOT EXISTS idx_scraper_votes_party ON e14_scraper_votes(party_name);

        -- Summary views
        CREATE VIEW IF NOT EXISTS e14_scraper_summary AS
        SELECT
            corporacion,
            departamento,
            COUNT(*) as total_mesas,
            SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as ocr_completed,
            SUM(total_votos) as total_votos,
            AVG(ocr_confidence) as avg_confidence
        FROM e14_scraper_forms
        GROUP BY corporacion, departamento;

        CREATE VIEW IF NOT EXISTS e14_scraper_party_totals AS
        SELECT
            party_name,
            SUM(votes) as total_votes,
            COUNT(DISTINCT form_id) as mesas_count,
            AVG(confidence) as avg_confidence
        FROM e14_scraper_votes
        GROUP BY party_name
        ORDER BY total_votes DESC;
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {db_path}")


def load_forms_to_db(forms: List[E14Form], db_path: str, batch_size: int = 1000):
    """Load forms to database in batches."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total = len(forms)
    inserted = 0
    skipped = 0

    logger.info(f"Loading {total:,} forms to database...")

    for i in range(0, total, batch_size):
        batch = forms[i:i + batch_size]

        for form in batch:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO e14_scraper_forms
                    (mesa_id, pdf_path, filename, corporacion, departamento,
                     municipio, zona_cod, puesto_cod, mesa_num)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    form.mesa_id,
                    form.pdf_path,
                    form.filename,
                    form.corporacion,
                    form.departamento,
                    form.municipio,
                    form.zona_cod,
                    form.puesto_cod,
                    form.mesa_num,
                ))

                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1

            except Exception as e:
                logger.warning(f"Error inserting {form.mesa_id}: {e}")
                skipped += 1

        conn.commit()

        if (i + batch_size) % 10000 == 0 or i + batch_size >= total:
            pct = min(100, ((i + batch_size) / total) * 100)
            logger.info(f"Progress: {pct:.1f}% ({inserted:,} inserted, {skipped:,} skipped)")

    conn.close()

    logger.info(f"Load complete: {inserted:,} inserted, {skipped:,} skipped")
    return inserted


def get_stats(db_path: str) -> Dict[str, Any]:
    """Get database statistics."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # Total forms
    cursor.execute("SELECT COUNT(*) FROM e14_scraper_forms")
    stats['total_forms'] = cursor.fetchone()[0]

    # By corporacion
    cursor.execute("""
        SELECT corporacion, COUNT(*)
        FROM e14_scraper_forms
        GROUP BY corporacion
    """)
    stats['by_corporacion'] = dict(cursor.fetchall())

    # By departamento
    cursor.execute("""
        SELECT departamento, COUNT(*) as cnt
        FROM e14_scraper_forms
        GROUP BY departamento
        ORDER BY cnt DESC
        LIMIT 10
    """)
    stats['top_departamentos'] = cursor.fetchall()

    # OCR status
    cursor.execute("""
        SELECT
            SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN ocr_processed = 0 THEN 1 ELSE 0 END) as pending
        FROM e14_scraper_forms
    """)
    row = cursor.fetchone()
    stats['ocr_completed'] = row[0] or 0
    stats['ocr_pending'] = row[1] or 0

    conn.close()
    return stats


def process_with_ocr(form: E14Form, ocr_service) -> E14Form:
    """Process a single form with Tesseract OCR."""
    try:
        result = ocr_service.process_pdf(form.pdf_path)

        form.ocr_processed = True
        form.ocr_confidence = result.confidence
        form.total_votos = result.total_votos
        form.votos_blancos = result.votos_blancos
        form.votos_nulos = result.votos_nulos
        form.partidos = result.partidos

    except Exception as e:
        logger.warning(f"OCR failed for {form.mesa_id}: {e}")
        form.ocr_processed = True
        form.ocr_confidence = 0

    return form


def run_ocr_batch(db_path: str, limit: int = None, workers: int = 4):
    """Run OCR on unprocessed forms."""
    from services.e14_tesseract_ocr import E14TesseractOCR

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get unprocessed forms
    query = """
        SELECT id, pdf_path, mesa_id
        FROM e14_scraper_forms
        WHERE ocr_processed = 0
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.info("No forms pending OCR")
        return

    total = len(rows)
    logger.info(f"Processing {total:,} forms with OCR ({workers} workers)...")

    ocr = E14TesseractOCR()
    processed = 0
    start_time = time.time()

    def process_one(row):
        form_id, pdf_path, mesa_id = row
        try:
            result = ocr.process_pdf(pdf_path)
            return (form_id, True, result)
        except Exception as e:
            return (form_id, False, str(e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_one, row): row for row in rows}

        for future in concurrent.futures.as_completed(futures):
            form_id, success, result = future.result()
            processed += 1

            # Update database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if success:
                cursor.execute("""
                    UPDATE e14_scraper_forms
                    SET ocr_processed = 1,
                        ocr_confidence = ?,
                        total_votos = ?,
                        votos_blancos = ?,
                        votos_nulos = ?,
                        ocr_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    result.confidence,
                    result.total_votos,
                    result.votos_blancos,
                    result.votos_nulos,
                    form_id
                ))

                # Insert party votes
                for partido in result.partidos:
                    cursor.execute("""
                        INSERT INTO e14_scraper_votes
                        (form_id, party_name, party_code, votes, confidence, needs_review)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        form_id,
                        partido.get('party_name', ''),
                        partido.get('party_code', ''),
                        partido.get('votes', 0),
                        partido.get('confidence', 0),
                        1 if partido.get('needs_review') else 0
                    ))
            else:
                cursor.execute("""
                    UPDATE e14_scraper_forms
                    SET ocr_processed = 1, ocr_confidence = 0, ocr_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (form_id,))

            conn.commit()
            conn.close()

            # Progress
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                remaining = total - processed
                eta = remaining / rate if rate > 0 else 0
                logger.info(f"OCR Progress: {processed}/{total} ({rate:.1f}/s, ETA: {eta/60:.1f}min)")

    elapsed = time.time() - start_time
    logger.info(f"OCR complete: {processed} forms in {elapsed/60:.1f} minutes")


def main():
    parser = argparse.ArgumentParser(description="Load E-14 PDFs from scraper to CASTOR")
    parser.add_argument("--input-dir", default=SCRAPER_OUTPUT, help="Scraper output directory")
    parser.add_argument("--db", default=CASTOR_DB, help="CASTOR database path")
    parser.add_argument("--limit", type=int, help="Limit number of forms to process")
    parser.add_argument("--ocr", action="store_true", help="Run OCR processing")
    parser.add_argument("--workers", type=int, default=4, help="OCR worker threads")
    parser.add_argument("--stats-only", action="store_true", help="Show stats only")

    args = parser.parse_args()

    # Ensure directories exist
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    # Init database
    init_database(args.db)

    if args.stats_only:
        stats = get_stats(args.db)
        print("\n" + "="*60)
        print("E-14 SCRAPER DATA STATISTICS")
        print("="*60)
        print(f"Total forms: {stats['total_forms']:,}")
        print(f"By corporación: {stats['by_corporacion']}")
        print(f"OCR completed: {stats['ocr_completed']:,}")
        print(f"OCR pending: {stats['ocr_pending']:,}")
        print("\nTop departamentos:")
        for dept, count in stats['top_departamentos']:
            print(f"  {dept}: {count:,}")
        print("="*60)
        return

    # Scan and load forms
    if not args.ocr:
        forms = scan_pdfs(args.input_dir)

        if args.limit:
            forms = forms[:args.limit]

        if forms:
            load_forms_to_db(forms, args.db)

    # Run OCR if requested
    if args.ocr:
        run_ocr_batch(args.db, limit=args.limit, workers=args.workers)

    # Show final stats
    stats = get_stats(args.db)
    print("\n" + "="*60)
    print("LOAD COMPLETE")
    print("="*60)
    print(f"Total forms in DB: {stats['total_forms']:,}")
    print(f"By corporación: {stats['by_corporacion']}")
    print(f"OCR completed: {stats['ocr_completed']:,}")
    print(f"OCR pending: {stats['ocr_pending']:,}")
    print("="*60)


if __name__ == "__main__":
    main()
