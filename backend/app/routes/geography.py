"""
Routes para el módulo geoespacial del War Room.
Endpoints para mapa choropleth y estadísticas por departamento.
"""
import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app

from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

geography_bp = Blueprint('geography', __name__)

# Exempt from rate limiting - dashboard makes many parallel calls
limiter.exempt(geography_bp)

# Cache for GeoJSON data
_geojson_cache = None

# Demo data for department metrics
_dept_metrics_cache = {}


def load_geojson():
    """Load Colombia departments GeoJSON."""
    global _geojson_cache

    if _geojson_cache is not None:
        return _geojson_cache

    try:
        # Find the static folder
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        project_root = os.path.dirname(app_dir)
        geojson_path = os.path.join(project_root, 'static', 'data', 'colombia-departments.geojson')

        if os.path.exists(geojson_path):
            with open(geojson_path, 'r', encoding='utf-8') as f:
                _geojson_cache = json.load(f)
                return _geojson_cache
        else:
            logger.warning(f"GeoJSON file not found at {geojson_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading GeoJSON: {e}")
        return None


def generate_dept_metrics(dept_code: str, mode: str = 'coverage'):
    """Generate demo metrics for a department."""
    # Use cached if available
    cache_key = f"{dept_code}_{mode}"
    if cache_key in _dept_metrics_cache:
        return _dept_metrics_cache[cache_key]

    # Generate consistent random data based on dept_code
    random.seed(hash(dept_code) % 1000)

    total_mesas = random.randint(200, 2000)
    processed_testigo = int(total_mesas * random.uniform(0.3, 0.9))
    processed_rnec = int(total_mesas * random.uniform(0.1, 0.7))
    reconciled = int(min(processed_testigo, processed_rnec) * random.uniform(0.5, 0.95))

    high_risk = int(total_mesas * random.uniform(0.02, 0.15))
    medium_risk = int(total_mesas * random.uniform(0.05, 0.20))

    # Calculate mode-specific value
    if mode == 'coverage':
        value = (processed_testigo + processed_rnec) / (total_mesas * 2) * 100 if total_mesas > 0 else 0
    elif mode == 'risk':
        value = (high_risk + medium_risk * 0.5) / total_mesas * 100 if total_mesas > 0 else 0
    elif mode == 'discrepancy':
        value = random.uniform(0, 12)  # 0-12% discrepancy
    else:  # votes
        value = random.uniform(5, 35)  # Vote percentage for selected candidate

    metrics = {
        "dept_code": dept_code,
        "value": round(value, 1),
        "mesas_total": total_mesas,
        "mesas_testigo": processed_testigo,
        "mesas_rnec": processed_rnec,
        "mesas_reconciled": reconciled,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": total_mesas - high_risk - medium_risk,
        "coverage_pct": round((processed_testigo + processed_rnec) / (total_mesas * 2) * 100, 1) if total_mesas > 0 else 0,
        "incidents_open": random.randint(0, 10),
        "incidents_p0": random.randint(0, 3),
    }

    _dept_metrics_cache[cache_key] = metrics
    return metrics


def get_color_for_value(value: float, mode: str) -> str:
    """Get color based on value and mode."""
    if mode == 'coverage':
        # Green (high) to Red (low)
        if value >= 80:
            return '#4A7C59'  # Green
        elif value >= 60:
            return '#7CB342'  # Light green
        elif value >= 40:
            return '#D4A017'  # Yellow/Warning
        elif value >= 20:
            return '#E65100'  # Orange
        else:
            return '#8B3A3A'  # Red

    elif mode == 'risk':
        # Red (high) to Green (low) - inverted
        if value >= 15:
            return '#8B3A3A'  # Red
        elif value >= 10:
            return '#E65100'  # Orange
        elif value >= 5:
            return '#D4A017'  # Yellow
        elif value >= 2:
            return '#7CB342'  # Light green
        else:
            return '#4A7C59'  # Green

    elif mode == 'discrepancy':
        # Orange (high) to Green (low)
        if value >= 10:
            return '#E65100'  # Orange
        elif value >= 5:
            return '#D4A017'  # Yellow
        elif value >= 2:
            return '#7CB342'  # Light green
        else:
            return '#4A7C59'  # Green

    else:  # votes
        # Purple scale for vote percentage
        if value >= 30:
            return '#7B1FA2'  # Dark purple
        elif value >= 20:
            return '#9C27B0'  # Purple
        elif value >= 15:
            return '#BA68C8'  # Light purple
        elif value >= 10:
            return '#CE93D8'  # Very light purple
        else:
            return '#E1BEE7'  # Pale purple


