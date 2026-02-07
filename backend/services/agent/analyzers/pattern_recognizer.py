"""
Pattern Recognizer.
Recognizes patterns across electoral data for intelligence insights.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns that can be recognized."""
    GEOGRAPHIC_CLUSTER = "GEOGRAPHIC_CLUSTER"
    TEMPORAL_SPIKE = "TEMPORAL_SPIKE"
    PARTY_ANOMALY = "PARTY_ANOMALY"
    SYSTEMATIC_ERROR = "SYSTEMATIC_ERROR"
    COORDINATION_SIGNAL = "COORDINATION_SIGNAL"
    OUTLIER_SEQUENCE = "OUTLIER_SEQUENCE"


@dataclass
class RecognizedPattern:
    """A recognized pattern in the data."""
    pattern_id: str
    pattern_type: PatternType
    description: str
    confidence: float
    affected_areas: List[str]
    affected_mesas: List[str]
    time_window: Tuple[datetime, datetime]
    evidence: List[Dict[str, Any]]
    significance: float  # 0.0 to 1.0
    recommended_action: str
    detected_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type.value,
            'description': self.description,
            'confidence': self.confidence,
            'affected_areas': self.affected_areas,
            'affected_mesas': self.affected_mesas,
            'time_window': [self.time_window[0].isoformat(), self.time_window[1].isoformat()],
            'evidence': self.evidence,
            'significance': self.significance,
            'recommended_action': self.recommended_action,
            'detected_at': self.detected_at.isoformat(),
        }


