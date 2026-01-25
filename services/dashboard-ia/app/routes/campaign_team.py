"""
Routes para el Dashboard de Equipo de Campaña Electoral.
API para War Room, Reportes, Plan de Acción y Correlación E-14/Social.
"""
import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app, render_template

from app.schemas.campaign_team import AlertAssignRequest
from app.services.campaign_team_service import get_campaign_team_service

logger = logging.getLogger(__name__)

campaign_team_bp = Blueprint('campaign_team', __name__)


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
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        stats = service.get_war_room_stats(contest_id)

        return jsonify({
            "success": True,
            **stats.dict()
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
        contest_id = request.args.get('contest_id', type=int)
        if not contest_id:
            return jsonify({
                "success": False,
                "error": "contest_id is required"
            }), 400

        service = get_service()
        response = service.get_votes_by_candidate(contest_id)

        return jsonify(response.dict())

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

    Returns:
        E14 form data with candidates and OCR confidence
    """
    import os
    import json
    import glob

    try:
        # Look for E-14 extraction JSON files
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        pattern = os.path.join(backend_dir, 'e14_extraction_*.json')
        extraction_files = glob.glob(pattern)

        if not extraction_files:
            # Return mock data if no extraction files
            return jsonify({
                "success": True,
                "forms": [],
                "message": "No hay extracciones E-14 disponibles"
            })

        forms = []
        for filepath in extraction_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract relevant info
                header = data.get('header', {})
                nivelacion = data.get('nivelacion', {})
                partidos = data.get('partidos', [])
                resumen = data.get('resumen', {})

                # Build candidates list from all parties
                candidates = []
                for partido in partidos:
                    party_name = partido.get('party_name', 'Sin partido')
                    party_code = partido.get('party_code', '')
                    total_party = partido.get('total_votos', 0)
                    confidence = partido.get('confidence_total', 0.85)

                    # Add party aggregate votes
                    if partido.get('votos_agrupacion', 0) > 0 or not partido.get('votos_candidatos'):
                        candidates.append({
                            "party_code": party_code,
                            "party_name": party_name,
                            "candidate_number": "Lista",
                            "candidate_name": f"{party_name} (Lista)",
                            "votes": partido.get('votos_agrupacion', total_party),
                            "confidence": confidence,
                            "needs_review": partido.get('needs_review', False),
                            "is_party_vote": True
                        })

                    # Add individual candidates
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
                    "header": {
                        "election_name": header.get('election_name', ''),
                        "election_date": header.get('election_date', ''),
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
                    "total_partidos": len(partidos),
                    "overall_confidence": data.get('overall_confidence', 0.85)
                }

                forms.append(form_data)

            except Exception as e:
                logger.warning(f"Error reading E-14 file {filepath}: {e}")
                continue

        return jsonify({
            "success": True,
            "forms": forms,
            "total_forms": len(forms),
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting E-14 live data: {e}", exc_info=True)
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