# ============================================================
# CHOROPLETH ENDPOINT
# ============================================================

@geography_bp.route('/choropleth', methods=['GET'])
def get_choropleth():
    """
    Get GeoJSON with metrics for choropleth map.

    Query params:
        mode: coverage | risk | discrepancy | votes (default: coverage)
        contest_id: Contest ID (optional)
        candidate_id: Candidate ID for votes mode (optional)

    Returns:
        GeoJSON with properties containing metrics and colors
    """
    try:
        mode = request.args.get('mode', 'coverage')
        contest_id = request.args.get('contest_id', type=int)

        geojson = load_geojson()
        if not geojson:
            return jsonify({
                "success": False,
                "error": "GeoJSON data not available"
            }), 500

        # Enrich features with metrics
        enriched_features = []
        for feature in geojson.get('features', []):
            dept_code = feature['properties'].get('code')
            dept_name = feature['properties'].get('name')

            if not dept_code:
                continue

            metrics = generate_dept_metrics(dept_code, mode)
            color = get_color_for_value(metrics['value'], mode)

            enriched_feature = {
                "type": "Feature",
                "properties": {
                    **feature['properties'],
                    "metrics": metrics,
                    "fill_color": color,
                    "value": metrics['value'],
                    "mode": mode
                },
                "geometry": feature['geometry']
            }
            enriched_features.append(enriched_feature)

        return jsonify({
            "success": True,
            "type": "FeatureCollection",
            "features": enriched_features,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting choropleth data: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# DEPARTMENT STATS ENDPOINT
# ============================================================

@geography_bp.route('/department/<dept_code>/stats', methods=['GET'])
def get_department_stats(dept_code: str):
    """
    Get detailed statistics for a specific department.

    Path params:
        dept_code: Department code (e.g., "05" for Antioquia)

    Returns:
        Detailed KPIs and metrics for the department
    """
    try:
        geojson = load_geojson()
        dept_info = None

        if geojson:
            for feature in geojson.get('features', []):
                if feature['properties'].get('code') == dept_code:
                    dept_info = feature['properties']
                    break

        metrics = generate_dept_metrics(dept_code, 'coverage')

        # Generate additional stats
        random.seed(hash(dept_code) % 1000 + 1)

        stats = {
            "dept_code": dept_code,
            "dept_name": dept_info.get('name') if dept_info else f"Departamento {dept_code}",
            "capital": dept_info.get('capital') if dept_info else None,
            **metrics,
            "top_candidates": [
                {"name": "Paloma Valencia", "votes": random.randint(5000, 20000), "percentage": round(random.uniform(15, 25), 1)},
                {"name": "Vicky Dávila", "votes": random.randint(4000, 18000), "percentage": round(random.uniform(12, 22), 1)},
                {"name": "Juan Carlos Pinzón", "votes": random.randint(3000, 15000), "percentage": round(random.uniform(10, 18), 1)},
            ],
            "municipalities_processed": random.randint(10, 50),
            "municipalities_total": random.randint(20, 60),
            "last_update": datetime.utcnow().isoformat()
        }

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error getting department stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# DEPARTMENT INCIDENTS ENDPOINT
# ============================================================

@geography_bp.route('/department/<dept_code>/incidents', methods=['GET'])
def get_department_incidents(dept_code: str):
    """
    Get incidents for a specific department.

    Path params:
        dept_code: Department code

    Query params:
        limit: Max results (default 10)

    Returns:
        List of incidents in the department
    """
    try:
        limit = request.args.get('limit', 10, type=int)

        geojson = load_geojson()
        dept_name = None

        if geojson:
            for feature in geojson.get('features', []):
                if feature['properties'].get('code') == dept_code:
                    dept_name = feature['properties'].get('name')
                    break

        # Generate demo incidents
        random.seed(hash(dept_code) % 1000 + 2)
        incident_types = ['OCR_LOW_CONF', 'ARITHMETIC_FAIL', 'E11_VS_URNA', 'DISCREPANCY_RNEC', 'SOURCE_MISMATCH']
        severities = ['P0', 'P0', 'P1', 'P1', 'P1', 'P2', 'P2', 'P3']

        incidents = []
        num_incidents = random.randint(2, min(limit, 8))

        for i in range(num_incidents):
            incidents.append({
                "id": random.randint(100, 999),
                "incident_type": random.choice(incident_types),
                "severity": random.choice(severities),
                "status": "OPEN" if random.random() > 0.3 else "ASSIGNED",
                "mesa_id": f"{dept_code}-{random.randint(1, 50):03d}-{random.randint(1, 20):03d}-{random.randint(1, 5):02d}-{random.randint(1, 10):03d}",
                "dept_code": dept_code,
                "dept_name": dept_name,
                "muni_name": f"Municipio {random.randint(1, 20)}",
                "description": f"Incidente detectado en mesa de {dept_name or dept_code}",
                "ocr_confidence": round(random.uniform(0.45, 0.85), 2) if random.random() > 0.3 else None,
                "sla_remaining_minutes": random.randint(0, 25),
                "created_at": datetime.utcnow().isoformat()
            })

        # Sort by severity
        severity_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        incidents.sort(key=lambda x: severity_order.get(x['severity'], 4))

        return jsonify({
            "success": True,
            "dept_code": dept_code,
            "dept_name": dept_name,
            "incidents": incidents[:limit],
            "total": len(incidents)
        })

    except Exception as e:
        logger.error(f"Error getting department incidents: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@geography_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for geography API."""
    geojson = load_geojson()
    return jsonify({
        "success": True,
        "service": "geography",
        "geojson_loaded": geojson is not None,
        "departments_count": len(geojson.get('features', [])) if geojson else 0,
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================
# MOE RISK DATA
# ============================================================

_moe_risk_cache = None

def load_moe_risk_data():
    """Load MOE electoral risk municipalities data."""
    global _moe_risk_cache

    if _moe_risk_cache is not None:
        return _moe_risk_cache

    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        moe_path = os.path.join(app_dir, 'data', 'moe_risk_municipalities.json')

        if os.path.exists(moe_path):
            with open(moe_path, 'r', encoding='utf-8') as f:
                _moe_risk_cache = json.load(f)
                logger.info(f"Loaded MOE risk data: {len(_moe_risk_cache.get('municipalities', []))} municipalities")
                return _moe_risk_cache
        else:
            logger.warning(f"MOE risk file not found at {moe_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading MOE risk data: {e}")
        return None


@geography_bp.route('/moe/risk-municipalities', methods=['GET'])
def get_moe_risk_municipalities():
    """
    Get MOE electoral risk municipalities data.

    Query params:
    - department: Filter by department code
    - risk_level: Filter by risk level (EXTREME, HIGH)
    - factor: Filter by risk factor
    """
    try:
        moe_data = load_moe_risk_data()

        if not moe_data:
            return jsonify({
                "success": False,
                "error": "MOE risk data not available"
            }), 404

        # Get filter parameters
        dept_filter = request.args.get('department')
        risk_filter = request.args.get('risk_level')
        factor_filter = request.args.get('factor')

        municipalities = moe_data.get('municipalities', [])

        # Apply filters
        if dept_filter:
            municipalities = [m for m in municipalities if m.get('department_code') == dept_filter]

        if risk_filter:
            municipalities = [m for m in municipalities if m.get('risk_level') == risk_filter.upper()]

        if factor_filter:
            municipalities = [m for m in municipalities if factor_filter.upper() in m.get('factors', [])]

        return jsonify({
            "success": True,
            "metadata": moe_data.get('metadata', {}),
            "risk_factors": moe_data.get('risk_factors', {}),
            "department_summary": moe_data.get('department_summary', {}),
            "municipalities": municipalities,
            "filtered_count": len(municipalities),
            "total_count": len(moe_data.get('municipalities', []))
        })

    except Exception as e:
        logger.error(f"Error in MOE risk municipalities: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@geography_bp.route('/moe/department-summary', methods=['GET'])
def get_moe_department_summary():
    """Get MOE risk summary by department."""
    try:
        moe_data = load_moe_risk_data()

        if not moe_data:
            return jsonify({
                "success": False,
                "error": "MOE risk data not available"
            }), 404

        return jsonify({
            "success": True,
            "department_summary": moe_data.get('department_summary', {}),
            "metadata": moe_data.get('metadata', {})
        })

    except Exception as e:
        logger.error(f"Error in MOE department summary: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
