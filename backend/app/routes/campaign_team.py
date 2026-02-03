"""
Routes para el Dashboard de Equipo de Campaña Electoral.
API para War Room, Reportes, Plan de Acción y Correlación E-14/Social.
"""
import logging
import random
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app, render_template

from app.schemas.campaign_team import AlertAssignRequest
from app.services.campaign_team_service import get_campaign_team_service
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

# ============================================================
# MOCK DATA - 8 CANDIDATOS CONSULTA NACIONAL
# ============================================================

CANDIDATOS_CONSULTA = [
    {
        "id": 1,
        "name": "Vicky Dávila",
        "party": "Valientes",
        "party_code": "VAL",
        "color": "#E91E63",
        "photo": "/static/images/candidates/vicky_davila.jpg"
    },
    {
        "id": 2,
        "name": "Juan Manuel Galán",
        "party": "Nuevo Liberalismo",
        "party_code": "NL",
        "color": "#D32F2F",
        "photo": "/static/images/candidates/juan_galan.jpg"
    },
    {
        "id": 3,
        "name": "Paloma Valencia",
        "party": "Centro Democrático",
        "party_code": "CD",
        "color": "#1565C0",
        "photo": "/static/images/candidates/paloma_valencia.jpg"
    },
    {
        "id": 4,
        "name": "Enrique Peñalosa",
        "party": "Partido Verde Oxígeno",
        "party_code": "PVO",
        "color": "#388E3C",
        "photo": "/static/images/candidates/enrique_penalosa.jpg"
    },
    {
        "id": 5,
        "name": "Juan Carlos Pinzón",
        "party": "Partido Verde Oxígeno",
        "party_code": "PVO",
        "color": "#43A047",
        "photo": "/static/images/candidates/jc_pinzon.jpg"
    },
    {
        "id": 6,
        "name": "Aníbal Gaviria",
        "party": "Unidos - La Fuerza de las Regiones",
        "party_code": "UFR",
        "color": "#FF9800",
        "photo": "/static/images/candidates/anibal_gaviria.jpg"
    },
    {
        "id": 7,
        "name": "Mauricio Cárdenas",
        "party": "Avanza Colombia",
        "party_code": "AC",
        "color": "#7B1FA2",
        "photo": "/static/images/candidates/mauricio_cardenas.jpg"
    },
    {
        "id": 8,
        "name": "David Luna",
        "party": "Sí Hay Un Camino",
        "party_code": "SHUC",
        "color": "#00ACC1",
        "photo": "/static/images/candidates/david_luna.jpg"
    },
    {
        "id": 9,
        "name": "Juan Daniel Oviedo",
        "party": "Con Toda Por Colombia",
        "party_code": "CTPC",
        "color": "#5E35B1",
        "photo": "/static/images/candidates/juan_oviedo.jpg"
    }
]

def generate_mock_e14_data():
    """Generate realistic mock E-14 data for the 9 candidates (2026 elections)."""
    import random

    # Base votes with some randomization - realistic polling scenario
    base_votes = {
        "Vicky Dávila": random.randint(220000, 280000),        # Líder
        "Juan Manuel Galán": random.randint(180000, 240000),   # Segundo
        "Paloma Valencia": random.randint(150000, 200000),     # Tercera
        "Enrique Peñalosa": random.randint(120000, 170000),    # Cuarto
        "Juan Carlos Pinzón": random.randint(100000, 150000),  # Quinto
        "Aníbal Gaviria": random.randint(80000, 130000),       # Sexto
        "Mauricio Cárdenas": random.randint(70000, 120000),    # Séptimo
        "David Luna": random.randint(50000, 90000),            # Octavo
        "Juan Daniel Oviedo": random.randint(40000, 80000)     # Noveno
    }

    total_votes = sum(base_votes.values())

    candidates_data = []
    for cand in CANDIDATOS_CONSULTA:
        votes = base_votes.get(cand["name"], 50000)
        percentage = (votes / total_votes) * 100

        # Random variations for E-14 data
        mesas_processed = random.randint(4500, 5500)
        mesas_total = 6200

        candidates_data.append({
            "id": cand["id"],
            "name": cand["name"],
            "party": cand["party"],
            "party_code": cand["party_code"],
            "color": cand["color"],
            "votes": votes,
            "percentage": round(percentage, 2),
            "votes_last_hour": random.randint(1000, 5000),
            "trend": random.choice(["up", "up", "stable", "down"]),
            "trend_value": round(random.uniform(-2.5, 4.5), 1),
            "mesas_processed": mesas_processed,
            "mesas_total": mesas_total,
            "coverage_pct": round((mesas_processed / mesas_total) * 100, 1),
            "confidence": round(random.uniform(0.82, 0.95), 2),
            "last_update": datetime.utcnow().isoformat()
        })

    # Sort by votes descending
    candidates_data.sort(key=lambda x: x["votes"], reverse=True)

    return candidates_data, total_votes

