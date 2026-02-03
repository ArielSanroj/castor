"""
E-14 Data API Routes.

Provides access to E-14 forms loaded from the scraper.
Used by the dashboard to display electoral data.
"""
import sqlite3
from flask import Blueprint, jsonify, request, current_app
import os

e14_data_bp = Blueprint('e14_data', __name__, url_prefix='/api/e14-data')

DB_PATH = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


@e14_data_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get overall statistics of loaded E-14 forms.

    Returns:
        - total_forms: Total number of forms
        - by_corporacion: Count by SEN/CAM
        - ocr_completed: Forms with OCR done
        - ocr_pending: Forms pending OCR
        - top_departamentos: Top 10 departments by form count
    """
    conn = get_db()
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
    stats['ocr_progress'] = round((stats['ocr_completed'] / max(stats['total_forms'], 1)) * 100, 1)

    # Top departamentos
    cursor.execute("""
        SELECT departamento, COUNT(*) as cnt
        FROM e14_scraper_forms
        GROUP BY departamento
        ORDER BY cnt DESC
        LIMIT 10
    """)
    stats['top_departamentos'] = [
        {'departamento': row[0], 'count': row[1]}
        for row in cursor.fetchall()
    ]

    # Total votes (from OCR)
    cursor.execute("""
        SELECT SUM(total_votos), SUM(votos_blancos), SUM(votos_nulos)
        FROM e14_scraper_forms
        WHERE ocr_processed = 1
    """)
    row = cursor.fetchone()
    stats['total_votos'] = row[0] or 0
    stats['votos_blancos'] = row[1] or 0
    stats['votos_nulos'] = row[2] or 0

    conn.close()
    return jsonify(stats)


@e14_data_bp.route('/forms', methods=['GET'])
def get_forms():
    """
    Get paginated list of E-14 forms.

    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
        - corporacion: Filter by SEN or CAM
        - departamento: Filter by department
        - municipio: Filter by municipality
        - ocr_only: Only return OCR processed forms
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    corporacion = request.args.get('corporacion')
    departamento = request.args.get('departamento')
    municipio = request.args.get('municipio')
    ocr_only = request.args.get('ocr_only', 'false').lower() == 'true'

    conn = get_db()
    cursor = conn.cursor()

    # Build query
    where_clauses = []
    params = []

    if corporacion:
        where_clauses.append("corporacion = ?")
        params.append(corporacion)

    if departamento:
        where_clauses.append("departamento = ?")
        params.append(departamento)

    if municipio:
        where_clauses.append("municipio = ?")
        params.append(municipio)

    if ocr_only:
        where_clauses.append("ocr_processed = 1")

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM e14_scraper_forms {where_sql}", params)
    total = cursor.fetchone()[0]

    # Get page
    offset = (page - 1) * per_page
    cursor.execute(f"""
        SELECT
            id, mesa_id, filename, corporacion, departamento, municipio,
            zona_cod, puesto_cod, mesa_num, ocr_processed, ocr_confidence,
            total_votos, votos_blancos, votos_nulos
        FROM e14_scraper_forms
        {where_sql}
        ORDER BY departamento, municipio, mesa_id
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    forms = []
    for row in cursor.fetchall():
        forms.append({
            'id': row[0],
            'mesa_id': row[1],
            'filename': row[2],
            'corporacion': row[3],
            'departamento': row[4],
            'municipio': row[5],
            'zona_cod': row[6],
            'puesto_cod': row[7],
            'mesa_num': row[8],
            'ocr_processed': bool(row[9]),
            'ocr_confidence': row[10],
            'total_votos': row[11],
            'votos_blancos': row[12],
            'votos_nulos': row[13],
        })

    conn.close()

    return jsonify({
        'forms': forms,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    })


@e14_data_bp.route('/departamentos', methods=['GET'])
def get_departamentos():
    """Get list of departments with form counts."""
    conn = get_db()
    cursor = conn.cursor()

    corporacion = request.args.get('corporacion')

    if corporacion:
        cursor.execute("""
            SELECT departamento, COUNT(*) as cnt,
                   SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as ocr_done
            FROM e14_scraper_forms
            WHERE corporacion = ?
            GROUP BY departamento
            ORDER BY cnt DESC
        """, (corporacion,))
    else:
        cursor.execute("""
            SELECT departamento, COUNT(*) as cnt,
                   SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as ocr_done
            FROM e14_scraper_forms
            GROUP BY departamento
            ORDER BY cnt DESC
        """)

    results = [
        {'departamento': row[0], 'total_mesas': row[1], 'ocr_completed': row[2]}
        for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(results)


@e14_data_bp.route('/municipios/<departamento>', methods=['GET'])
def get_municipios(departamento):
    """Get list of municipalities for a department."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT municipio, COUNT(*) as cnt,
               SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as ocr_done,
               SUM(total_votos) as votos
        FROM e14_scraper_forms
        WHERE departamento = ?
        GROUP BY municipio
        ORDER BY cnt DESC
    """, (departamento,))

    results = [
        {
            'municipio': row[0],
            'total_mesas': row[1],
            'ocr_completed': row[2],
            'total_votos': row[3] or 0
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(results)


@e14_data_bp.route('/party-totals', methods=['GET'])
def get_party_totals():
    """Get vote totals by party from OCR results."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT party_name, SUM(votes) as total_votes,
               COUNT(DISTINCT form_id) as mesas_count,
               AVG(confidence) as avg_confidence
        FROM e14_scraper_votes
        GROUP BY party_name
        ORDER BY total_votes DESC
        LIMIT 30
    """)

    results = [
        {
            'party_name': row[0],
            'total_votes': row[1],
            'mesas_count': row[2],
            'avg_confidence': round(row[3] or 0, 2)
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(results)


@e14_data_bp.route('/form/<int:form_id>', methods=['GET'])
def get_form_detail(form_id):
    """Get detailed form data including party votes."""
    conn = get_db()
    cursor = conn.cursor()

    # Get form
    cursor.execute("""
        SELECT * FROM e14_scraper_forms WHERE id = ?
    """, (form_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Form not found'}), 404

    columns = [desc[0] for desc in cursor.description]
    form = dict(zip(columns, row))

    # Get party votes
    cursor.execute("""
        SELECT party_name, party_code, votes, confidence, needs_review
        FROM e14_scraper_votes
        WHERE form_id = ?
        ORDER BY votes DESC
    """, (form_id,))

    form['partidos'] = [
        {
            'party_name': row[0],
            'party_code': row[1],
            'votes': row[2],
            'confidence': row[3],
            'needs_review': bool(row[4])
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(form)


@e14_data_bp.route('/summary/by-dept', methods=['GET'])
def get_summary_by_dept():
    """Get summary grouped by department."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            departamento,
            corporacion,
            COUNT(*) as total_mesas,
            SUM(CASE WHEN ocr_processed = 1 THEN 1 ELSE 0 END) as ocr_done,
            SUM(total_votos) as total_votos,
            AVG(ocr_confidence) as avg_confidence
        FROM e14_scraper_forms
        GROUP BY departamento, corporacion
        ORDER BY total_mesas DESC
    """)

    results = [
        {
            'departamento': row[0],
            'corporacion': row[1],
            'total_mesas': row[2],
            'ocr_completed': row[3],
            'ocr_pending': row[2] - row[3],
            'total_votos': row[4] or 0,
            'avg_confidence': round(row[5] or 0, 2)
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return jsonify(results)
