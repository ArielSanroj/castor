"""
E-14 Form Monitor.
Polls for new E-14 forms and detects anomalies.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class E14Monitor:
    """
    Monitors E-14 forms for anomalies and validation failures.
    Polls the E-14 data source at configured intervals.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        on_anomaly: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the E-14 monitor.

        Args:
            config: Agent configuration
            on_anomaly: Callback when anomaly is detected
        """
        self.config = config or get_agent_config()
        self._on_anomaly = on_anomaly
        self._last_poll_time: Optional[datetime] = None
        self._processed_ids: set = set()
        self._max_processed_cache = 10000

        logger.info("E14Monitor initialized")

    async def poll(self, e14_data_service=None) -> List[Dict[str, Any]]:
        """
        Poll for new E-14 forms and check for anomalies.

        Args:
            e14_data_service: Service to fetch E-14 data

        Returns:
            List of detected anomalies
        """
        anomalies = []
        self._last_poll_time = datetime.utcnow()

        if not e14_data_service:
            logger.debug("No E-14 data service provided, skipping poll")
            return anomalies

        try:
            # Fetch recent E-14 forms
            since = datetime.utcnow() - timedelta(minutes=5)
            forms = await self._fetch_recent_forms(e14_data_service, since)

            for form in forms:
                form_id = form.get('extraction_id') or form.get('id')

                # Skip already processed
                if form_id in self._processed_ids:
                    continue

                # Check for anomalies
                form_anomalies = self._detect_anomalies(form)
                if form_anomalies:
                    anomalies.extend(form_anomalies)
                    for anomaly in form_anomalies:
                        if self._on_anomaly:
                            self._on_anomaly(anomaly)

                self._mark_processed(form_id)

            logger.debug(f"E14Monitor poll complete: {len(forms)} forms, {len(anomalies)} anomalies")

        except Exception as e:
            logger.error(f"Error polling E-14 forms: {e}", exc_info=True)

        return anomalies

    def check_form(self, form_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check a single E-14 form for anomalies.

        Args:
            form_data: E-14 form data (E14PayloadV2 format)

        Returns:
            List of detected anomalies
        """
        return self._detect_anomalies(form_data)

    def _detect_anomalies(self, form: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in an E-14 form.

        Args:
            form: E-14 form data

        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        header = form.get('document_header_extracted', {})
        mesa_id = self._get_mesa_id(header)

        # Check validations
        for validation in form.get('validations', []):
            if not validation.get('passed'):
                severity = validation.get('severity', 'MEDIUM')
                anomaly = {
                    'type': 'VALIDATION_FAILURE',
                    'rule_key': validation.get('rule_key'),
                    'severity': severity,
                    'mesa_id': mesa_id,
                    'details': validation.get('details', {}),
                    'detected_at': datetime.utcnow().isoformat(),
                }

                # Categorize specific anomalies
                rule_key = validation.get('rule_key', '')
                if 'ARITHMETIC' in rule_key or 'SUM' in rule_key:
                    anomaly['type'] = 'ARITHMETIC_MISMATCH'
                    details = validation.get('details', {})
                    anomaly['delta'] = abs(details.get('expected', 0) - details.get('actual', 0))
                elif 'E11' in rule_key or 'SUFRAGANTES' in rule_key:
                    anomaly['type'] = 'E11_VS_URNA'

                anomalies.append(anomaly)

        # Check OCR confidence
        ocr_anomaly = self._check_ocr_confidence(form, mesa_id)
        if ocr_anomaly:
            anomalies.append(ocr_anomaly)

        return anomalies

    def _check_ocr_confidence(self, form: Dict[str, Any], mesa_id: str) -> Optional[Dict[str, Any]]:
        """Check for low OCR confidence."""
        ocr_fields = form.get('ocr_fields', [])
        if not ocr_fields:
            return None

        low_confidence_fields = []
        total_confidence = 0.0
        count = 0

        for field in ocr_fields:
            confidence = field.get('confidence', 1.0)
            total_confidence += confidence
            count += 1

            if confidence < self.config.OCR_CONFIDENCE_THRESHOLD:
                low_confidence_fields.append({
                    'field_key': field.get('field_key'),
                    'confidence': confidence,
                    'needs_review': field.get('needs_review', True),
                })

        avg_confidence = total_confidence / count if count > 0 else 1.0

        if avg_confidence < self.config.OCR_CONFIDENCE_THRESHOLD or len(low_confidence_fields) > 3:
            return {
                'type': 'OCR_LOW_CONFIDENCE',
                'severity': 'MEDIUM' if avg_confidence > 0.5 else 'HIGH',
                'mesa_id': mesa_id,
                'avg_confidence': avg_confidence,
                'low_confidence_fields': low_confidence_fields,
                'detected_at': datetime.utcnow().isoformat(),
            }

        return None

    def _get_mesa_id(self, header: Dict[str, Any]) -> str:
        """Extract mesa_id from header."""
        if 'mesa_id' in header:
            return header['mesa_id']

        # Build from components
        dept = header.get('dept_code', '00')
        muni = header.get('muni_code', '000')
        zone = header.get('zone_code', '00')
        station = header.get('station_code', '00')
        table = header.get('table_number', 0)

        return f"{dept}-{muni}-{zone}-{station}-{table:03d}"

    def _mark_processed(self, form_id: str) -> None:
        """Mark a form as processed."""
        self._processed_ids.add(form_id)

        # Cleanup old entries
        if len(self._processed_ids) > self._max_processed_cache:
            # Remove oldest entries (convert to list, slice, convert back)
            self._processed_ids = set(list(self._processed_ids)[-self._max_processed_cache // 2:])

    async def _fetch_recent_forms(self, service, since: datetime) -> List[Dict[str, Any]]:
        """Fetch recent E-14 forms from service."""
        # This would integrate with the actual E-14 data service
        # For now, return empty list
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            'last_poll_time': self._last_poll_time.isoformat() if self._last_poll_time else None,
            'processed_count': len(self._processed_ids),
            'poll_interval_seconds': self.config.E14_POLL_INTERVAL,
        }