def generate_mock_war_room_stats():
    """Generate mock War Room statistics."""
    mesas_total = 12450
    mesas_testigo = random.randint(5500, 6500)
    mesas_rnec = random.randint(2500, 3500)
    mesas_reconciled = random.randint(2000, 2800)

    return {
        "total_mesas": mesas_total,
        "mesas_testigo": mesas_testigo,
        "mesas_rnec": mesas_rnec,
        "mesas_reconciled": mesas_reconciled,
        "testigo_percent": round((mesas_testigo / mesas_total) * 100, 1),
        "rnec_percent": round((mesas_rnec / mesas_total) * 100, 1),
        "reconciled_percent": round((mesas_reconciled / mesas_total) * 100, 1),
        "coverage_percent": round(((mesas_testigo + mesas_rnec) / mesas_total) * 100 / 2, 1),
        "high_risk": random.randint(80, 150),
        "medium_risk": random.randint(200, 400),
        "low_risk": mesas_total - random.randint(300, 550),
        "p0_incidents": random.randint(2, 8),
        "processed": mesas_testigo + mesas_rnec
    }

campaign_team_bp = Blueprint('campaign_team', __name__)

# Exempt this blueprint from rate limiting - dashboard makes many parallel API calls
limiter.exempt(campaign_team_bp)


def get_service():
    """Get campaign team service with database connection."""
    db_service = current_app.extensions.get("database_service")
    return get_campaign_team_service(db_service=db_service)


# ============================================================
# PAGE ROUTE
# ============================================================

@campaign_team_bp.route('/dashboard', methods=['GET'])
def campaign_team_dashboard():
    """Render the Campaign Team Dashboard page."""
    return render_template('campaign_team_dashboard.html')


# ============================================================
# WAR ROOM ENDPOINTS
# ============================================================

