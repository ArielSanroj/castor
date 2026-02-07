"""
Electoral Intelligence Agent - Main Orchestrator.

Autonomous agent that monitors electoral dashboards, detects anomalies,
and takes actions with measurable OKRs and KPIs.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from services.agent.config import AgentConfig, AgentAction, HITLRequirement, get_agent_config
from services.agent.state import AgentState, AgentStatus, ActionRecord, HITLRequest, AgentMetrics
from services.agent.decision_engine import DecisionEngine, Decision

logger = logging.getLogger(__name__)


class ElectoralIntelligenceAgent:
    """
    Main orchestrator for the Electoral Intelligence Agent.

    Coordinates monitors, analyzers, and actuators to provide
    autonomous electoral monitoring and response.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        redis_client=None,
        openai_service=None
    ):
        """
        Initialize the Electoral Intelligence Agent.

        Args:
            config: Agent configuration (uses singleton if None)
            redis_client: Redis client for state persistence
            openai_service: OpenAI service for LLM-powered features
        """
        self.config = config or get_agent_config()
        self.state = AgentState(redis_client)
        self.decision_engine = DecisionEngine(self.config)
        self._openai_service = openai_service

        # Thread pool for parallel operations
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Monitor references (lazy-loaded)
        self._e14_monitor = None
        self._incident_monitor = None
        self._deadline_tracker = None
        self._kpi_monitor = None

        # Actuator references (lazy-loaded)
        self._incident_creator = None
        self._alert_dispatcher = None
        self._report_generator = None
        self._hitl_escalator = None

        # Running state
        self._running = False
        self._tasks: List[asyncio.Task] = []

        logger.info("ElectoralIntelligenceAgent initialized")

    # ============================================================
    # Lifecycle Methods
    # ============================================================

    async def start(self) -> bool:
        """
        Start the agent.

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Agent is already running")
            return False

        try:
            self.state.set_status(AgentStatus.STARTING)
            self.state.set_started_at()

            # Initialize monitors
            await self._initialize_monitors()

            # Start monitoring loops
            self._running = True
            self._tasks = [
                asyncio.create_task(self._e14_monitoring_loop()),
                asyncio.create_task(self._incident_monitoring_loop()),
                asyncio.create_task(self._deadline_monitoring_loop()),
                asyncio.create_task(self._kpi_monitoring_loop()),
                asyncio.create_task(self._briefing_loop()),
            ]

            self.state.set_status(AgentStatus.RUNNING)
            logger.info("Agent started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start agent: {e}", exc_info=True)
            self.state.set_status(AgentStatus.ERROR)
            return False

    async def stop(self) -> bool:
        """
        Stop the agent.

        Returns:
            True if stopped successfully
        """
        if not self._running:
            logger.warning("Agent is not running")
            return False

        try:
            self._running = False

            # Cancel all tasks
            for task in self._tasks:
                task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []

            self.state.set_status(AgentStatus.STOPPED)
            self.state.update_uptime()
            logger.info("Agent stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping agent: {e}", exc_info=True)
            return False

    async def pause(self) -> bool:
        """Pause the agent (monitors continue but no actions taken)."""
        if self.state.get_status() != AgentStatus.RUNNING:
            return False
        self.state.set_status(AgentStatus.PAUSED)
        logger.info("Agent paused")
        return True

    async def resume(self) -> bool:
        """Resume a paused agent."""
        if self.state.get_status() != AgentStatus.PAUSED:
            return False
        self.state.set_status(AgentStatus.RUNNING)
        logger.info("Agent resumed")
        return True

    # ============================================================
    # Public Interface
    # ============================================================

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics."""
        metrics = self.state.get_metrics()
        return {
            'status': self.state.get_status().value,
            'started_at': self.state.get_started_at().isoformat() if self.state.get_started_at() else None,
            'uptime_seconds': metrics.uptime_seconds,
            'metrics': metrics.to_dict(),
        }

    def get_health(self) -> Dict[str, Any]:
        """Get agent health check."""
        status = self.state.get_status()
        return {
            'healthy': status in (AgentStatus.RUNNING, AgentStatus.PAUSED),
            'status': status.value,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent agent actions."""
        actions = self.state.get_recent_actions(limit)
        return [a.to_dict() for a in actions]

    def get_pending_hitl(self) -> List[Dict[str, Any]]:
        """Get pending HITL approval requests."""
        requests = self.state.get_pending_hitl_requests()
        return [r.to_dict() for r in requests]

    def approve_hitl(self, request_id: str, user_id: str, notes: Optional[str] = None) -> bool:
        """
        Approve a HITL request.

        Args:
            request_id: HITL request ID
            user_id: User approving the request
            notes: Optional approval notes

        Returns:
            True if approved successfully
        """
        request = self.state.update_hitl_request(request_id, 'approved', user_id, notes)
        if request:
            # Execute the approved action
            asyncio.create_task(self._execute_approved_action(request))
            return True
        return False

    def reject_hitl(self, request_id: str, user_id: str, notes: Optional[str] = None) -> bool:
        """
        Reject a HITL request.

        Args:
            request_id: HITL request ID
            user_id: User rejecting the request
            notes: Optional rejection notes

        Returns:
            True if rejected successfully
        """
        request = self.state.update_hitl_request(request_id, 'rejected', user_id, notes)
        return request is not None

    def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        """Get the most recent intelligence briefing."""
        return self.state.get_latest_briefing()

    async def generate_briefing(self) -> Dict[str, Any]:
        """Force generation of a new briefing."""
        return await self._generate_intelligence_briefing()

    # ============================================================
    # Manual Processing Methods (for API integration)
    # ============================================================

    async def process_e14_form(self, form_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an E-14 form and take appropriate actions.

        Args:
            form_data: E-14 form data (E14PayloadV2 format)

        Returns:
            List of actions taken
        """
        if self.state.get_status() not in (AgentStatus.RUNNING,):
            logger.warning("Agent not running, skipping E-14 processing")
            return []

        start_time = datetime.utcnow()
        decisions = self.decision_engine.evaluate_e14_form(form_data)

        actions_taken = []
        for decision in decisions:
            result = await self._execute_decision(decision)
            actions_taken.append(result)

        # Update metrics
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        if decisions:
            self.state.increment_metric('anomalies_detected_total', len(decisions))
            self.state.increment_metric('anomalies_detected_last_hour')

        logger.info(f"Processed E-14 form: {len(decisions)} decisions in {elapsed_ms:.0f}ms")
        return actions_taken

    async def process_incident_update(self, incident: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an incident update and take appropriate actions.

        Args:
            incident: Incident data

        Returns:
            List of actions taken
        """
        if self.state.get_status() not in (AgentStatus.RUNNING,):
            return []

        decisions = self.decision_engine.evaluate_incident(incident)

        actions_taken = []
        for decision in decisions:
            result = await self._execute_decision(decision)
            actions_taken.append(result)

        return actions_taken

    # ============================================================
    # Monitoring Loops
    # ============================================================

    async def _e14_monitoring_loop(self):
        """Monitor for new E-14 forms."""
        logger.info("Starting E-14 monitoring loop")
        while self._running:
            try:
                if self.state.get_status() == AgentStatus.RUNNING:
                    await self._poll_e14_forms()
                await asyncio.sleep(self.config.E14_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in E-14 monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _incident_monitoring_loop(self):
        """Monitor incidents for SLA and escalation."""
        logger.info("Starting incident monitoring loop")
        while self._running:
            try:
                if self.state.get_status() == AgentStatus.RUNNING:
                    await self._poll_incidents()
                await asyncio.sleep(self.config.INCIDENT_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in incident monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _deadline_monitoring_loop(self):
        """Monitor legal deadlines."""
        logger.info("Starting deadline monitoring loop")
        while self._running:
            try:
                if self.state.get_status() == AgentStatus.RUNNING:
                    await self._poll_deadlines()
                await asyncio.sleep(self.config.DEADLINE_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in deadline monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _kpi_monitoring_loop(self):
        """Update KPI metrics."""
        logger.info("Starting KPI monitoring loop")
        while self._running:
            try:
                self.state.update_uptime()
                await asyncio.sleep(self.config.KPI_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in KPI monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _briefing_loop(self):
        """Generate periodic intelligence briefings."""
        logger.info("Starting briefing loop")
        while self._running:
            try:
                if self.state.get_status() == AgentStatus.RUNNING:
                    last_briefing = self.state.get_latest_briefing()
                    last_time = None
                    if last_briefing and last_briefing.get('stored_at'):
                        last_time = datetime.fromisoformat(last_briefing['stored_at'])

                    if self.decision_engine.should_generate_briefing(last_time):
                        await self._generate_intelligence_briefing()

                # Sleep for 5 minutes between checks
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in briefing loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    # ============================================================
    # Polling Methods
    # ============================================================

    async def _poll_e14_forms(self):
        """Poll for new E-14 forms to process."""
        from services.agent.e14_data_service import E14DataService
        from services.agent.agent_store import mark_processed

        data_service = E14DataService()
        forms = data_service.get_unprocessed_forms(limit=100)
        if not forms:
            return

        for form in forms:
            if self.state.get_status() != AgentStatus.RUNNING:
                break
            actions = await self.process_e14_form(form)
            incidents_created = len([a for a in actions if a.get('action') == 'create_incident' or a.get('created')])
            mark_processed(form.get('id', 0), incidents_created=incidents_created)

    async def _poll_incidents(self):
        """Poll incidents for SLA monitoring."""
        # This would integrate with the incidents service
        # For now, placeholder - would call incident_monitor
        pass

    async def _poll_deadlines(self):
        """Poll for approaching legal deadlines."""
        # This would integrate with the deadline tracker
        # For now, placeholder
        pass

    # ============================================================
    # Decision Execution
    # ============================================================

    async def _execute_decision(self, decision: Decision) -> Dict[str, Any]:
        """
        Execute a decision, creating HITL request if needed.

        Args:
            decision: Decision to execute

        Returns:
            Action result
        """
        action_id = str(uuid.uuid4())

        # Record the action
        action_record = ActionRecord(
            action_id=action_id,
            action_type=decision.action.value,
            timestamp=datetime.utcnow().isoformat(),
            trigger_rule=decision.rule_name,
            target_id=decision.context.get('incident_id') or decision.context.get('mesa_id'),
            target_type='incident' if 'incident_id' in decision.context else 'e14_form',
            details=decision.context,
            hitl_required=decision.hitl_required != HITLRequirement.AUTOMATIC,
        )

        # Check if HITL is required
        if decision.hitl_required != HITLRequirement.AUTOMATIC:
            # Create HITL request
            hitl_request = HITLRequest(
                request_id=action_id,
                action_type=decision.action.value,
                created_at=datetime.utcnow().isoformat(),
                expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
                priority=decision.priority,
                title=f"{decision.action.value}: {decision.rule_name}",
                description=decision.rationale,
                context=decision.context,
                recommended_action=decision.action.value,
            )
            self.state.add_hitl_request(hitl_request)
            action_record.hitl_status = 'pending'
            self.state.record_action(action_record)

            return {
                'action_id': action_id,
                'action': decision.action.value,
                'status': 'pending_approval',
                'hitl_request_id': action_id,
            }

        # Execute automatic action
        try:
            result = await self._execute_action(decision)
            action_record.result = 'success'
            action_record.details['result'] = result
        except Exception as e:
            logger.error(f"Error executing action {decision.action}: {e}", exc_info=True)
            action_record.result = 'error'
            action_record.error = str(e)
            result = {'error': str(e)}

        self.state.record_action(action_record)

        return {
            'action_id': action_id,
            'action': decision.action.value,
            'status': action_record.result,
            'result': result,
        }

    async def _execute_action(self, decision: Decision) -> Dict[str, Any]:
        """
        Execute an automatic action.

        Args:
            decision: Decision containing action and context

        Returns:
            Action result
        """
        action = decision.action
        context = decision.context

        if action == AgentAction.CREATE_INCIDENT:
            return await self._create_incident(context)
        elif action == AgentAction.DISPATCH_SLA_ALERT:
            return await self._dispatch_alert(context)
        elif action == AgentAction.CLASSIFY_CPACA:
            return await self._classify_cpaca(context)
        elif action == AgentAction.UPDATE_RISK_SCORES:
            return await self._update_risk_scores(context)
        elif action == AgentAction.GENERATE_HOURLY_BRIEF:
            return await self._generate_intelligence_briefing()
        else:
            logger.warning(f"Unhandled action type: {action}")
            return {'status': 'not_implemented'}

    async def _execute_approved_action(self, request: HITLRequest) -> Dict[str, Any]:
        """Execute an action that was approved via HITL."""
        decision = Decision(
            action=AgentAction(request.action_type),
            hitl_required=HITLRequirement.AUTOMATIC,  # Already approved
            priority=request.priority,
            rule_name=request.title,
            context=request.context,
            rationale=request.description,
        )
        return await self._execute_action(decision)

    # ============================================================
    # Actuator Methods
    # ============================================================

    async def _create_incident(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create an incident from detected anomaly."""
        incident_type = context.get('incident_type', 'UNKNOWN')
        mesa_id = context.get('mesa_id', '')

        # Parse mesa_id for geographic info
        parts = mesa_id.split('-') if mesa_id else []
        dept_code = parts[0] if len(parts) > 0 else '00'
        muni_code = parts[1] if len(parts) > 1 else '000'

        incident_data = {
            'incident_type': incident_type,
            'mesa_id': mesa_id,
            'dept_code': dept_code,
            'muni_code': muni_code,
            'description': self._build_incident_description(context),
            'ocr_confidence': context.get('ocr_confidence'),
            'delta_value': context.get('delta') or context.get('anomaly_count'),
            'evidence': context,
        }

        logger.info(f"Creating incident: {incident_type} for {mesa_id}")
        try:
            from services.incident_store import create_incident as store_create_incident
            incident = store_create_incident(incident_data, dedupe=True)
            self.state.increment_metric('incidents_auto_created')
            return {'created': True, 'incident': incident}
        except Exception as e:
            logger.error(f"Error creating incident: {e}", exc_info=True)
            return {'created': False, 'error': str(e)}

    async def _dispatch_alert(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an SLA or deadline alert."""
        alert_type = context.get('deadline_type') or 'SLA'
        incident_id = context.get('incident_id')

        logger.info(f"Dispatching {alert_type} alert for incident {incident_id}")

        # In a real implementation, this would send WebSocket/push notifications
        return {
            'dispatched': True,
            'alert_type': alert_type,
            'incident_id': incident_id,
        }

    async def _classify_cpaca(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify incident by CPACA article."""
        mesa_id = context.get('mesa_id')

        # CPACA classification logic would go here
        # For now, return a placeholder
        classification = {
            'article': 223,  # Default to Art. 223 (electoral irregularities)
            'deadline_hours': 48,
            'action_required': 'REVIEW',
        }

        logger.info(f"Classified {mesa_id} under Art. {classification['article']}")
        self.state.increment_metric('cpaca_classifications_total')

        return {
            'classified': True,
            'mesa_id': mesa_id,
            'cpaca_article': classification['article'],
        }

    async def _update_risk_scores(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update risk scores for a municipality."""
        municipality_code = context.get('municipality_code')
        risk_level = context.get('risk_level', 'MEDIUM')

        logger.info(f"Updating risk score for {municipality_code} to {risk_level}")

        return {
            'updated': True,
            'municipality_code': municipality_code,
            'risk_level': risk_level,
        }

    async def _generate_intelligence_briefing(self) -> Dict[str, Any]:
        """Generate an intelligence briefing using LLM."""
        start_time = datetime.utcnow()

        # Gather data for briefing
        metrics = self.state.get_metrics()
        recent_actions = self.state.get_recent_actions(20)
        pending_hitl = self.state.get_pending_hitl_requests()

        briefing_data = {
            'generated_at': start_time.isoformat(),
            'period': 'last_hour',
            'metrics_summary': {
                'anomalies_detected': metrics.anomalies_detected_last_hour,
                'incidents_created': metrics.incidents_auto_created,
                'alerts_sent': metrics.deadline_alerts_sent,
                'hitl_pending': len(pending_hitl),
            },
            'recent_actions': [a.to_dict() for a in recent_actions[-10:]],
            'pending_approvals': len(pending_hitl),
        }

        # If LLM is enabled, generate narrative summary
        if self.config.LLM_BRIEFINGS_ENABLED and self._openai_service:
            try:
                narrative = await self._generate_briefing_narrative(briefing_data)
                briefing_data['narrative'] = narrative
            except Exception as e:
                logger.error(f"Error generating briefing narrative: {e}")
                briefing_data['narrative'] = "Briefing narrative unavailable."
        else:
            briefing_data['narrative'] = self._generate_simple_narrative(briefing_data)

        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        briefing_data['generation_latency_seconds'] = latency

        # Store briefing
        self.state.store_briefing(briefing_data)
        self.state.update_metrics(briefing_latency_seconds=latency)

        logger.info(f"Generated intelligence briefing in {latency:.2f}s")
        return briefing_data

    async def _generate_briefing_narrative(self, data: Dict[str, Any]) -> str:
        """Generate narrative summary using LLM."""
        if not self._openai_service:
            return self._generate_simple_narrative(data)

        prompt = f"""Genera un briefing ejecutivo de inteligencia electoral en español.

Datos del último período:
- Anomalías detectadas: {data['metrics_summary']['anomalies_detected']}
- Incidentes creados: {data['metrics_summary']['incidents_created']}
- Alertas enviadas: {data['metrics_summary']['alerts_sent']}
- Aprobaciones pendientes: {data['pending_approvals']}

Últimas acciones: {len(data['recent_actions'])} acciones registradas

Genera un resumen ejecutivo de 2-3 párrafos para el War Room."""

        try:
            response = self._openai_service.chat(prompt)
            return response
        except Exception as e:
            logger.error(f"LLM briefing generation failed: {e}")
            return self._generate_simple_narrative(data)

    def _generate_simple_narrative(self, data: Dict[str, Any]) -> str:
        """Generate simple narrative without LLM."""
        metrics = data['metrics_summary']
        return (
            f"Briefing de Inteligencia Electoral - {data['generated_at']}\n\n"
            f"En el último período se detectaron {metrics['anomalies_detected']} anomalías, "
            f"se crearon {metrics['incidents_created']} incidentes automáticamente, "
            f"y se enviaron {metrics['alerts_sent']} alertas de deadline.\n\n"
            f"Hay {metrics['hitl_pending']} solicitudes pendientes de aprobación humana."
        )

    def _build_incident_description(self, context: Dict[str, Any]) -> str:
        """Build incident description from context."""
        incident_type = context.get('incident_type', 'UNKNOWN')

        if incident_type == 'ARITHMETIC_FAIL':
            delta = context.get('delta', 0)
            return f"Error aritmético detectado: diferencia de {delta} votos"
        elif incident_type == 'OCR_LOW_CONF':
            conf = context.get('ocr_confidence', 0)
            fields = context.get('low_confidence_fields', [])
            return f"Confianza OCR baja ({conf:.0%}) en campos: {', '.join(fields[:3])}"
        elif incident_type == 'GEOGRAPHIC_CLUSTER':
            count = context.get('anomaly_count', 0)
            return f"Cluster geográfico: {count} anomalías en la zona"
        else:
            return f"Anomalía detectada: {incident_type}"

    # ============================================================
    # Initialization
    # ============================================================

    async def _initialize_monitors(self):
        """Initialize monitor components."""
        # Monitors are lazy-loaded when needed
        # This is a placeholder for any initialization logic
        logger.info("Monitors initialized")
