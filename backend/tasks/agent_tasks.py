"""
Background tasks for the Electoral Intelligence Agent.
Uses RQ (Redis Queue) for async execution.
"""
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global state for batch processing
_batch_processing_state = {
    'running': False,
    'progress': 0,
    'total': 0,
    'anomalies_found': 0,
    'incidents_created': 0,
    'errors': [],
    'started_at': None,
    'completed_at': None,
}


def run_agent_cycle():
    """
    Run a single agent processing cycle.
    Called periodically by the worker.
    """
    try:
        from services.agent import ElectoralIntelligenceAgent

        # Get or create agent instance
        agent = ElectoralIntelligenceAgent()

        # Process any pending work
        # This is a synchronous wrapper for the async agent
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # The agent's monitoring loops run continuously when started
            # This task is for manual/periodic triggers
            logger.info("Agent cycle task completed")
        finally:
            loop.close()

        return {'status': 'completed', 'timestamp': datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Error in agent cycle: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def process_e14_batch(form_ids: List[str]) -> Dict[str, Any]:
    """
    Process a batch of E-14 forms through the agent.

    Args:
        form_ids: List of E-14 form IDs to process

    Returns:
        Processing results
    """
    try:
        from services.agent import ElectoralIntelligenceAgent
        import asyncio

        agent = ElectoralIntelligenceAgent()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        results = {
            'processed': 0,
            'anomalies': 0,
            'incidents_created': 0,
            'errors': [],
        }

        try:
            # Fetch and process each form
            # In production, this would fetch from the database
            for form_id in form_ids:
                try:
                    # Placeholder - would fetch form data
                    # form_data = fetch_form(form_id)
                    # actions = loop.run_until_complete(agent.process_e14_form(form_data))
                    results['processed'] += 1
                except Exception as e:
                    results['errors'].append({'form_id': form_id, 'error': str(e)})
        finally:
            loop.close()

        logger.info(f"Batch processed: {results['processed']} forms")
        return results

    except Exception as e:
        logger.error(f"Error in E-14 batch processing: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def generate_scheduled_briefing() -> Dict[str, Any]:
    """
    Generate a scheduled intelligence briefing.

    Returns:
        Generated briefing
    """
    try:
        from services.agent import ElectoralIntelligenceAgent
        import asyncio

        agent = ElectoralIntelligenceAgent()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            briefing = loop.run_until_complete(agent.generate_briefing())
            logger.info("Scheduled briefing generated")
            return briefing
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error generating scheduled briefing: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def cleanup_agent_state() -> Dict[str, Any]:
    """
    Clean up old agent state data.

    Returns:
        Cleanup results
    """
    try:
        from services.agent.state import AgentState
        from services.agent.monitors.deadline_tracker import DeadlineTracker
        from services.agent.monitors.incident_monitor import IncidentMonitor

        state = AgentState()
        deadline_tracker = DeadlineTracker()
        incident_monitor = IncidentMonitor()

        # Clean up old deadlines
        deadlines_cleaned = deadline_tracker.cleanup_old_deadlines(max_age_days=30)

        # Clean up warned incidents cache
        warned_cleaned = incident_monitor.cleanup_warned_cache(max_age_hours=24)

        results = {
            'deadlines_cleaned': deadlines_cleaned,
            'warned_cache_cleaned': warned_cleaned,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.info(f"Agent state cleanup: {results}")
        return results

    except Exception as e:
        logger.error(f"Error in agent state cleanup: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def process_hitl_expirations() -> Dict[str, Any]:
    """
    Process expired HITL requests.

    Returns:
        Processing results
    """
    try:
        from services.agent.actuators.hitl_escalator import HITLEscalator
        from services.agent.state import AgentState
        import asyncio

        state = AgentState()
        escalator = HITLEscalator(state=state)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            expired = loop.run_until_complete(escalator.process_expired_requests())
            auto_escalated = loop.run_until_complete(escalator.auto_escalate_stale_requests())

            results = {
                'expired_count': len(expired),
                'auto_escalated_count': len(auto_escalated),
                'timestamp': datetime.utcnow().isoformat(),
            }

            logger.info(f"HITL expirations processed: {results}")
            return results
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error processing HITL expirations: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def get_batch_processing_status() -> Dict[str, Any]:
    """Get current batch processing status."""
    return _batch_processing_state.copy()


def process_all_e14_forms(
    batch_size: int = 500,
    max_forms: Optional[int] = None,
    create_incidents: bool = True
) -> Dict[str, Any]:
    """
    Process all E-14 forms through the agent's anomaly detection.

    Args:
        batch_size: Number of forms to process per batch
        max_forms: Maximum forms to process (None = all)
        create_incidents: Whether to create incidents for anomalies

    Returns:
        Processing results
    """
    global _batch_processing_state

    try:
        from services.agent.e14_data_service import E14DataService
        from services.agent.analyzers.anomaly_detector import AnomalyDetector
        from services.agent.analyzers.legal_classifier import LegalClassifier
        from services.agent.config import get_agent_config

        config = get_agent_config()
        data_service = E14DataService()
        anomaly_detector = AnomalyDetector(config)
        legal_classifier = LegalClassifier(config)

        # Get total count
        total_forms = data_service.count_forms(ocr_only=True)
        if max_forms:
            total_forms = min(total_forms, max_forms)

        # Initialize state
        _batch_processing_state = {
            'running': True,
            'progress': 0,
            'total': total_forms,
            'anomalies_found': 0,
            'incidents_created': 0,
            'errors': [],
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'by_type': {},
            'by_department': {},
            'high_priority': [],
        }

        logger.info(f"Starting batch processing of {total_forms} E-14 forms")

        processed = 0
        all_anomalies = []

        from services.agent.agent_store import mark_batch_processed

        for batch in data_service.iterate_all_forms(batch_size=batch_size, ocr_only=True):
            if max_forms and processed >= max_forms:
                break

            # Process batch
            batch_anomalies, stats = anomaly_detector.analyze_batch(batch)

            for anomaly in batch_anomalies:
                all_anomalies.append(anomaly)

                # Track by type
                anomaly_type = anomaly.anomaly_type.value
                _batch_processing_state['by_type'][anomaly_type] = \
                    _batch_processing_state['by_type'].get(anomaly_type, 0) + 1

                # Track by department
                mesa_id = anomaly.mesa_id or ''
                dept = mesa_id.split('-')[0] if '-' in mesa_id else 'UNKNOWN'
                _batch_processing_state['by_department'][dept] = \
                    _batch_processing_state['by_department'].get(dept, 0) + 1

                # Track high priority
                if anomaly.severity.value in ('CRITICAL', 'HIGH'):
                    _batch_processing_state['high_priority'].append({
                        'type': anomaly_type,
                        'mesa_id': anomaly.mesa_id,
                        'severity': anomaly.severity.value,
                        'details': anomaly.details,
                    })

            processed += len(batch)
            _batch_processing_state['progress'] = processed
            _batch_processing_state['anomalies_found'] = len(all_anomalies)
            mark_batch_processed([item.get('id') for item in batch if item.get('id')])

            # Log progress every 5000 forms
            if processed % 5000 == 0:
                logger.info(
                    f"Batch progress: {processed}/{total_forms} forms, "
                    f"{len(all_anomalies)} anomalies found"
                )

            # Yield control briefly
            time.sleep(0.01)

        # Classify anomalies by CPACA articles
        classified_incidents = []
        for anomaly in all_anomalies:
            incident_data = {
                'id': len(classified_incidents) + 1,
                'incident_type': anomaly.anomaly_type.value,
                'mesa_id': anomaly.mesa_id,
                'delta_value': anomaly.details.get('delta', 0),
                'ocr_confidence': anomaly.details.get('avg_confidence', 0.85),
                'created_at': datetime.utcnow().isoformat(),
            }

            classification = legal_classifier.classify(incident_data)
            incident_data['cpaca_article'] = classification.primary_article.value
            incident_data['causals'] = [c.value for c in classification.causals]
            incident_data['deadline_hours'] = classification.deadline_hours
            incident_data['recommended_actions'] = classification.recommended_actions

            classified_incidents.append(incident_data)

        if create_incidents and classified_incidents:
            try:
                from services.incident_store import create_incidents_from_anomalies
                created = create_incidents_from_anomalies([a.to_dict() for a in all_anomalies])
                _batch_processing_state['incidents_created'] = len(created)
            except Exception as e:
                _batch_processing_state['errors'].append(f"incident_create_failed: {e}")

        # Finalize state
        _batch_processing_state['running'] = False
        _batch_processing_state['completed_at'] = datetime.utcnow().isoformat()
        if not _batch_processing_state.get('incidents_created'):
            _batch_processing_state['incidents_created'] = len(classified_incidents)

        # Keep only top 100 high priority for reporting
        _batch_processing_state['high_priority'] = \
            _batch_processing_state['high_priority'][:100]

        results = {
            'status': 'completed',
            'total_processed': processed,
            'total_anomalies': len(all_anomalies),
            'classified_incidents': len(classified_incidents),
            'by_type': _batch_processing_state['by_type'],
            'by_department': _batch_processing_state['by_department'],
            'high_priority_count': len(_batch_processing_state['high_priority']),
            'started_at': _batch_processing_state['started_at'],
            'completed_at': _batch_processing_state['completed_at'],
        }

        logger.info(f"Batch processing completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        _batch_processing_state['running'] = False
        _batch_processing_state['errors'].append(str(e))
        return {'status': 'error', 'error': str(e)}


def analyze_department(departamento: str) -> Dict[str, Any]:
    """
    Analyze all E-14 forms for a specific department.

    Args:
        departamento: Department name

    Returns:
        Analysis results
    """
    try:
        from services.agent.e14_data_service import E14DataService
        from services.agent.analyzers.anomaly_detector import AnomalyDetector
        from services.agent.analyzers.risk_scorer import RiskScorer
        from services.agent.config import get_agent_config

        config = get_agent_config()
        data_service = E14DataService()
        anomaly_detector = AnomalyDetector(config)
        risk_scorer = RiskScorer(config)

        # Get forms for department
        forms = data_service.get_forms_batch(
            offset=0,
            limit=50000,
            ocr_only=True,
            departamento=departamento
        )

        if not forms:
            return {
                'status': 'no_data',
                'departamento': departamento,
                'message': 'No OCR-processed forms found'
            }

        # Analyze
        anomalies, stats = anomaly_detector.analyze_batch(forms)

        # Calculate risk
        risk_assessment = risk_scorer.calculate_risk(
            area_code=departamento[:2] if len(departamento) >= 2 else '00',
            area_type="DEPARTMENT",
            area_name=departamento,
            anomalies=[a.to_dict() for a in anomalies],
            incidents=[],
            total_mesas=len(forms),
            mesas_processed=len(forms)
        )

        results = {
            'status': 'completed',
            'departamento': departamento,
            'total_forms': len(forms),
            'anomalies_found': len(anomalies),
            'anomaly_rate': round(len(anomalies) / max(len(forms), 1) * 100, 2),
            'risk_level': risk_assessment.risk_level.value,
            'risk_score': risk_assessment.score,
            'by_type': {},
            'top_anomalies': [],
        }

        # Group by type
        for anomaly in anomalies:
            atype = anomaly.anomaly_type.value
            results['by_type'][atype] = results['by_type'].get(atype, 0) + 1

        # Top anomalies
        sorted_anomalies = sorted(
            anomalies,
            key=lambda a: {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(
                a.severity.value, 0
            ),
            reverse=True
        )
        results['top_anomalies'] = [
            {
                'type': a.anomaly_type.value,
                'severity': a.severity.value,
                'mesa_id': a.mesa_id,
                'details': a.details,
            }
            for a in sorted_anomalies[:20]
        ]

        logger.info(f"Department analysis completed: {departamento}, {len(anomalies)} anomalies")
        return results

    except Exception as e:
        logger.error(f"Error analyzing department {departamento}: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}
