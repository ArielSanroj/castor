"""
Routes for the Electoral Intelligence Agent API.
Provides endpoints for agent control, monitoring, and HITL management.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request, current_app, g

from app.schemas.agent import (
    AgentConfigUpdateRequest,
    HITLApproveRequest,
    HITLRejectRequest,
)
from services.agent import ElectoralIntelligenceAgent, AgentConfig, AgentState
from services.agent.state import AgentStatus
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

# Global agent instance (initialized on first request)
_agent_instance: Optional[ElectoralIntelligenceAgent] = None
_agent_state: Optional[AgentState] = None


def get_agent() -> ElectoralIntelligenceAgent:
    """Get or create the agent instance."""
    global _agent_instance, _agent_state

    if _agent_instance is None:
        # Get Redis client if available
        redis_client = None
        try:
            from config import Config
            if Config.REDIS_URL:
                import redis
                redis_client = redis.from_url(Config.REDIS_URL)
        except Exception as e:
            logger.warning(f"Redis not available for agent: {e}")

        # Get OpenAI service if available
        openai_service = None
        try:
            from services.openai_service import OpenAIService
            openai_service = OpenAIService()
        except Exception as e:
            logger.warning(f"OpenAI service not available for agent: {e}")

        _agent_state = AgentState(redis_client)
        _agent_instance = ElectoralIntelligenceAgent(
            redis_client=redis_client,
            openai_service=openai_service
        )

    return _agent_instance


def get_state() -> AgentState:
    """Get the agent state manager."""
    global _agent_state
    if _agent_state is None:
        get_agent()  # This initializes state
    return _agent_state


def run_async(coro):
    """Run async coroutine in Flask context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ============================================================
# HEALTH AND STATUS ENDPOINTS
# ============================================================