class PatternRecognizer:
    """
    Recognizes patterns in electoral data for intelligence purposes.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the pattern recognizer.

        Args:
            config: Agent configuration
        """
        self.config = config or get_agent_config()
        self._pattern_counter = 0

        # Data buffers for pattern detection
        self._anomaly_buffer: List[Dict[str, Any]] = []
        self._incident_buffer: List[Dict[str, Any]] = []
        self._form_buffer: List[Dict[str, Any]] = []

        # Detected patterns cache
        self._detected_patterns: Dict[str, RecognizedPattern] = {}

        # Configuration
        self._buffer_max_age_hours = 6
        self._buffer_max_size = 10000

        logger.info("PatternRecognizer initialized")

    def add_anomaly(self, anomaly: Dict[str, Any]) -> List[RecognizedPattern]:
        """
        Add an anomaly and check for new patterns.

        Args:
            anomaly: Anomaly data

        Returns:
            List of newly detected patterns
        """
        self._anomaly_buffer.append(anomaly)
        self._cleanup_buffer(self._anomaly_buffer, 'detected_at')
        return self._check_patterns()

    def add_incident(self, incident: Dict[str, Any]) -> List[RecognizedPattern]:
        """
        Add an incident and check for new patterns.

        Args:
            incident: Incident data

        Returns:
            List of newly detected patterns
        """
        self._incident_buffer.append(incident)
        self._cleanup_buffer(self._incident_buffer, 'created_at')
        return self._check_patterns()

    def add_form(self, form: Dict[str, Any]) -> List[RecognizedPattern]:
        """
        Add a form and check for new patterns.

        Args:
            form: E-14 form data

        Returns:
            List of newly detected patterns
        """
        self._form_buffer.append(form)
        self._cleanup_buffer(self._form_buffer, 'produced_at')
        return self._check_patterns()

    def analyze_batch(
        self,
        anomalies: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]],
        forms: Optional[List[Dict[str, Any]]] = None
    ) -> List[RecognizedPattern]:
        """
        Analyze a batch of data for patterns.

        Args:
            anomalies: List of anomalies
            incidents: List of incidents
            forms: Optional list of E-14 forms

        Returns:
            List of detected patterns
        """
        # Add to buffers
        self._anomaly_buffer.extend(anomalies)
        self._incident_buffer.extend(incidents)
        if forms:
            self._form_buffer.extend(forms)

        # Cleanup
        self._cleanup_buffer(self._anomaly_buffer, 'detected_at')
        self._cleanup_buffer(self._incident_buffer, 'created_at')
        self._cleanup_buffer(self._form_buffer, 'produced_at')

        # Detect patterns
        return self._check_patterns()

    def _check_patterns(self) -> List[RecognizedPattern]:
        """Run all pattern detection algorithms."""
        new_patterns = []

        # Check geographic clustering
        geo_patterns = self._detect_geographic_clusters()
        new_patterns.extend(geo_patterns)

        # Check temporal spikes
        temporal_patterns = self._detect_temporal_spikes()
        new_patterns.extend(temporal_patterns)

        # Check systematic errors
        systematic_patterns = self._detect_systematic_errors()
        new_patterns.extend(systematic_patterns)

        # Check coordination signals
        coordination_patterns = self._detect_coordination_signals()
        new_patterns.extend(coordination_patterns)

        return new_patterns

    def _detect_geographic_clusters(self) -> List[RecognizedPattern]:
        """Detect geographic clustering of anomalies."""
        patterns = []

        # Group anomalies by municipality
        by_muni: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for anomaly in self._anomaly_buffer:
            muni = anomaly.get('muni_code', 'unknown')
            by_muni[muni].append(anomaly)

        # Check for clusters
        for muni_code, muni_anomalies in by_muni.items():
            if len(muni_anomalies) >= self.config.GEOGRAPHIC_CLUSTER_THRESHOLD:
                pattern_key = f"geo_cluster_{muni_code}"

                # Skip if already detected recently
                if pattern_key in self._detected_patterns:
                    continue

                # Get time window
                times = [
                    datetime.fromisoformat(a.get('detected_at', '2000-01-01'))
                    for a in muni_anomalies
                ]
                time_window = (min(times), max(times))

                pattern = self._create_pattern(
                    pattern_type=PatternType.GEOGRAPHIC_CLUSTER,
                    description=f"Cluster geográfico: {len(muni_anomalies)} anomalías en municipio {muni_code}",
                    confidence=0.9,
                    affected_areas=[muni_code],
                    affected_mesas=[a.get('mesa_id', '') for a in muni_anomalies],
                    time_window=time_window,
                    evidence=muni_anomalies[:10],  # Limit evidence
                    significance=min(1.0, len(muni_anomalies) / 20),
                    recommended_action="INVESTIGATE_MUNICIPALITY",
                )

                self._detected_patterns[pattern_key] = pattern
                patterns.append(pattern)

        return patterns

    def _detect_temporal_spikes(self) -> List[RecognizedPattern]:
        """Detect temporal spikes in anomaly frequency."""
        patterns = []

        if len(self._anomaly_buffer) < 10:
            return patterns

        # Group by hour
        by_hour: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for anomaly in self._anomaly_buffer:
            timestamp = anomaly.get('detected_at', '')
            if timestamp:
                hour_key = timestamp[:13]  # YYYY-MM-DDTHH
                by_hour[hour_key].append(anomaly)

        # Calculate average and check for spikes
        if len(by_hour) < 2:
            return patterns

        counts = [len(v) for v in by_hour.values()]
        avg_count = sum(counts) / len(counts)

        for hour_key, anomalies in by_hour.items():
            if len(anomalies) > avg_count * 3:  # 3x average = spike
                pattern_key = f"temporal_spike_{hour_key}"

                if pattern_key in self._detected_patterns:
                    continue

                hour_start = datetime.fromisoformat(hour_key + ":00:00")
                time_window = (hour_start, hour_start + timedelta(hours=1))

                pattern = self._create_pattern(
                    pattern_type=PatternType.TEMPORAL_SPIKE,
                    description=f"Pico temporal: {len(anomalies)} anomalías en hora {hour_key}",
                    confidence=0.8,
                    affected_areas=list(set(a.get('muni_code', '') for a in anomalies)),
                    affected_mesas=[a.get('mesa_id', '') for a in anomalies],
                    time_window=time_window,
                    evidence=anomalies[:10],
                    significance=len(anomalies) / (avg_count * 5),
                    recommended_action="MONITOR_CLOSELY",
                )

                self._detected_patterns[pattern_key] = pattern
                patterns.append(pattern)

        return patterns

    def _detect_systematic_errors(self) -> List[RecognizedPattern]:
        """Detect systematic errors (same type of error repeated)."""
        patterns = []

        # Group by anomaly type
        by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for anomaly in self._anomaly_buffer:
            atype = anomaly.get('type', 'UNKNOWN')
            by_type[atype].append(anomaly)

        # Check for systematic patterns
        for atype, anomalies in by_type.items():
            if len(anomalies) >= 10:
                # Check if similar details
                if self._are_similar(anomalies):
                    pattern_key = f"systematic_{atype}"

                    if pattern_key in self._detected_patterns:
                        continue

                    times = [
                        datetime.fromisoformat(a.get('detected_at', '2000-01-01'))
                        for a in anomalies
                    ]
                    time_window = (min(times), max(times))

                    pattern = self._create_pattern(
                        pattern_type=PatternType.SYSTEMATIC_ERROR,
                        description=f"Error sistemático tipo {atype}: {len(anomalies)} ocurrencias similares",
                        confidence=0.85,
                        affected_areas=list(set(a.get('muni_code', '') for a in anomalies)),
                        affected_mesas=[a.get('mesa_id', '') for a in anomalies],
                        time_window=time_window,
                        evidence=anomalies[:10],
                        significance=min(1.0, len(anomalies) / 30),
                        recommended_action="INVESTIGATE_ROOT_CAUSE",
                    )

                    self._detected_patterns[pattern_key] = pattern
                    patterns.append(pattern)

        return patterns

    def _detect_coordination_signals(self) -> List[RecognizedPattern]:
        """Detect potential coordination signals (suspiciously similar timing)."""
        patterns = []

        if len(self._anomaly_buffer) < 20:
            return patterns

        # Group by 5-minute windows
        by_window: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for anomaly in self._anomaly_buffer:
            timestamp = anomaly.get('detected_at', '')
            if timestamp:
                # Round to 5-minute window
                dt = datetime.fromisoformat(timestamp)
                window_key = dt.strftime('%Y-%m-%dT%H:') + f"{(dt.minute // 5) * 5:02d}"
                by_window[window_key].append(anomaly)

        # Check for suspicious clustering in time
        for window_key, anomalies in by_window.items():
            if len(anomalies) >= 5:
                # Check if from different municipalities (suspicious coordination)
                municipalities = set(a.get('muni_code', '') for a in anomalies)
                if len(municipalities) >= 3:
                    pattern_key = f"coordination_{window_key}"

                    if pattern_key in self._detected_patterns:
                        continue

                    window_start = datetime.fromisoformat(window_key + ":00")
                    time_window = (window_start, window_start + timedelta(minutes=5))

                    pattern = self._create_pattern(
                        pattern_type=PatternType.COORDINATION_SIGNAL,
                        description=f"Señal de coordinación: {len(anomalies)} anomalías en {len(municipalities)} municipios en 5min",
                        confidence=0.7,
                        affected_areas=list(municipalities),
                        affected_mesas=[a.get('mesa_id', '') for a in anomalies],
                        time_window=time_window,
                        evidence=anomalies[:10],
                        significance=len(municipalities) / 10,
                        recommended_action="FLAG_FOR_ANALYSIS",
                    )

                    self._detected_patterns[pattern_key] = pattern
                    patterns.append(pattern)

        return patterns

    def _are_similar(self, anomalies: List[Dict[str, Any]]) -> bool:
        """Check if anomalies have similar characteristics."""
        if len(anomalies) < 2:
            return False

        # Check if delta values are similar (within 20%)
        deltas = [a.get('delta', 0) for a in anomalies if a.get('delta')]
        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            if avg_delta > 0:
                similar_count = sum(
                    1 for d in deltas
                    if abs(d - avg_delta) / avg_delta < 0.2
                )
                if similar_count / len(deltas) > 0.7:
                    return True

        return False

    def _create_pattern(
        self,
        pattern_type: PatternType,
        description: str,
        confidence: float,
        affected_areas: List[str],
        affected_mesas: List[str],
        time_window: Tuple[datetime, datetime],
        evidence: List[Dict[str, Any]],
        significance: float,
        recommended_action: str
    ) -> RecognizedPattern:
        """Create a pattern record."""
        self._pattern_counter += 1
        return RecognizedPattern(
            pattern_id=f"PAT-{self._pattern_counter:06d}",
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            affected_areas=affected_areas,
            affected_mesas=affected_mesas,
            time_window=time_window,
            evidence=evidence,
            significance=min(1.0, significance),
            recommended_action=recommended_action,
            detected_at=datetime.utcnow(),
        )

    def _cleanup_buffer(self, buffer: List[Dict[str, Any]], timestamp_field: str) -> None:
        """Clean up old entries from buffer."""
        cutoff = datetime.utcnow() - timedelta(hours=self._buffer_max_age_hours)
        cutoff_str = cutoff.isoformat()

        buffer[:] = [
            item for item in buffer
            if item.get(timestamp_field, '9999') > cutoff_str
        ][-self._buffer_max_size:]

    def get_recent_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently detected patterns."""
        patterns = sorted(
            self._detected_patterns.values(),
            key=lambda p: p.detected_at,
            reverse=True
        )
        return [p.to_dict() for p in patterns[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get recognizer statistics."""
        return {
            'patterns_detected': self._pattern_counter,
            'active_patterns': len(self._detected_patterns),
            'buffer_sizes': {
                'anomalies': len(self._anomaly_buffer),
                'incidents': len(self._incident_buffer),
                'forms': len(self._form_buffer),
            },
        }
