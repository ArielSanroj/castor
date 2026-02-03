#!/usr/bin/env python3
"""
Load Tesseract OCR results to PostgreSQL database.

Creates tables and loads the 486 E-14 extraction results for SQL queries.
"""
import json
import glob
import os
import sys
import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    "dbname": "castor_elecciones",
    "user": os.environ.get("PGUSER", ""),  # Uses default user
    "host": "localhost",
    "port": 5432,
}

# Paths
TESSERACT_DIR = os.path.expanduser("~/Downloads/Code/Proyectos/castor/output/tesseract_results")

# SQL for creating tables
CREATE_TABLES_SQL = """
-- E-14 Forms (mesas)
CREATE TABLE IF NOT EXISTS e14_forms (
    id SERIAL PRIMARY KEY,
    extraction_id VARCHAR(20) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    corporacion VARCHAR(20),
    departamento VARCHAR(100),
    municipio VARCHAR(100),
    zona VARCHAR(10),
    puesto VARCHAR(100),
    mesa VARCHAR(20),
    total_votos INTEGER DEFAULT 0,
    votos_blancos INTEGER DEFAULT 0,
    votos_nulos INTEGER DEFAULT 0,
    confidence FLOAT DEFAULT 0,
    processing_time_ms INTEGER,
    source VARCHAR(20) DEFAULT 'tesseract',
    created_at TIMESTAMP DEFAULT NOW()
);

-- E-14 Party Votes
CREATE TABLE IF NOT EXISTS e14_party_votes (
    id SERIAL PRIMARY KEY,
    form_id INTEGER REFERENCES e14_forms(id) ON DELETE CASCADE,
    party_name VARCHAR(200) NOT NULL,
    party_code VARCHAR(20),
    votes INTEGER DEFAULT 0,
    confidence FLOAT DEFAULT 0,
    needs_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_e14_forms_municipio ON e14_forms(municipio);
CREATE INDEX IF NOT EXISTS idx_e14_forms_corporacion ON e14_forms(corporacion);
CREATE INDEX IF NOT EXISTS idx_e14_forms_mesa ON e14_forms(mesa);
CREATE INDEX IF NOT EXISTS idx_e14_party_votes_form ON e14_party_votes(form_id);
CREATE INDEX IF NOT EXISTS idx_e14_party_votes_party ON e14_party_votes(party_name);

-- Aggregated view for quick queries
CREATE OR REPLACE VIEW e14_party_totals AS
SELECT
    party_name,
    SUM(votes) as total_votes,
    COUNT(DISTINCT form_id) as mesas_count,
    AVG(confidence) as avg_confidence,
    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) as needs_review_count
FROM e14_party_votes
GROUP BY party_name
ORDER BY total_votes DESC;

-- View by municipio
CREATE OR REPLACE VIEW e14_municipio_summary AS
SELECT
    f.municipio,
    f.departamento,
    COUNT(DISTINCT f.id) as total_mesas,
    SUM(f.total_votos) as total_votos,
    AVG(f.confidence) as avg_confidence
FROM e14_forms f
GROUP BY f.municipio, f.departamento
ORDER BY total_votos DESC;
"""


def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        # Try without user specified
        try:
            conn = psycopg2.connect(dbname=DB_CONFIG["dbname"], host=DB_CONFIG["host"])
            return conn
        except Exception as e2:
            logger.error(f"Database connection error (retry): {e2}")
            raise


