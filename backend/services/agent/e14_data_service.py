"""
E-14 Data Service for the Electoral Intelligence Agent.
Fetches E-14 forms from the scraper database and converts them
to the format expected by the agent's analyzers.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterator

from services.qr_parser import parse_qr_barcode, QRParseStatus

logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")


class E14DataService:
    """
    Service to fetch E-14 data from the scraper database.
    Provides methods for batch processing and real-time polling.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        logger.info(f"E14DataService initialized with DB: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics of E-14 forms."""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}

        # Total forms
        cursor.execute("SELECT COUNT(*) FROM e14_scraper_forms")
        stats['total_forms'] = cursor.fetchone()[0]

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

        # By corporacion
        cursor.execute("""
            SELECT corporacion, COUNT(*)
            FROM e14_scraper_forms
            GROUP BY corporacion
        """)
        stats['by_corporacion'] = dict(cursor.fetchall())

        # By department
        cursor.execute("""
            SELECT departamento, COUNT(*) as cnt
            FROM e14_scraper_forms
            WHERE ocr_processed = 1
            GROUP BY departamento
            ORDER BY cnt DESC
            LIMIT 10
        """)
        stats['top_departamentos'] = [
            {'departamento': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]

        conn.close()
        return stats

    def get_forms_batch(
        self,
        offset: int = 0,
        limit: int = 1000,
        ocr_only: bool = True,
        departamento: Optional[str] = None,
        municipio: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a batch of E-14 forms for processing.

        Args:
            offset: Starting offset
            limit: Maximum forms to return
            ocr_only: Only return OCR-processed forms
            departamento: Filter by department
            municipio: Filter by municipality

        Returns:
            List of forms in agent-compatible format
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if ocr_only:
            where_clauses.append("f.ocr_processed = 1")

        if departamento:
            # Case-insensitive match
            where_clauses.append("UPPER(f.departamento) = UPPER(?)")
            params.append(departamento)

        if municipio:
            where_clauses.append("UPPER(f.municipio) = UPPER(?)")
            params.append(municipio)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            SELECT
                f.id, f.mesa_id, f.filename, f.corporacion, f.departamento,
                f.municipio, f.zona_cod, f.puesto_cod, f.mesa_num,
                f.ocr_processed, f.ocr_confidence, f.total_votos,
                f.votos_blancos, f.votos_nulos, f.created_at
            FROM e14_scraper_forms f
            {where_sql}
            ORDER BY f.id
            LIMIT ? OFFSET ?
        """
        logger.debug(f"Query: {query}, Params: {params + [limit, offset]}")
        cursor.execute(query, params + [limit, offset])

        forms = []
        for row in cursor.fetchall():
            form = self._convert_to_agent_format(dict(row), cursor)
            forms.append(form)

        conn.close()
        return forms

    def iterate_all_forms(
        self,
        batch_size: int = 500,
        ocr_only: bool = True
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Iterate through all forms in batches.

        Args:
            batch_size: Number of forms per batch
            ocr_only: Only return OCR-processed forms

        Yields:
            Batches of forms
        """
        offset = 0
        while True:
            batch = self.get_forms_batch(
                offset=offset,
                limit=batch_size,
                ocr_only=ocr_only
            )
            if not batch:
                break
            yield batch
            offset += batch_size

    def get_form_with_votes(self, form_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single form with all party votes.

        Args:
            form_id: Form ID

        Returns:
            Form data in agent-compatible format
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM e14_scraper_forms WHERE id = ?
        """, (form_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        form = self._convert_to_agent_format(dict(row), cursor)
        conn.close()
        return form

    def _convert_to_agent_format(
        self,
        row: Dict[str, Any],
        cursor: sqlite3.Cursor
    ) -> Dict[str, Any]:
        """
        Convert database row to agent-compatible format.

        The agent expects:
        - document_header_extracted
        - validations
        - ocr_fields
        """
        form_id = row['id']

        # Get party votes
        cursor.execute("""
            SELECT party_name, party_code, votes, confidence, needs_review
            FROM e14_scraper_votes
            WHERE form_id = ?
        """, (form_id,))
        votes = cursor.fetchall()

        # Build header
        header = {
            'mesa_id': row.get('mesa_id', ''),
            'dept_code': row.get('departamento', '00')[:2] if row.get('departamento') else '00',
            'muni_code': row.get('municipio', '000')[:3] if row.get('municipio') else '000',
            'zone_code': str(row.get('zona_cod', '00')),
            'station_code': str(row.get('puesto_cod', '00')),
            'table_number': row.get('mesa_num', 0) or 0,
            'corporacion': row.get('corporacion', ''),
            'departamento': row.get('departamento', ''),
            'municipio': row.get('municipio', ''),
        }

        # Enforce QR as primary key when possible (mesa_id often encodes QR)
        qr_raw = row.get('mesa_id') or ''
        if qr_raw:
            qr_data = parse_qr_barcode(qr_raw)
            if qr_data.parse_status in (QRParseStatus.SUCCESS, QRParseStatus.PARTIAL):
                header['dept_code'] = qr_data.dept_code or header['dept_code']
                header['muni_code'] = qr_data.muni_code or header['muni_code']
                header['zone_code'] = qr_data.zone_code or header['zone_code']
                header['station_code'] = qr_data.station_code or header['station_code']
                if qr_data.table_number is not None:
                    header['table_number'] = qr_data.table_number
                header['polling_table_id'] = qr_data.polling_table_id or header['mesa_id']

        # Build OCR fields from votes
        ocr_fields = []
        total_calculated = 0
        for vote in votes:
            vote_dict = dict(vote)
            ocr_fields.append({
                'field_key': f"CANDIDATE_VOTES_{vote_dict['party_code']}",
                'party_name': vote_dict['party_name'],
                'party_code': vote_dict['party_code'],
                'value_int': vote_dict['votes'] or 0,
                'confidence': vote_dict['confidence'] or 0.0,
                'needs_review': bool(vote_dict.get('needs_review', False)),
            })
            total_calculated += vote_dict['votes'] or 0

        # Add blancos and nulos
        votos_blancos = row.get('votos_blancos', 0) or 0
        votos_nulos = row.get('votos_nulos', 0) or 0
        total_votos = row.get('total_votos', 0) or 0

        ocr_fields.append({
            'field_key': 'VOTOS_BLANCOS',
            'value_int': votos_blancos,
            'confidence': row.get('ocr_confidence', 0.0) or 0.0,
        })
        ocr_fields.append({
            'field_key': 'VOTOS_NULOS',
            'value_int': votos_nulos,
            'confidence': row.get('ocr_confidence', 0.0) or 0.0,
        })
        ocr_fields.append({
            'field_key': 'TOTAL_VOTOS',
            'value_int': total_votos,
            'confidence': row.get('ocr_confidence', 0.0) or 0.0,
        })

        # Build validations - check arithmetic
        validations = []
        expected_total = total_calculated + votos_blancos + votos_nulos
        actual_total = total_votos

        if actual_total > 0 and expected_total != actual_total:
            validations.append({
                'rule_key': 'ARITHMETIC_SUM',
                'passed': False,
                'severity': 'CRITICAL' if abs(expected_total - actual_total) > 10 else 'HIGH',
                'details': {
                    'expected': expected_total,
                    'actual': actual_total,
                    'delta': abs(expected_total - actual_total),
                }
            })
        else:
            validations.append({
                'rule_key': 'ARITHMETIC_SUM',
                'passed': True,
                'severity': 'INFO',
            })

        # Check for low OCR confidence
        avg_confidence = row.get('ocr_confidence', 0.0) or 0.0
        if avg_confidence < 0.70:
            validations.append({
                'rule_key': 'OCR_CONFIDENCE',
                'passed': False,
                'severity': 'MEDIUM' if avg_confidence > 0.5 else 'HIGH',
                'details': {
                    'avg_confidence': avg_confidence,
                    'threshold': 0.70,
                }
            })

        return {
            'id': form_id,
            'extraction_id': f"e14_{form_id}",
            'mesa_id': row.get('mesa_id', ''),
            'document_header_extracted': header,
            'validations': validations,
            'ocr_fields': ocr_fields,
            'ocr_confidence': avg_confidence,
            'total_votos': total_votos,
            'votos_blancos': votos_blancos,
            'votos_nulos': votos_nulos,
            'source': 'e14_scraper_db',
            'created_at': row.get('created_at', datetime.utcnow().isoformat()),
        }

    def get_forms_by_municipio(self, municipio: str) -> List[Dict[str, Any]]:
        """Get all forms for a specific municipality."""
        return self.get_forms_batch(
            offset=0,
            limit=10000,
            ocr_only=True,
            municipio=municipio
        )

    def count_forms(self, ocr_only: bool = True) -> int:
        """Count total forms."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if ocr_only:
            cursor.execute("SELECT COUNT(*) FROM e14_scraper_forms WHERE ocr_processed = 1")
        else:
            cursor.execute("SELECT COUNT(*) FROM e14_scraper_forms")

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_unprocessed_forms(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get OCR-processed forms that the agent has not processed yet.
        """
        from services.agent.agent_store import init_db
        init_db()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT f.*
            FROM e14_scraper_forms f
            LEFT JOIN agent_e14_processed p ON p.form_id = f.id
            WHERE f.ocr_processed = 1 AND p.form_id IS NULL
            ORDER BY f.id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        forms = [self._convert_to_agent_format(dict(row), cursor) for row in rows]
        conn.close()
        return forms