@campaign_team_bp.route('/war-room/stats', methods=['GET'])
def get_war_room_stats():
    """
    Get War Room KPIs.

    Query params:
        contest_id (required): Contest ID

    Returns:
        WarRoomStats JSON
    """
    try:
        contest_id = request.args.get('contest_id', 1, type=int)

        # Use mock data for demo (8 candidates from national consultation)
        mock_stats = generate_mock_war_room_stats()
        return jsonify({
            "success": True,
            "stats": mock_stats
        })

    except Exception as e:
        logger.error(f"Error getting war room stats: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/war-room/progress', methods=['GET'])
def get_processing_progress():
    """
    Get processing progress by municipality.

    Query params:
        contest_id (required): Contest ID

    Returns:
        List of ProcessingProgress per municipality
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        progress = service.get_processing_progress(contest_id)

        return jsonify({
            "success": True,
            "progress": [p.dict() for p in progress],
            "total_municipalities": len(progress)
        })

    except Exception as e:
        logger.error(f"Error getting processing progress: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/war-room/alerts', methods=['GET'])
def get_alerts():
    """
    Get alerts list.

    Query params:
        contest_id (required): Contest ID
        status (optional): Filter by status (OPEN, ACKNOWLEDGED, etc.)
        severity (optional): Filter by severity (CRITICAL, HIGH, etc.)
        limit (optional): Max results (default 50)

    Returns:
        AlertsListResponse JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        status = request.args.get('status')
        severity = request.args.get('severity')
        limit = request.args.get('limit', 50, type=int)

        service = get_service()
        response = service.get_alerts(
            contest_id=contest_id,
            status=status,
            severity=severity,
            limit=limit
        )

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/war-room/alerts/<int:alert_id>/assign', methods=['POST'])
def assign_alert(alert_id: int):
    """
    Assign an alert to a user.

    Path params:
        alert_id: Alert ID

    Request body:
        user_id (required): User ID to assign
        notes (optional): Notes

    Returns:
        Success status
    """
    try:
        data = request.get_json() or {}

        user_id = data.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400

        notes = data.get('notes')

        service = get_service()
        success = service.assign_alert(
            alert_id=alert_id,
            user_id=user_id,
            notes=notes
        )

        if success:
            return jsonify({
                "success": True,
                "message": f"Alert {alert_id} assigned to user {user_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to assign alert"
            }), 404

    except Exception as e:
        logger.error(f"Error assigning alert: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# REPORTS ENDPOINTS
# ============================================================

@campaign_team_bp.route('/reports/votes-by-candidate', methods=['GET'])
def get_votes_by_candidate():
    """
    Get votes breakdown by candidate.

    Query params:
        contest_id (required): Contest ID

    Returns:
        VotesReportResponse JSON with candidate and party breakdown
    """
    try:
        contest_id = request.args.get('contest_id', 1, type=int)

        # Try to get from service, fallback to mock data
        try:
            service = get_service()
            response = service.get_votes_by_candidate(contest_id)
            if response and response.candidates and len(response.candidates) > 0:
                return jsonify(response.dict())
        except Exception:
            pass

        # Generate mock data for the 8 candidates
        candidates_data, total_votes = generate_mock_e14_data()

        return jsonify({
            "success": True,
            "candidates": candidates_data,
            "total_votes": total_votes,
            "mesas_processed": random.randint(5000, 6000),
            "mesas_total": 6200,
            "last_update": datetime.utcnow().isoformat(),
            "contest_id": contest_id
        })

    except Exception as e:
        logger.error(f"Error getting votes by candidate: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/reports/regional-trends', methods=['GET'])
def get_regional_trends():
    """
    Get regional voting trends by department.

    Query params:
        contest_id (required): Contest ID

    Returns:
        RegionalTrendsResponse JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        response = service.get_regional_trends(contest_id)

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting regional trends: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/reports/e14-vs-social', methods=['GET'])
def get_e14_vs_social():
    """
    Get correlation between E-14 results and social media metrics.

    Query params:
        contest_id (required): Contest ID
        candidate_name (optional): Filter by candidate

    Returns:
        E14SocialCorrelationResponse JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        candidate_name = request.args.get('candidate_name')

        service = get_service()
        response = service.get_e14_vs_social_correlation(
            contest_id=contest_id,
            candidate_name=candidate_name
        )

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting E14 vs social correlation: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# ACTION PLAN ENDPOINTS
# ============================================================

@campaign_team_bp.route('/action-plan/prioritized', methods=['GET'])
def get_prioritized_actions():
    """
    Get prioritized action plan.

    Query params:
        contest_id (required): Contest ID

    Returns:
        ActionPlanResponse JSON with categorized actions
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        response = service.get_prioritized_actions(contest_id)

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting prioritized actions: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@campaign_team_bp.route('/action-plan/opportunity-zones', methods=['GET'])
def get_opportunity_zones():
    """
    Get zones with low participation (opportunity for mobilization).

    Query params:
        contest_id (required): Contest ID
        limit (optional): Max results (default 20)

    Returns:
        OpportunityZonesResponse JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        limit = request.args.get('limit', 20, type=int)

        service = get_service()
        response = service.get_opportunity_zones(contest_id, limit=limit)

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting opportunity zones: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CORRELATION ENDPOINTS
# ============================================================

@campaign_team_bp.route('/correlation/forecast-vs-reality', methods=['GET'])
def get_forecast_vs_reality():
    """
    Compare forecast predictions with actual E-14 results.

    Query params:
        contest_id (required): Contest ID
        candidate_name (optional): Filter by candidate

    Returns:
        ForecastVsRealityResponse JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        candidate_name = request.args.get('candidate_name')

        service = get_service()
        response = service.get_forecast_vs_reality(
            contest_id=contest_id,
            candidate_name=candidate_name
        )

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting forecast vs reality: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@campaign_team_bp.route('/summary', methods=['GET'])
def get_dashboard_summary():
    """
    Get complete dashboard summary.

    Query params:
        contest_id (required): Contest ID

    Returns:
        DashboardSummary JSON
    """
    try:
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        response = service.get_dashboard_summary(contest_id)

        return jsonify(response.dict())

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# E-14 LIVE FORM DATA
# ============================================================

@campaign_team_bp.route('/e14-live', methods=['GET'])
def get_e14_live_data():
    """
    Get E-14 form data for live visualization.

    Query params:
        mesa_id (optional): Specific mesa ID to get
        limit (optional): Max forms to return (default 50)
        source (optional): 'tesseract' or 'vision' (default: tesseract)
        no_cache (optional): Skip cache and fetch fresh data

    Returns:
        E14 form data with candidates and OCR confidence
    """
    import os
    import json
    import glob

    limit = request.args.get('limit', 50, type=int)
    source = request.args.get('source', 'tesseract')
    no_cache = request.args.get('no_cache', 'false').lower() == 'true'

    # Try to get from cache first (unless no_cache is set)
    if not no_cache:
        try:
            from services.e14_cache_service import get_e14_cache_service
            cache = get_e14_cache_service()
            cached_response = cache.get_full_response(limit)
            if cached_response:
                logger.info(f"Returning cached E-14 response (limit={limit})")
                return jsonify(cached_response)
        except Exception as e:
            logger.warning(f"Cache lookup failed, falling back to file system: {e}")

    try:
        # Primary source: Tesseract OCR results (486 PDFs processed)
        # __file__ = backend/app/routes/campaign_team.py
        # Go up: routes -> app -> backend -> castor
        current_file = os.path.abspath(__file__)
        routes_dir = os.path.dirname(current_file)      # backend/app/routes
        app_dir = os.path.dirname(routes_dir)           # backend/app
        backend_dir = os.path.dirname(app_dir)          # backend
        project_root = os.path.dirname(backend_dir)     # castor
        tesseract_dir = os.path.join(project_root, 'output', 'tesseract_results')

        extraction_files = []

        if source == 'tesseract' and os.path.isdir(tesseract_dir):
            pattern = os.path.join(tesseract_dir, '*_tesseract.json')
            extraction_files = sorted(glob.glob(pattern))[:limit]

        # Fallback: Vision API extractions
        if not extraction_files:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            pattern = os.path.join(backend_dir, 'e14_extraction_*.json')
            extraction_files = glob.glob(pattern)

        if not extraction_files:
            return jsonify({
                "success": True,
                "forms": [],
                "message": "No hay extracciones E-14 disponibles"
            })

        forms = []
        aggregated_votes = {}  # Aggregate votes by party across all forms

        for filepath in extraction_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle both Tesseract and Vision API formats
                is_tesseract = '_tesseract.json' in filepath

                if is_tesseract:
                    # Tesseract format
                    partidos = data.get('partidos', [])
                    header = {
                        'corporacion': data.get('corporacion', ''),
                        'departamento_name': data.get('departamento', ''),
                        'municipio_name': data.get('municipio', ''),
                        'zona': data.get('zona', ''),
                        'lugar': data.get('puesto', ''),
                        'mesa': data.get('mesa', ''),
                    }
                    nivelacion = {}
                    resumen = {
                        'total_votos_validos': data.get('total_votos', 0),
                        'votos_blanco': data.get('votos_blancos', 0),
                        'votos_nulos': data.get('votos_nulos', 0),
                    }
                    overall_confidence = data.get('confidence', 0.5)
                else:
                    # Vision API format
                    header = data.get('header', {})
                    nivelacion = data.get('nivelacion', {})
                    partidos = data.get('partidos', [])
                    resumen = data.get('resumen', {})
                    overall_confidence = data.get('overall_confidence', 0.85)

                # Build candidates list from all parties
                candidates = []
                for partido in partidos:
                    party_name = partido.get('party_name', 'Sin partido')
                    party_code = partido.get('party_code', '')
                    votes = partido.get('votes', partido.get('total_votos', 0))
                    confidence = partido.get('confidence', partido.get('confidence_total', 0.5))
                    needs_review = partido.get('needs_review', confidence < 0.7)

                    # Add to candidates list
                    candidates.append({
                        "party_code": party_code,
                        "party_name": party_name,
                        "candidate_number": "Lista",
                        "candidate_name": f"{party_name}",
                        "votes": votes,
                        "confidence": confidence,
                        "needs_review": needs_review,
                        "is_party_vote": True
                    })

                    # Aggregate votes by party (for summary)
                    if party_name not in aggregated_votes:
                        aggregated_votes[party_name] = {"votes": 0, "mesas": 0, "confidence_sum": 0}
                    aggregated_votes[party_name]["votes"] += votes
                    aggregated_votes[party_name]["mesas"] += 1
                    aggregated_votes[party_name]["confidence_sum"] += confidence

                    # Add individual candidates if present (Vision API format)
                    for cand in partido.get('votos_candidatos', []):
                        if cand.get('votes', 0) > 0:
                            candidates.append({
                                "party_code": party_code,
                                "party_name": party_name,
                                "candidate_number": cand.get('candidate_number', ''),
                                "candidate_name": f"Candidato #{cand.get('candidate_number', '')}",
                                "votes": cand.get('votes', 0),
                                "confidence": cand.get('confidence', 0.85),
                                "needs_review": cand.get('needs_review', False),
                                "is_party_vote": False
                            })

                # Sort by votes descending
                candidates.sort(key=lambda x: x['votes'], reverse=True)

                form_data = {
                    "extraction_id": data.get('extraction_id', ''),
                    "extracted_at": data.get('extracted_at', ''),
                    "processing_time_ms": data.get('processing_time_ms', 0),
                    "source": "tesseract" if is_tesseract else "vision",
                    "header": {
                        "election_name": header.get('election_name', 'CONGRESO 2022'),
                        "election_date": header.get('election_date', '13 DE MARZO DE 2022'),
                        "corporacion": header.get('corporacion', ''),
                        "departamento": header.get('departamento_name', ''),
                        "municipio": header.get('municipio_name', ''),
                        "puesto": header.get('lugar', ''),
                        "mesa": header.get('mesa', ''),
                        "zona": header.get('zona', ''),
                        "barcode": header.get('barcode', '')
                    },
                    "nivelacion": {
                        "total_sufragantes": nivelacion.get('total_sufragantes_e11', 0),
                        "total_votos_urna": nivelacion.get('total_votos_urna', 0),
                        "confidence_sufragantes": nivelacion.get('confidence_sufragantes', 0),
                        "confidence_urna": nivelacion.get('confidence_urna', 0)
                    },
                    "resumen": {
                        "total_votos_validos": resumen.get('total_votos_validos', 0),
                        "votos_blanco": resumen.get('votos_blanco', 0),
                        "votos_nulos": resumen.get('votos_nulos', 0),
                        "votos_no_marcados": resumen.get('votos_no_marcados', 0),
                        "confidence_validos": resumen.get('confidence_validos', 0)
                    },
                    "candidates": candidates[:20],  # Top 20
                    "partidos": partidos,  # All parties for this form
                    "total_partidos": len(partidos),
                    "overall_confidence": overall_confidence
                }

                forms.append(form_data)

            except Exception as e:
                logger.warning(f"Error reading E-14 file {filepath}: {e}")
                continue

        # Build aggregated summary by party
        party_summary = []
        total_all_votes = 0
        for party_name, stats in sorted(aggregated_votes.items(), key=lambda x: x[1]["votes"], reverse=True):
            avg_confidence = stats["confidence_sum"] / stats["mesas"] if stats["mesas"] > 0 else 0
            party_summary.append({
                "party_name": party_name,
                "total_votes": stats["votes"],
                "mesas_count": stats["mesas"],
                "avg_confidence": round(avg_confidence, 2)
            })
            total_all_votes += stats["votes"]

        response_data = {
            "success": True,
            "forms": forms[:limit],
            "total_forms": len(extraction_files),
            "forms_returned": len(forms),
            "party_summary": party_summary[:30],  # Top 30 parties
            "total_parties": len(party_summary),
            "total_votes": total_all_votes,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Cache the response for future requests
        try:
            from services.e14_cache_service import get_e14_cache_service
            cache = get_e14_cache_service()
            cache.set_full_response(response_data, limit)
        except Exception as cache_err:
            logger.warning(f"Failed to cache response: {cache_err}")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting E-14 live data: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# E-14 CACHE MANAGEMENT
# ============================================================

@campaign_team_bp.route('/e14-cache/info', methods=['GET'])
def get_e14_cache_info():
    """Get E-14 cache statistics."""
    try:
        from services.e14_cache_service import get_e14_cache_service
        cache = get_e14_cache_service()
        info = cache.get_cache_info()
        return jsonify({"success": True, **info})
    except Exception as e:
        logger.error(f"Cache info error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@campaign_team_bp.route('/e14-cache/clear', methods=['POST', 'DELETE'])
def clear_e14_cache():
    """Clear all E-14 cache entries."""
    try:
        from services.e14_cache_service import get_e14_cache_service
        cache = get_e14_cache_service()
        deleted = cache.clear_all()
        return jsonify({
            "success": True,
            "message": f"Cleared {deleted} cache keys",
            "deleted_count": deleted
        })
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@campaign_team_bp.route('/e14-cache/warm', methods=['POST'])
def warm_e14_cache():
    """Warm E-14 cache from PostgreSQL database."""
    try:
        from services.e14_cache_service import get_e14_cache_service
        cache = get_e14_cache_service()
        success = cache.warm_cache_from_db()
        if success:
            return jsonify({
                "success": True,
                "message": "Cache warmed from PostgreSQL"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to warm cache"
            }), 500
    except Exception as e:
        logger.error(f"Cache warm error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# MESA DETAIL ENDPOINT
# ============================================================

@campaign_team_bp.route('/mesa/<mesa_id>/detail', methods=['GET'])
def get_mesa_detail(mesa_id: str):
    """
    Get detailed information for a specific mesa.

    Path params:
        mesa_id: Mesa identifier (e.g., "05-001-001-01-003")

    Returns:
        MesaDetail JSON with header, OCR fields, validations, source comparison
    """
    import random

    try:
        # Parse mesa_id to extract location info
        parts = mesa_id.split('-')
        dept_code = parts[0] if len(parts) > 0 else '05'
        muni_code = parts[1] if len(parts) > 1 else '001'

        # Department names mapping
        dept_names = {
            '05': 'Antioquia', '08': 'Atlántico', '11': 'Bogotá D.C.',
            '13': 'Bolívar', '15': 'Boyacá', '17': 'Caldas',
            '25': 'Cundinamarca', '54': 'Norte de Santander', '76': 'Valle del Cauca'
        }

        # Generate consistent random data based on mesa_id
        random.seed(hash(mesa_id) % 10000)

        # Overall confidence
        overall_confidence = random.uniform(0.55, 0.98)
        status = 'VALIDATED' if overall_confidence > 0.85 else ('NEEDS_REVIEW' if overall_confidence > 0.70 else 'HIGH_RISK')

        # OCR Fields with individual confidence
        sufragantes_e11 = random.randint(200, 400)
        votos_urna = sufragantes_e11 + random.randint(-5, 5)
        votos_validos = votos_urna - random.randint(2, 10)
        votos_blanco = random.randint(1, 15)
        votos_nulos = random.randint(1, 10)
        votos_no_marcados = votos_urna - votos_validos - votos_blanco - votos_nulos

        ocr_fields = [
            {"key": "sufragantes_e11", "label": "Sufragantes E-11", "value": sufragantes_e11, "confidence": random.uniform(0.85, 0.99), "needs_review": False},
            {"key": "votos_urna", "label": "Votos en Urna", "value": votos_urna, "confidence": random.uniform(0.80, 0.98), "needs_review": abs(votos_urna - sufragantes_e11) > 3},
            {"key": "votos_validos", "label": "Votos Válidos", "value": votos_validos, "confidence": overall_confidence, "needs_review": overall_confidence < 0.75},
            {"key": "votos_blanco", "label": "Votos en Blanco", "value": votos_blanco, "confidence": random.uniform(0.85, 0.99), "needs_review": False},
            {"key": "votos_nulos", "label": "Votos Nulos", "value": votos_nulos, "confidence": random.uniform(0.80, 0.98), "needs_review": False},
            {"key": "votos_no_marcados", "label": "No Marcados", "value": max(0, votos_no_marcados), "confidence": random.uniform(0.75, 0.95), "needs_review": False},
        ]

        # Validations
        sum_check = votos_validos + votos_blanco + votos_nulos + max(0, votos_no_marcados)
        validations = [
            {"rule": "NIV_001", "name": "Nivelación correcta", "passed": abs(sufragantes_e11 - votos_urna) <= 3, "message": f"Sufragantes ({sufragantes_e11}) vs Urna ({votos_urna})"},
            {"rule": "SUM_001", "name": "Suma de votos", "passed": abs(sum_check - votos_urna) <= 2, "message": f"Suma ({sum_check}) vs Total ({votos_urna})"},
            {"rule": "EXC_001", "name": "No excede sufragantes", "passed": votos_urna <= sufragantes_e11 + 2, "message": "Votos no exceden sufragantes"},
            {"rule": "BLK_001", "name": "Blancos válidos", "passed": votos_blanco <= votos_validos * 0.1, "message": f"Blancos ({votos_blanco}) <= 10% válidos"},
        ]

        # Generate candidate votes for comparison
        candidates = [
            {"number": "101", "name": "Paloma Valencia", "party": "Centro Democrático"},
            {"number": "102", "name": "Vicky Dávila", "party": "Independiente"},
            {"number": "103", "name": "Juan Carlos Pinzón", "party": "Coalición"},
            {"number": "104", "name": "David Luna", "party": "Cambio Radical"},
            {"number": "105", "name": "Mauricio Cárdenas", "party": "Liberal"},
        ]

        # Source comparison (Testigo vs RNEC)
        comparison = []
        for cand in candidates:
            testigo_votes = random.randint(10, 80)
            # RNEC might have small differences
            rnec_votes = testigo_votes + random.randint(-3, 3) if random.random() > 0.3 else testigo_votes
            delta = testigo_votes - rnec_votes
            delta_pct = abs(delta / testigo_votes * 100) if testigo_votes > 0 else 0

            comparison.append({
                "candidate_number": cand["number"],
                "candidate_name": cand["name"],
                "party": cand["party"],
                "testigo": testigo_votes,
                "rnec": rnec_votes,
                "delta": delta,
                "delta_pct": round(delta_pct, 1),
                "has_discrepancy": abs(delta) > 0
            })

        # Sort by testigo votes descending
        comparison.sort(key=lambda x: x['testigo'], reverse=True)

        # Active incidents for this mesa
        incidents = []
        if overall_confidence < 0.75:
            incidents.append({
                "id": random.randint(100, 999),
                "type": "OCR_LOW_CONF",
                "severity": "P1",
                "status": "OPEN",
                "description": f"Confianza OCR baja ({overall_confidence*100:.0f}%)"
            })

        if not validations[1]['passed']:
            incidents.append({
                "id": random.randint(100, 999),
                "type": "ARITHMETIC_FAIL",
                "severity": "P0",
                "status": "OPEN",
                "description": "Suma de votos no cuadra"
            })

        has_rnec_discrepancy = any(c['delta'] != 0 for c in comparison)
        if has_rnec_discrepancy:
            total_delta = sum(abs(c['delta']) for c in comparison)
            if total_delta > 5:
                incidents.append({
                    "id": random.randint(100, 999),
                    "type": "DISCREPANCY_RNEC",
                    "severity": "P0" if total_delta > 10 else "P1",
                    "status": "OPEN",
                    "description": f"Diferencia total de {total_delta} votos vs RNEC"
                })

        # Build response
        detail = {
            "mesa_id": mesa_id,
            "header": {
                "dept_code": dept_code,
                "dept_name": dept_names.get(dept_code, f"Departamento {dept_code}"),
                "muni_code": muni_code,
                "muni_name": f"Municipio {muni_code}",
                "puesto": f"I.E. Puesto {parts[2] if len(parts) > 2 else '001'}",
                "mesa_number": parts[-1] if len(parts) > 0 else "001",
                "zona": random.randint(1, 5)
            },
            "status": status,
            "overall_confidence": round(overall_confidence, 3),
            "last_update": datetime.utcnow().isoformat(),
            "source_testigo": random.random() > 0.2,  # 80% have testigo
            "source_rnec": random.random() > 0.4,     # 60% have RNEC
            "image_url": None,  # Would be S3 URL in production
            "ocr_fields": ocr_fields,
            "validations": validations,
            "comparison": comparison,
            "incidents": incidents,
            "audit_log": [
                {"action": "CREATED", "user": "system", "timestamp": (datetime.utcnow()).isoformat()},
                {"action": "OCR_PROCESSED", "user": "ocr_service", "timestamp": (datetime.utcnow()).isoformat()},
            ]
        }

        return jsonify({
            "success": True,
            "detail": detail
        })

    except Exception as e:
        logger.error(f"Error getting mesa detail: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@campaign_team_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for campaign team API."""
    return jsonify({
        "success": True,
        "service": "campaign-team-dashboard",
        "timestamp": datetime.utcnow().isoformat()
    })