@agent_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check for the agent.

    Returns:
        Agent health status
    """
    try:
        agent = get_agent()
        health = agent.get_health()
        return jsonify(health)
    except Exception as e:
        logger.error(f"Agent health check failed: {e}", exc_info=True)
        return jsonify({
            'healthy': False,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@agent_bp.route('/status', methods=['GET'])
def get_status():
    """
    Get current agent status and metrics.

    Returns:
        Agent status with metrics
    """
    try:
        agent = get_agent()
        status = agent.get_status()
        return jsonify({
            'success': True,
            **status
        })
    except Exception as e:
        logger.error(f"Error getting agent status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# AGENT CONTROL ENDPOINTS
# ============================================================

@agent_bp.route('/start', methods=['POST'])
@limiter.limit("5 per minute")
def start_agent():
    """
    Start the agent.

    Requires admin role in production.

    Returns:
        Start result
    """
    try:
        agent = get_agent()
        result = run_async(agent.start())

        if result:
            return jsonify({
                'success': True,
                'status': 'running',
                'message': 'Agent started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'status': agent.state.get_status().value,
                'message': 'Agent could not be started (may already be running)'
            }), 400

    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/stop', methods=['POST'])
@limiter.limit("5 per minute")
def stop_agent():
    """
    Stop the agent.

    Requires admin role in production.

    Returns:
        Stop result
    """
    try:
        agent = get_agent()
        result = run_async(agent.stop())

        if result:
            return jsonify({
                'success': True,
                'status': 'stopped',
                'message': 'Agent stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'status': agent.state.get_status().value,
                'message': 'Agent could not be stopped (may not be running)'
            }), 400

    except Exception as e:
        logger.error(f"Error stopping agent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/pause', methods=['POST'])
@limiter.limit("10 per minute")
def pause_agent():
    """Pause the agent (monitors continue but no actions taken)."""
    try:
        agent = get_agent()
        result = run_async(agent.pause())

        return jsonify({
            'success': result,
            'status': agent.state.get_status().value,
        })
    except Exception as e:
        logger.error(f"Error pausing agent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/resume', methods=['POST'])
@limiter.limit("10 per minute")
def resume_agent():
    """Resume a paused agent."""
    try:
        agent = get_agent()
        result = run_async(agent.resume())

        return jsonify({
            'success': result,
            'status': agent.state.get_status().value,
        })
    except Exception as e:
        logger.error(f"Error resuming agent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# CONFIGURATION ENDPOINTS
# ============================================================

@agent_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get current agent configuration.

    Returns:
        Agent configuration
    """
    try:
        from services.agent.config import get_agent_config
        config = get_agent_config()

        # Convert to dict, excluding non-serializable
        config_dict = {
            'E14_POLL_INTERVAL': config.E14_POLL_INTERVAL,
            'INCIDENT_POLL_INTERVAL': config.INCIDENT_POLL_INTERVAL,
            'KPI_POLL_INTERVAL': config.KPI_POLL_INTERVAL,
            'OCR_CONFIDENCE_THRESHOLD': config.OCR_CONFIDENCE_THRESHOLD,
            'ANOMALY_SCORE_THRESHOLD': config.ANOMALY_SCORE_THRESHOLD,
            'NULLITY_VIABILITY_THRESHOLD': config.NULLITY_VIABILITY_THRESHOLD,
            'ARITHMETIC_DELTA_THRESHOLD': config.ARITHMETIC_DELTA_THRESHOLD,
            'GEOGRAPHIC_CLUSTER_THRESHOLD': config.GEOGRAPHIC_CLUSTER_THRESHOLD,
            'SLA_WARNING_P0': config.SLA_WARNING_P0,
            'SLA_WARNING_P1': config.SLA_WARNING_P1,
            'SLA_WARNING_P2': config.SLA_WARNING_P2,
            'HITL_AUTO_ESCALATE_AFTER_MINUTES': config.HITL_AUTO_ESCALATE_AFTER_MINUTES,
            'BRIEFING_INTERVAL_MINUTES': config.BRIEFING_INTERVAL_MINUTES,
            'AUTO_INCIDENT_CREATION': config.AUTO_INCIDENT_CREATION,
            'AUTO_LEGAL_CLASSIFICATION': config.AUTO_LEGAL_CLASSIFICATION,
            'AUTO_RISK_SCORING': config.AUTO_RISK_SCORING,
            'LLM_BRIEFINGS_ENABLED': config.LLM_BRIEFINGS_ENABLED,
        }

        return jsonify({'success': True, 'config': config_dict})

    except Exception as e:
        logger.error(f"Error getting agent config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/config', methods=['PUT'])
@limiter.limit("10 per minute")
def update_config():
    """
    Update agent configuration.

    Requires admin role in production.

    Returns:
        Updated configuration
    """
    try:
        data = request.get_json() or {}

        # Validate with Pydantic
        update_request = AgentConfigUpdateRequest(**data)

        from services.agent.config import get_agent_config
        config = get_agent_config()

        # Update only provided values
        updated_fields = []
        for field, value in update_request.model_dump(exclude_none=True).items():
            if hasattr(config, field):
                setattr(config, field, value)
                updated_fields.append(field)

        logger.info(f"Agent config updated: {updated_fields}")

        return jsonify({
            'success': True,
            'updated_fields': updated_fields,
            'message': f'Updated {len(updated_fields)} configuration fields'
        })

    except Exception as e:
        logger.error(f"Error updating agent config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================
# ACTIONS ENDPOINTS
# ============================================================

@agent_bp.route('/actions', methods=['GET'])
def get_actions():
    """
    Get recent agent actions.

    Query params:
        limit (optional): Max results (default 50, max 200)

    Returns:
        List of recent actions
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 200)

        agent = get_agent()
        actions = agent.get_recent_actions(limit)

        return jsonify({
            'success': True,
            'actions': actions,
            'total': len(actions)
        })

    except Exception as e:
        logger.error(f"Error getting agent actions: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# HITL ENDPOINTS
# ============================================================

@agent_bp.route('/hitl/pending', methods=['GET'])
def get_pending_hitl():
    """
    Get pending HITL approval requests.

    Returns:
        List of pending requests
    """
    try:
        agent = get_agent()
        pending = agent.get_pending_hitl()

        return jsonify({
            'success': True,
            'requests': pending,
            'total': len(pending),
            'pending_count': len(pending)
        })

    except Exception as e:
        logger.error(f"Error getting pending HITL: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/hitl/<request_id>/approve', methods=['POST'])
@limiter.limit("30 per minute")
def approve_hitl(request_id: str):
    """
    Approve a HITL request.

    Args:
        request_id: HITL request ID

    Returns:
        Approval result
    """
    try:
        data = request.get_json() or {}

        # Get user ID from auth context (simplified for now)
        user_id = data.get('user_id', 'unknown')
        notes = data.get('notes')

        agent = get_agent()
        result = agent.approve_hitl(request_id, user_id, notes)

        if result:
            return jsonify({
                'success': True,
                'message': f'Request {request_id} approved'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Request not found or already processed'
            }), 404

    except Exception as e:
        logger.error(f"Error approving HITL: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/hitl/<request_id>/reject', methods=['POST'])
@limiter.limit("30 per minute")
def reject_hitl(request_id: str):
    """
    Reject a HITL request.

    Args:
        request_id: HITL request ID

    Returns:
        Rejection result
    """
    try:
        data = request.get_json() or {}

        # Validate
        if not data.get('notes'):
            return jsonify({
                'success': False,
                'error': 'Rejection notes are required'
            }), 400

        user_id = data.get('user_id', 'unknown')
        notes = data['notes']

        agent = get_agent()
        result = agent.reject_hitl(request_id, user_id, notes)

        if result:
            return jsonify({
                'success': True,
                'message': f'Request {request_id} rejected'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Request not found or already processed'
            }), 404

    except Exception as e:
        logger.error(f"Error rejecting HITL: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# BRIEFING ENDPOINTS
# ============================================================

@agent_bp.route('/briefing/latest', methods=['GET'])
def get_latest_briefing():
    """
    Get the latest intelligence briefing.

    Returns:
        Latest briefing
    """
    try:
        agent = get_agent()
        briefing = agent.get_latest_briefing()

        if briefing:
            return jsonify({
                'success': True,
                **briefing
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No briefings available yet'
            }), 404

    except Exception as e:
        logger.error(f"Error getting latest briefing: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/briefing/generate', methods=['POST'])
@limiter.limit("5 per minute")
def generate_briefing():
    """
    Force generation of a new briefing.

    Returns:
        Generated briefing
    """
    try:
        agent = get_agent()
        briefing = run_async(agent.generate_briefing())

        return jsonify({
            'success': True,
            **briefing
        })

    except Exception as e:
        logger.error(f"Error generating briefing: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PROCESSING ENDPOINTS
# ============================================================

@agent_bp.route('/process/e14', methods=['POST'])
@limiter.limit("60 per minute")
def process_e14():
    """
    Process an E-14 form through the agent.

    Request body should contain form_data in E14PayloadV2 format.

    Returns:
        Processing result with actions taken
    """
    try:
        data = request.get_json()
        if not data or 'form_data' not in data:
            return jsonify({
                'success': False,
                'error': 'form_data is required'
            }), 400

        agent = get_agent()
        actions = run_async(agent.process_e14_form(data['form_data']))

        return jsonify({
            'success': True,
            'actions_taken': actions,
            'count': len(actions)
        })

    except Exception as e:
        logger.error(f"Error processing E-14: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/process/incident', methods=['POST'])
@limiter.limit("60 per minute")
def process_incident():
    """
    Process an incident update through the agent.

    Returns:
        Processing result with actions taken
    """
    try:
        data = request.get_json()
        if not data or 'incident' not in data:
            return jsonify({
                'success': False,
                'error': 'incident is required'
            }), 400

        agent = get_agent()
        actions = run_async(agent.process_incident_update(data['incident']))

        return jsonify({
            'success': True,
            'actions_taken': actions,
            'count': len(actions)
        })

    except Exception as e:
        logger.error(f"Error processing incident: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# BATCH PROCESSING ENDPOINTS
# ============================================================

@agent_bp.route('/batch/start', methods=['POST'])
@limiter.limit("2 per minute")
def start_batch_processing():
    """
    Start batch processing of all E-14 forms.

    Query params:
        max_forms (optional): Maximum forms to process
        batch_size (optional): Forms per batch (default 500)

    Returns:
        Batch processing start result
    """
    try:
        from tasks.agent_tasks import process_all_e14_forms, get_batch_processing_status

        # Check if already running
        status = get_batch_processing_status()
        if status.get('running'):
            return jsonify({
                'success': False,
                'error': 'Batch processing already running',
                'progress': status.get('progress', 0),
                'total': status.get('total', 0)
            }), 409

        data = request.get_json() or {}
        max_forms = data.get('max_forms')
        batch_size = data.get('batch_size', 500)

        # Start processing in background thread
        import threading

        def run_batch():
            process_all_e14_forms(
                batch_size=batch_size,
                max_forms=max_forms,
                create_incidents=True
            )

        thread = threading.Thread(target=run_batch, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Batch processing started',
            'batch_size': batch_size,
            'max_forms': max_forms
        })

    except Exception as e:
        logger.error(f"Error starting batch processing: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/batch/status', methods=['GET'])
def get_batch_status():
    """
    Get current batch processing status.

    Returns:
        Batch processing status
    """
    try:
        from tasks.agent_tasks import get_batch_processing_status

        status = get_batch_processing_status()

        # Calculate progress percentage
        if status.get('total', 0) > 0:
            status['progress_percent'] = round(
                status.get('progress', 0) / status['total'] * 100, 2
            )
        else:
            status['progress_percent'] = 0

        return jsonify({
            'success': True,
            **status
        })

    except Exception as e:
        logger.error(f"Error getting batch status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/batch/results', methods=['GET'])
def get_batch_results():
    """
    Get batch processing results.

    Returns:
        Detailed results including anomalies by type and department
    """
    try:
        from tasks.agent_tasks import get_batch_processing_status

        status = get_batch_processing_status()

        if not status.get('completed_at'):
            return jsonify({
                'success': False,
                'error': 'Batch processing not completed yet',
                'running': status.get('running', False),
                'progress': status.get('progress', 0),
                'total': status.get('total', 0)
            }), 404

        return jsonify({
            'success': True,
            'results': {
                'total_processed': status.get('progress', 0),
                'total_anomalies': status.get('anomalies_found', 0),
                'incidents_created': status.get('incidents_created', 0),
                'by_type': status.get('by_type', {}),
                'by_department': status.get('by_department', {}),
                'high_priority': status.get('high_priority', []),
                'started_at': status.get('started_at'),
                'completed_at': status.get('completed_at'),
            }
        })

    except Exception as e:
        logger.error(f"Error getting batch results: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/analyze/department/<departamento>', methods=['POST'])
@limiter.limit("10 per minute")
def analyze_department(departamento: str):
    """
    Analyze all E-14 forms for a specific department.

    Args:
        departamento: Department name

    Returns:
        Analysis results including anomalies and risk score
    """
    try:
        from tasks.agent_tasks import analyze_department as analyze_dept_task

        results = analyze_dept_task(departamento)

        return jsonify({
            'success': True,
            **results
        })

    except Exception as e:
        logger.error(f"Error analyzing department: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/data/stats', methods=['GET'])
def get_e14_data_stats():
    """
    Get E-14 data statistics for the agent.

    Returns:
        Stats about available E-14 data
    """
    try:
        from services.agent.e14_data_service import E14DataService

        data_service = E14DataService()
        stats = data_service.get_stats()

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"Error getting E-14 stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