def create_tables(conn):
    """Create database tables."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLES_SQL)
    conn.commit()
    logger.info("Tables created successfully")


def load_tesseract_files(conn):
    """Load all Tesseract JSON files to database."""
    pattern = os.path.join(TESSERACT_DIR, "*_tesseract.json")
    files = sorted(glob.glob(pattern))

    if not files:
        logger.error(f"No files found in {TESSERACT_DIR}")
        return 0

    logger.info(f"Found {len(files)} Tesseract files to load")

    forms_data = []
    votes_data = []
    form_id_map = {}

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            extraction_id = data.get('extraction_id', '')
            if not extraction_id:
                continue

            # Form data
            forms_data.append((
                extraction_id,
                data.get('filename', ''),
                data.get('corporacion', ''),
                data.get('departamento', ''),
                data.get('municipio', ''),
                data.get('zona', ''),
                data.get('puesto', ''),
                data.get('mesa', ''),
                data.get('total_votos', 0),
                data.get('votos_blancos', 0),
                data.get('votos_nulos', 0),
                data.get('confidence', 0),
                data.get('processing_time_ms', 0),
                'tesseract'
            ))

            # Party votes
            for partido in data.get('partidos', []):
                votes_data.append((
                    extraction_id,  # Will be replaced with form_id after insert
                    partido.get('party_name', ''),
                    partido.get('party_code', ''),
                    partido.get('votes', 0),
                    partido.get('confidence', 0),
                    partido.get('needs_review', False)
                ))

        except Exception as e:
            logger.warning(f"Error reading {filepath}: {e}")
            continue

    # Insert forms
    with conn.cursor() as cur:
        # Clear existing data
        cur.execute("TRUNCATE e14_party_votes, e14_forms RESTART IDENTITY CASCADE")

        # Insert forms
        insert_forms_sql = """
            INSERT INTO e14_forms
            (extraction_id, filename, corporacion, departamento, municipio,
             zona, puesto, mesa, total_votos, votos_blancos, votos_nulos,
             confidence, processing_time_ms, source)
            VALUES %s
            ON CONFLICT (extraction_id) DO NOTHING
            RETURNING id, extraction_id
        """
        execute_values(cur, insert_forms_sql, forms_data)

        # Get form IDs
        cur.execute("SELECT id, extraction_id FROM e14_forms")
        for row in cur.fetchall():
            form_id_map[row[1]] = row[0]

        # Prepare votes data with form_id
        votes_with_ids = []
        for v in votes_data:
            form_id = form_id_map.get(v[0])
            if form_id:
                votes_with_ids.append((form_id, v[1], v[2], v[3], v[4], v[5]))

        # Insert party votes
        insert_votes_sql = """
            INSERT INTO e14_party_votes
            (form_id, party_name, party_code, votes, confidence, needs_review)
            VALUES %s
        """
        execute_values(cur, insert_votes_sql, votes_with_ids)

    conn.commit()

    logger.info(f"Loaded {len(forms_data)} forms and {len(votes_with_ids)} party votes")
    return len(forms_data)


def show_summary(conn):
    """Show summary statistics."""
    with conn.cursor() as cur:
        # Total forms
        cur.execute("SELECT COUNT(*) FROM e14_forms")
        total_forms = cur.fetchone()[0]

        # Total votes
        cur.execute("SELECT SUM(votes) FROM e14_party_votes")
        total_votes = cur.fetchone()[0] or 0

        # Top parties
        cur.execute("""
            SELECT party_name, total_votes, mesas_count
            FROM e14_party_totals
            LIMIT 10
        """)
        top_parties = cur.fetchall()

        # By municipio
        cur.execute("""
            SELECT municipio, total_mesas, total_votos
            FROM e14_municipio_summary
            LIMIT 5
        """)
        top_municipios = cur.fetchall()

    print("\n" + "="*60)
    print("RESUMEN DE DATOS CARGADOS")
    print("="*60)
    print(f"Total mesas (forms): {total_forms}")
    print(f"Total votos: {total_votes:,}")

    print("\nTop 10 Partidos:")
    for party, votes, mesas in top_parties:
        print(f"  {party[:40]}: {votes:,} votos ({mesas} mesas)")

    print("\nTop 5 Municipios:")
    for muni, mesas, votos in top_municipios:
        print(f"  {muni}: {mesas} mesas, {votos:,} votos")

    print("="*60)


def main():
    logger.info("Starting database load...")

    conn = connect_db()
    try:
        create_tables(conn)
        count = load_tesseract_files(conn)
        if count > 0:
            show_summary(conn)
            print("\n✅ Datos cargados exitosamente a PostgreSQL")
            print("\nEjemplos de queries SQL:")
            print("  SELECT * FROM e14_party_totals;")
            print("  SELECT * FROM e14_municipio_summary;")
            print("  SELECT * FROM e14_forms WHERE municipio = 'MEDELLIN';")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
