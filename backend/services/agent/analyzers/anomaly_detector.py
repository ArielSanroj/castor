"""
Anomaly Detector.
Detects anomalies in electoral data using rule-based and statistical methods.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""
    ARITHMETIC_MISMATCH = "ARITHMETIC_MISMATCH"
    OCR_LOW_CONFIDENCE = "OCR_LOW_CONFIDENCE"
    E11_URNA_MISMATCH = "E11_URNA_MISMATCH"
    SIGNATURE_MISSING = "SIGNATURE_MISSING"
    STATISTICAL_OUTLIER = "STATISTICAL_OUTLIER"
    GEOGRAPHIC_CLUSTER = "GEOGRAPHIC_CLUSTER"
    TEMPORAL_ANOMALY = "TEMPORAL_ANOMALY"
    DUPLICATE_FORM = "DUPLICATE_FORM"
    IMPOSSIBLE_VALUE = "IMPOSSIBLE_VALUE"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class DetectedAnomaly:
    """A detected anomaly."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    mesa_id: str
    dept_code: str
    muni_code: str
    description: str
    detected_at: datetime
    confidence: float
    details: Dict[str, Any]
    affected_fields: List[str]
    suggested_action: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'anomaly_id': self.anomaly_id,
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.value,
            'mesa_id': self.mesa_id,
            'dept_code': self.dept_code,
            'muni_code': self.muni_code,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'confidence': self.confidence,
            'details': self.details,
            'affected_fields': self.affected_fields,
            'suggested_action': self.suggested_action,
        }


