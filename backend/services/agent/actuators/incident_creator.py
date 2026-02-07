"""
Incident Creator.
Creates incidents from detected anomalies.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx

from services.agent.config import AgentConfig, get_agent_config
from app.schemas.incidents import IncidentType, IncidentSeverity, INCIDENT_CONFIG

logger = logging.getLogger(__name__)


class IncidentCreator:
    """
    Creates incidents in the incident management system.
    """

    # Mapping from anomaly types to incident types
    ANOMALY_TO_INCIDENT_TYPE = {
        'ARITHMETIC_MISMATCH': IncidentType.ARITHMETIC_FAIL,
        'OCR_LOW_CONFIDENCE': IncidentType.OCR_LOW_CONF,
        'E11_URNA_MISMATCH': IncidentType.E11_VS_URNA,
        'GEOGRAPHIC_CLUSTER': IncidentType.SOURCE_MISMATCH,  # Closest match
        'VALIDATION_FAILURE': IncidentType.ARITHMETIC_FAIL,
        'IMPOSSIBLE_VALUE': IncidentType.ARITHMETIC_FAIL,
    }

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        api_base_url: str = "http://localhost:5001"
    ):
        """
        Initialize the incident creator.

        Args:
            config: Agent configuration
            api_base_url: Base URL for the API
        """
        self.config = config or get_agent_config()
        self._api_base_url = api_base_url
        self._incidents_created = 0
        self._last_created_ids: List[int] = []

        logger.info("IncidentCreator initialized")

    async def create_from_anomaly(
        self,
        anomaly: Dict[str, Any],
        source: str = "AGENT"
    ) -> Dict[str, Any]:
        """
        Create an incident from a detected anomaly.

        Args:
            anomaly: Anomaly data
            source: Source identifier

        Returns:
            Created incident data or error
        """
        try:
            # Map anomaly to incident type
            anomaly_type = anomaly.get('type', 'UNKNOWN')
            incident_type = self.ANOMALY_TO_INCIDENT_TYPE.get(
                anomaly_type,
                IncidentType.ARITHMETIC_FAIL
            )

            # Determine severity
            severity = self._determine_severity(anomaly)

            # Build incident data
            incident_data = {
                'incident_type': incident_type.value,
                'severity': severity.value,
                'mesa_id': anomaly.get('mesa_id', ''),
                'dept_code': anomaly.get('dept_code', '00'),
                'dept_name': anomaly.get('dept_name'),
                'muni_code': anomaly.get('muni_code'),
                'muni_name': anomaly.get('muni_name'),
                'description': self._build_description(anomaly),
                'ocr_confidence': anomaly.get('avg_confidence') or anomaly.get('confidence'),
                'delta_value': anomaly.get('delta'),
                'evidence': {
                    'source': source,
                    'anomaly_id': anomaly.get('anomaly_id'),
                    'anomaly_type': anomaly_type,
                    'details': anomaly.get('details', {}),
                    'detected_at': anomaly.get('detected_at'),
                },
            }

            # Create incident via API
            result = await self._create_incident_api(incident_data)

            if result.get('success'):
                self._incidents_created += 1
                incident_id = result.get('incident', {}).get('id')
                if incident_id:
                    self._last_created_ids.append(incident_id)
                    # Keep only last 100
                    self._last_created_ids = self._last_created_ids[-100:]

                logger.info(
                    f"Created incident {incident_id} from anomaly {anomaly.get('anomaly_id')}"
                )
            else:
                logger.warning(f"Failed to create incident: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error creating incident from anomaly: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def create_from_decision(
        self,
        decision_context: Dict[str, Any],
        source: str = "AGENT"
    ) -> Dict[str, Any]:
        """
        Create an incident from a decision context.

        Args:
            decision_context: Context from decision engine
            source: Source identifier

        Returns:
            Created incident data or error
        """
        try:
            incident_type = decision_context.get('incident_type', 'ARITHMETIC_FAIL')
            mesa_id = decision_context.get('mesa_id', '')

            # Parse mesa_id for geographic info
            parts = mesa_id.split('-') if mesa_id else []
            dept_code = parts[0] if len(parts) > 0 else '00'
            muni_code = parts[1] if len(parts) > 1 else '000'

            # Get incident config
            try:
                inc_type = IncidentType(incident_type)
                config = INCIDENT_CONFIG.get(inc_type, {"default_severity": IncidentSeverity.P2})
                severity = config.get('default_severity', IncidentSeverity.P2)
            except ValueError:
                inc_type = IncidentType.ARITHMETIC_FAIL
                severity = IncidentSeverity.P1

            incident_data = {
                'incident_type': inc_type.value,
                'severity': severity.value,
                'mesa_id': mesa_id,
                'dept_code': dept_code,
                'muni_code': muni_code,
                'description': decision_context.get('description') or self._build_description_from_context(decision_context),
                'ocr_confidence': decision_context.get('ocr_confidence'),
                'delta_value': decision_context.get('delta') or decision_context.get('anomaly_count'),
                'evidence': {
                    'source': source,
                    'context': decision_context,
                },
            }

            return await self._create_incident_api(incident_data)

        except Exception as e:
            logger.error(f"Error creating incident from decision: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def create_batch(
        self,
        anomalies: List[Dict[str, Any]],
        source: str = "AGENT_BATCH"
    ) -> Dict[str, Any]:
        """
        Create incidents from a batch of anomalies.

        Args:
            anomalies: List of anomalies
            source: Source identifier

        Returns:
            Batch creation result
        """
        results = {
            'total': len(anomalies),
            'created': 0,
            'failed': 0,
            'incidents': [],
            'errors': [],
        }

        for anomaly in anomalies:
            result = await self.create_from_anomaly(anomaly, source)
            if result.get('success'):
                results['created'] += 1
                results['incidents'].append(result.get('incident'))
            else:
                results['failed'] += 1
                results['errors'].append({
                    'anomaly_id': anomaly.get('anomaly_id'),
                    'error': result.get('error'),
                })

        return results

    def _determine_severity(self, anomaly: Dict[str, Any]) -> IncidentSeverity:
        """Determine severity based on anomaly characteristics."""
        severity_str = anomaly.get('severity', 'MEDIUM')

        severity_map = {
            'CRITICAL': IncidentSeverity.P0,
            'HIGH': IncidentSeverity.P1,
            'MEDIUM': IncidentSeverity.P2,
            'LOW': IncidentSeverity.P3,
            'INFO': IncidentSeverity.P3,
        }

        severity = severity_map.get(severity_str, IncidentSeverity.P2)

        # Upgrade severity based on delta
        delta = anomaly.get('delta', 0)
        if delta and delta > 50:
            if severity == IncidentSeverity.P2:
                severity = IncidentSeverity.P1
            elif severity == IncidentSeverity.P1:
                severity = IncidentSeverity.P0

        return severity

    def _build_description(self, anomaly: Dict[str, Any]) -> str:
        """Build incident description from anomaly."""
        anomaly_type = anomaly.get('type', 'UNKNOWN')
        description = anomaly.get('description', '')

        if description:
            return description

        # Build from type
        if anomaly_type == 'ARITHMETIC_MISMATCH':
            delta = anomaly.get('delta', 0)
            expected = anomaly.get('details', {}).get('expected', 0)
            actual = anomaly.get('details', {}).get('actual', 0)
            return f"Error aritmético: esperado {expected}, actual {actual} (delta: {delta})"

        elif anomaly_type == 'OCR_LOW_CONFIDENCE':
            conf = anomaly.get('avg_confidence', 0)
            return f"Confianza OCR baja: {conf:.1%}"

        elif anomaly_type == 'E11_URNA_MISMATCH':
            details = anomaly.get('details', {})
            e11 = details.get('e11_count', 0)
            urna = details.get('urna_count', 0)
            return f"Sufragantes E-11 ({e11}) ≠ Votos en urna ({urna})"

        elif anomaly_type == 'GEOGRAPHIC_CLUSTER':
            count = anomaly.get('details', {}).get('anomaly_count', 0)
            return f"Cluster geográfico: {count} anomalías en la zona"

        return f"Anomalía detectada: {anomaly_type}"

    def _build_description_from_context(self, context: Dict[str, Any]) -> str:
        """Build description from decision context."""
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

        return f"Incidente detectado: {incident_type}"

    async def _create_incident_api(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create incident via API call.

        Writes to the incident store for real persistence.
        """
        from services.incident_store import create_incident as store_create_incident
        incident = store_create_incident(incident_data, dedupe=True)
        return {'success': True, 'incident': incident}

    def get_stats(self) -> Dict[str, Any]:
        """Get creator statistics."""
        return {
            'incidents_created': self._incidents_created,
            'last_created_ids': self._last_created_ids[-10:],
        }