class AnomalyDetector:
    """
    Detects anomalies in electoral data.
    Uses rule-based checks and statistical analysis.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the anomaly detector.

        Args:
            config: Agent configuration
        """
        self.config = config or get_agent_config()
        self._anomaly_counter = 0

        # Statistical baselines (would be learned from historical data)
        self._baselines: Dict[str, Dict[str, float]] = {}

        logger.info("AnomalyDetector initialized")

    def analyze_e14(self, form_data: Dict[str, Any]) -> List[DetectedAnomaly]:
        """
        Analyze an E-14 form for anomalies.

        Args:
            form_data: E-14 form data

        Returns:
            List of detected anomalies
        """
        anomalies = []
        header = form_data.get('document_header_extracted', {})
        mesa_id = self._get_mesa_id(header)
        dept_code = header.get('dept_code', '00')
        muni_code = header.get('muni_code', '000')

        # Run all detection methods
        anomalies.extend(self._check_arithmetic(form_data, mesa_id, dept_code, muni_code))
        anomalies.extend(self._check_ocr_confidence(form_data, mesa_id, dept_code, muni_code))
        anomalies.extend(self._check_e11_urna(form_data, mesa_id, dept_code, muni_code))
        anomalies.extend(self._check_impossible_values(form_data, mesa_id, dept_code, muni_code))
        anomalies.extend(self._check_validation_failures(form_data, mesa_id, dept_code, muni_code))

        return anomalies

    def analyze_batch(self, forms: List[Dict[str, Any]]) -> Tuple[List[DetectedAnomaly], Dict[str, Any]]:
        """
        Analyze a batch of forms for anomalies including cross-form patterns.

        Args:
            forms: List of E-14 form data

        Returns:
            Tuple of (anomalies, batch_statistics)
        """
        all_anomalies = []
        stats = {
            'forms_analyzed': len(forms),
            'anomalies_found': 0,
            'by_type': {},
            'by_severity': {},
        }

        # Analyze each form
        for form in forms:
            form_anomalies = self.analyze_e14(form)
            all_anomalies.extend(form_anomalies)

        # Check for geographic clustering
        cluster_anomalies = self._detect_geographic_clusters(forms, all_anomalies)
        all_anomalies.extend(cluster_anomalies)

        # Update statistics
        stats['anomalies_found'] = len(all_anomalies)
        for anomaly in all_anomalies:
            atype = anomaly.anomaly_type.value
            severity = anomaly.severity.value
            stats['by_type'][atype] = stats['by_type'].get(atype, 0) + 1
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

        return all_anomalies, stats

    def _check_arithmetic(
        self,
        form_data: Dict[str, Any],
        mesa_id: str,
        dept_code: str,
        muni_code: str
    ) -> List[DetectedAnomaly]:
        """Check for arithmetic mismatches."""
        anomalies = []

        # Check validations for arithmetic failures
        for validation in form_data.get('validations', []):
            rule_key = validation.get('rule_key', '')
            if ('ARITHMETIC' in rule_key or 'SUM' in rule_key) and not validation.get('passed'):
                details = validation.get('details', {})
                expected = details.get('expected', 0)
                actual = details.get('actual', 0)
                delta = abs(expected - actual)

                if delta > self.config.ARITHMETIC_DELTA_THRESHOLD:
                    anomalies.append(self._create_anomaly(
                        anomaly_type=AnomalyType.ARITHMETIC_MISMATCH,
                        severity=AnomalySeverity.CRITICAL if delta > 10 else AnomalySeverity.HIGH,
                        mesa_id=mesa_id,
                        dept_code=dept_code,
                        muni_code=muni_code,
                        description=f"Suma aritmética no cuadra: esperado {expected}, actual {actual} (delta: {delta})",
                        confidence=1.0,
                        details={
                            'expected': expected,
                            'actual': actual,
                            'delta': delta,
                            'rule_key': rule_key,
                        },
                        affected_fields=['vote_totals'],
                        suggested_action='REVIEW_AND_RECOUNT',
                    ))

        return anomalies

    def _check_ocr_confidence(
        self,
        form_data: Dict[str, Any],
        mesa_id: str,
        dept_code: str,
        muni_code: str
    ) -> List[DetectedAnomaly]:
        """Check for low OCR confidence."""
        anomalies = []
        ocr_fields = form_data.get('ocr_fields', [])

        if not ocr_fields:
            return anomalies

        low_conf_fields = []
        total_confidence = 0.0

        for field in ocr_fields:
            confidence = field.get('confidence', 1.0)
            total_confidence += confidence

            if confidence < self.config.OCR_CONFIDENCE_THRESHOLD:
                low_conf_fields.append({
                    'field_key': field.get('field_key'),
                    'confidence': confidence,
                })

        avg_confidence = total_confidence / len(ocr_fields)

        if len(low_conf_fields) >= 3 or avg_confidence < self.config.OCR_CONFIDENCE_THRESHOLD:
            severity = AnomalySeverity.HIGH if avg_confidence < 0.5 else AnomalySeverity.MEDIUM
            anomalies.append(self._create_anomaly(
                anomaly_type=AnomalyType.OCR_LOW_CONFIDENCE,
                severity=severity,
                mesa_id=mesa_id,
                dept_code=dept_code,
                muni_code=muni_code,
                description=f"Confianza OCR baja: promedio {avg_confidence:.1%}, {len(low_conf_fields)} campos bajo umbral",
                confidence=1.0 - avg_confidence,
                details={
                    'avg_confidence': avg_confidence,
                    'low_confidence_fields': low_conf_fields,
                    'threshold': self.config.OCR_CONFIDENCE_THRESHOLD,
                },
                affected_fields=[f['field_key'] for f in low_conf_fields],
                suggested_action='MANUAL_REVIEW',
            ))

        return anomalies

    def _check_e11_urna(
        self,
        form_data: Dict[str, Any],
        mesa_id: str,
        dept_code: str,
        muni_code: str
    ) -> List[DetectedAnomaly]:
        """Check for E-11 vs urna mismatch."""
        anomalies = []

        for validation in form_data.get('validations', []):
            rule_key = validation.get('rule_key', '')
            if ('E11' in rule_key or 'SUFRAGANTES' in rule_key) and not validation.get('passed'):
                details = validation.get('details', {})
                e11_count = details.get('e11_count', 0)
                urna_count = details.get('urna_count', 0)
                delta = abs(e11_count - urna_count)

                if delta > 0:
                    anomalies.append(self._create_anomaly(
                        anomaly_type=AnomalyType.E11_URNA_MISMATCH,
                        severity=AnomalySeverity.HIGH if delta > 5 else AnomalySeverity.MEDIUM,
                        mesa_id=mesa_id,
                        dept_code=dept_code,
                        muni_code=muni_code,
                        description=f"Sufragantes E-11 ({e11_count}) ≠ Votos en urna ({urna_count})",
                        confidence=1.0,
                        details={
                            'e11_count': e11_count,
                            'urna_count': urna_count,
                            'delta': delta,
                        },
                        affected_fields=['total_sufragantes_e11', 'total_votos_urna'],
                        suggested_action='INVESTIGATE_DISCREPANCY',
                    ))

        return anomalies

    def _check_impossible_values(
        self,
        form_data: Dict[str, Any],
        mesa_id: str,
        dept_code: str,
        muni_code: str
    ) -> List[DetectedAnomaly]:
        """Check for impossible values."""
        anomalies = []

        # Check for negative values or impossibly high numbers
        for field in form_data.get('ocr_fields', []):
            value = field.get('value_int')
            if value is not None:
                field_key = field.get('field_key', '')

                # Negative votes
                if value < 0:
                    anomalies.append(self._create_anomaly(
                        anomaly_type=AnomalyType.IMPOSSIBLE_VALUE,
                        severity=AnomalySeverity.CRITICAL,
                        mesa_id=mesa_id,
                        dept_code=dept_code,
                        muni_code=muni_code,
                        description=f"Valor negativo detectado en {field_key}: {value}",
                        confidence=1.0,
                        details={'field_key': field_key, 'value': value},
                        affected_fields=[field_key],
                        suggested_action='MANUAL_CORRECTION',
                    ))

                # Impossibly high vote count (>1000 per mesa is unusual)
                if 'CANDIDATE' in field_key or 'VOTES' in field_key:
                    if value > 1000:
                        anomalies.append(self._create_anomaly(
                            anomaly_type=AnomalyType.IMPOSSIBLE_VALUE,
                            severity=AnomalySeverity.HIGH,
                            mesa_id=mesa_id,
                            dept_code=dept_code,
                            muni_code=muni_code,
                            description=f"Valor inusualmente alto en {field_key}: {value}",
                            confidence=0.8,
                            details={'field_key': field_key, 'value': value},
                            affected_fields=[field_key],
                            suggested_action='VERIFY_VALUE',
                        ))

        return anomalies

    def _check_validation_failures(
        self,
        form_data: Dict[str, Any],
        mesa_id: str,
        dept_code: str,
        muni_code: str
    ) -> List[DetectedAnomaly]:
        """Check for general validation failures not covered by specific checks."""
        anomalies = []

        for validation in form_data.get('validations', []):
            if validation.get('passed'):
                continue

            rule_key = validation.get('rule_key', '')
            # Skip rules already handled
            if any(k in rule_key for k in ['ARITHMETIC', 'SUM', 'E11', 'SUFRAGANTES', 'OCR']):
                continue

            severity_map = {
                'CRITICAL': AnomalySeverity.CRITICAL,
                'HIGH': AnomalySeverity.HIGH,
                'MEDIUM': AnomalySeverity.MEDIUM,
                'LOW': AnomalySeverity.LOW,
            }
            severity = severity_map.get(
                validation.get('severity', 'MEDIUM'),
                AnomalySeverity.MEDIUM
            )

            anomalies.append(self._create_anomaly(
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,  # Generic type for other failures
                severity=severity,
                mesa_id=mesa_id,
                dept_code=dept_code,
                muni_code=muni_code,
                description=f"Validación fallida: {rule_key}",
                confidence=1.0,
                details=validation.get('details', {}),
                affected_fields=[],
                suggested_action='REVIEW_VALIDATION',
            ))

        return anomalies

    def _detect_geographic_clusters(
        self,
        forms: List[Dict[str, Any]],
        existing_anomalies: List[DetectedAnomaly]
    ) -> List[DetectedAnomaly]:
        """Detect geographic clustering of anomalies."""
        anomalies = []

        # Group anomalies by municipality
        by_municipality: Dict[str, List[DetectedAnomaly]] = {}
        for anomaly in existing_anomalies:
            muni = anomaly.muni_code
            if muni not in by_municipality:
                by_municipality[muni] = []
            by_municipality[muni].append(anomaly)

        # Check for clusters
        for muni_code, muni_anomalies in by_municipality.items():
            if len(muni_anomalies) >= self.config.GEOGRAPHIC_CLUSTER_THRESHOLD:
                # Get department code from first anomaly
                dept_code = muni_anomalies[0].dept_code

                anomalies.append(self._create_anomaly(
                    anomaly_type=AnomalyType.GEOGRAPHIC_CLUSTER,
                    severity=AnomalySeverity.CRITICAL,
                    mesa_id=f"CLUSTER-{muni_code}",
                    dept_code=dept_code,
                    muni_code=muni_code,
                    description=f"Cluster geográfico: {len(muni_anomalies)} anomalías en municipio {muni_code}",
                    confidence=0.9,
                    details={
                        'anomaly_count': len(muni_anomalies),
                        'anomaly_types': list(set(a.anomaly_type.value for a in muni_anomalies)),
                        'affected_mesas': [a.mesa_id for a in muni_anomalies],
                    },
                    affected_fields=[],
                    suggested_action='INVESTIGATE_MUNICIPALITY',
                ))

        return anomalies

    def _create_anomaly(
        self,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        mesa_id: str,
        dept_code: str,
        muni_code: str,
        description: str,
        confidence: float,
        details: Dict[str, Any],
        affected_fields: List[str],
        suggested_action: str
    ) -> DetectedAnomaly:
        """Create an anomaly record."""
        self._anomaly_counter += 1
        return DetectedAnomaly(
            anomaly_id=f"ANOM-{self._anomaly_counter:08d}",
            anomaly_type=anomaly_type,
            severity=severity,
            mesa_id=mesa_id,
            dept_code=dept_code,
            muni_code=muni_code,
            description=description,
            detected_at=datetime.utcnow(),
            confidence=confidence,
            details=details,
            affected_fields=affected_fields,
            suggested_action=suggested_action,
        )

    def _get_mesa_id(self, header: Dict[str, Any]) -> str:
        """Extract mesa_id from header."""
        if 'mesa_id' in header:
            return header['mesa_id']

        dept = header.get('dept_code', '00')
        muni = header.get('muni_code', '000')
        zone = header.get('zone_code', '00')
        station = header.get('station_code', '00')
        table = header.get('table_number', 0)

        return f"{dept}-{muni}-{zone}-{station}-{table:03d}"

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            'anomalies_generated': self._anomaly_counter,
            'thresholds': {
                'ocr_confidence': self.config.OCR_CONFIDENCE_THRESHOLD,
                'arithmetic_delta': self.config.ARITHMETIC_DELTA_THRESHOLD,
                'geographic_cluster': self.config.GEOGRAPHIC_CLUSTER_THRESHOLD,
            },
        }
