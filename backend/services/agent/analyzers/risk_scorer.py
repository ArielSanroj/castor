"""
Risk Scorer.
Calculates risk scores for municipalities and geographic areas.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for geographic areas."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MINIMAL = "MINIMAL"


@dataclass
class RiskScore:
    """Risk score for a geographic area."""
    area_code: str
    area_type: str  # DEPARTMENT, MUNICIPALITY, ZONE
    area_name: str
    risk_level: RiskLevel
    score: float  # 0.0 to 1.0
    factors: Dict[str, float]
    anomaly_count: int
    incident_count: int
    last_incident_at: Optional[datetime]
    trend: str  # INCREASING, STABLE, DECREASING
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'area_code': self.area_code,
            'area_type': self.area_type,
            'area_name': self.area_name,
            'risk_level': self.risk_level.value,
            'score': self.score,
            'factors': self.factors,
            'anomaly_count': self.anomaly_count,
            'incident_count': self.incident_count,
            'last_incident_at': self.last_incident_at.isoformat() if self.last_incident_at else None,
            'trend': self.trend,
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class MunicipalityData:
    """Accumulated data for a municipality."""
    code: str
    name: str
    dept_code: str
    total_mesas: int = 0
    mesas_processed: int = 0
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    incidents: List[Dict[str, Any]] = field(default_factory=list)
    historical_risk: float = 0.5  # Historical baseline


class RiskScorer:
    """
    Calculates and tracks risk scores for geographic areas.
    """

    # Risk level thresholds
    RISK_THRESHOLDS = {
        RiskLevel.CRITICAL: 0.85,
        RiskLevel.HIGH: 0.70,
        RiskLevel.MEDIUM: 0.50,
        RiskLevel.LOW: 0.30,
        RiskLevel.MINIMAL: 0.0,
    }

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the risk scorer.

        Args:
            config: Agent configuration
        """
        self.config = config or get_agent_config()

        # Cached municipality data
        self._municipalities: Dict[str, MunicipalityData] = {}

        # Historical scores for trend calculation
        self._score_history: Dict[str, List[Tuple[datetime, float]]] = {}

        logger.info("RiskScorer initialized")

    def calculate_risk(
        self,
        area_code: str,
        area_type: str = "MUNICIPALITY",
        area_name: str = "",
        anomalies: Optional[List[Dict[str, Any]]] = None,
        incidents: Optional[List[Dict[str, Any]]] = None,
        total_mesas: int = 0,
        mesas_processed: int = 0
    ) -> RiskScore:
        """
        Calculate risk score for an area.

        Args:
            area_code: Area code (municipality, department)
            area_type: Type of area
            area_name: Human-readable name
            anomalies: List of anomalies in the area
            incidents: List of incidents in the area
            total_mesas: Total mesas in the area
            mesas_processed: Mesas processed so far

        Returns:
            RiskScore for the area
        """
        anomalies = anomalies or []
        incidents = incidents or []

        # Calculate risk factors
        factors = self._calculate_factors(
            anomalies=anomalies,
            incidents=incidents,
            total_mesas=total_mesas,
            mesas_processed=mesas_processed,
            area_code=area_code
        )

        # Calculate weighted score
        score = self._calculate_weighted_score(factors)

        # Determine risk level
        risk_level = self._score_to_level(score)

        # Calculate trend
        trend = self._calculate_trend(area_code, score)

        # Get last incident time
        last_incident_at = None
        if incidents:
            incident_times = [
                datetime.fromisoformat(i['created_at'].replace('Z', '+00:00'))
                for i in incidents
                if i.get('created_at')
            ]
            if incident_times:
                last_incident_at = max(incident_times)

        # Store for trend tracking
        self._record_score(area_code, score)

        risk_score = RiskScore(
            area_code=area_code,
            area_type=area_type,
            area_name=area_name,
            risk_level=risk_level,
            score=score,
            factors=factors,
            anomaly_count=len(anomalies),
            incident_count=len(incidents),
            last_incident_at=last_incident_at,
            trend=trend,
            updated_at=datetime.utcnow(),
        )

        logger.debug(f"Risk score for {area_code}: {score:.2f} ({risk_level.value})")
        return risk_score

    def update_municipality(
        self,
        muni_code: str,
        muni_name: str,
        dept_code: str,
        anomaly: Optional[Dict[str, Any]] = None,
        incident: Optional[Dict[str, Any]] = None,
        mesa_processed: bool = False
    ) -> RiskScore:
        """
        Update municipality data and recalculate risk.

        Args:
            muni_code: Municipality code
            muni_name: Municipality name
            dept_code: Department code
            anomaly: New anomaly to add
            incident: New incident to add
            mesa_processed: Whether a mesa was processed

        Returns:
            Updated RiskScore
        """
        # Get or create municipality data
        if muni_code not in self._municipalities:
            self._municipalities[muni_code] = MunicipalityData(
                code=muni_code,
                name=muni_name,
                dept_code=dept_code,
            )

        muni = self._municipalities[muni_code]

        # Update data
        if anomaly:
            muni.anomalies.append(anomaly)
            # Keep only recent anomalies (last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            muni.anomalies = [
                a for a in muni.anomalies
                if datetime.fromisoformat(a.get('detected_at', '2000-01-01')) > cutoff
            ]

        if incident:
            muni.incidents.append(incident)

        if mesa_processed:
            muni.mesas_processed += 1

        # Recalculate risk
        return self.calculate_risk(
            area_code=muni_code,
            area_type="MUNICIPALITY",
            area_name=muni_name,
            anomalies=muni.anomalies,
            incidents=muni.incidents,
            total_mesas=muni.total_mesas,
            mesas_processed=muni.mesas_processed,
        )

    def get_high_risk_areas(self, min_level: RiskLevel = RiskLevel.HIGH) -> List[RiskScore]:
        """
        Get all areas at or above a risk level.

        Args:
            min_level: Minimum risk level to include

        Returns:
            List of high-risk RiskScores
        """
        threshold = self.RISK_THRESHOLDS.get(min_level, 0.7)
        high_risk = []

        for muni_code, muni_data in self._municipalities.items():
            score = self.calculate_risk(
                area_code=muni_code,
                area_type="MUNICIPALITY",
                area_name=muni_data.name,
                anomalies=muni_data.anomalies,
                incidents=muni_data.incidents,
                total_mesas=muni_data.total_mesas,
                mesas_processed=muni_data.mesas_processed,
            )

            if score.score >= threshold:
                high_risk.append(score)

        # Sort by score descending
        high_risk.sort(key=lambda x: x.score, reverse=True)
        return high_risk

    def predict_risk(
        self,
        area_code: str,
        hours_ahead: int = 4
    ) -> Tuple[float, RiskLevel, float]:
        """
        Predict future risk based on trends.

        Args:
            area_code: Area code
            hours_ahead: Hours to predict ahead

        Returns:
            Tuple of (predicted_score, predicted_level, confidence)
        """
        history = self._score_history.get(area_code, [])

        if len(history) < 3:
            # Not enough history, return current
            if history:
                current = history[-1][1]
                return current, self._score_to_level(current), 0.3
            return 0.5, RiskLevel.MEDIUM, 0.1

        # Calculate trend using last 6 hours of data
        cutoff = datetime.utcnow() - timedelta(hours=6)
        recent = [(t, s) for t, s in history if t > cutoff]

        if len(recent) < 2:
            current = history[-1][1]
            return current, self._score_to_level(current), 0.4

        # Linear regression for prediction
        first_score = recent[0][1]
        last_score = recent[-1][1]
        time_span = (recent[-1][0] - recent[0][0]).total_seconds() / 3600  # hours

        if time_span > 0:
            rate = (last_score - first_score) / time_span
            predicted = last_score + (rate * hours_ahead)
            predicted = max(0.0, min(1.0, predicted))  # Clamp to 0-1

            # Confidence based on data quality
            confidence = min(0.75, 0.3 + (len(recent) * 0.05))
        else:
            predicted = last_score
            confidence = 0.3

        return predicted, self._score_to_level(predicted), confidence

    def _calculate_factors(
        self,
        anomalies: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]],
        total_mesas: int,
        mesas_processed: int,
        area_code: str
    ) -> Dict[str, float]:
        """Calculate individual risk factors."""
        factors = {}

        # Factor 1: Anomaly density
        if mesas_processed > 0:
            factors['anomaly_density'] = min(1.0, len(anomalies) / mesas_processed)
        else:
            factors['anomaly_density'] = 0.0

        # Factor 2: Incident severity
        severity_scores = {'P0': 1.0, 'P1': 0.7, 'P2': 0.4, 'P3': 0.2}
        if incidents:
            severities = [severity_scores.get(i.get('severity', 'P3'), 0.2) for i in incidents]
            factors['incident_severity'] = sum(severities) / len(severities)
        else:
            factors['incident_severity'] = 0.0

        # Factor 3: Recent activity (last hour weighted more)
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        recent_anomalies = sum(
            1 for a in anomalies
            if datetime.fromisoformat(a.get('detected_at', '2000-01-01')) > hour_ago
        )
        factors['recent_activity'] = min(1.0, recent_anomalies / max(1, self.config.GEOGRAPHIC_CLUSTER_THRESHOLD))

        # Factor 4: Cluster indicator
        if len(anomalies) >= self.config.GEOGRAPHIC_CLUSTER_THRESHOLD:
            factors['cluster_indicator'] = 1.0
        elif len(anomalies) >= self.config.GEOGRAPHIC_CLUSTER_THRESHOLD / 2:
            factors['cluster_indicator'] = 0.7
        else:
            factors['cluster_indicator'] = len(anomalies) / self.config.GEOGRAPHIC_CLUSTER_THRESHOLD

        # Factor 5: Open incidents ratio
        open_incidents = [i for i in incidents if i.get('status') in ('OPEN', 'ASSIGNED')]
        if incidents:
            factors['open_incidents_ratio'] = len(open_incidents) / len(incidents)
        else:
            factors['open_incidents_ratio'] = 0.0

        # Factor 6: Historical baseline
        muni_data = self._municipalities.get(area_code)
        if muni_data:
            factors['historical_baseline'] = muni_data.historical_risk
        else:
            factors['historical_baseline'] = 0.5

        return factors

    def _calculate_weighted_score(self, factors: Dict[str, float]) -> float:
        """Calculate weighted risk score from factors."""
        weights = {
            'anomaly_density': 0.20,
            'incident_severity': 0.25,
            'recent_activity': 0.20,
            'cluster_indicator': 0.15,
            'open_incidents_ratio': 0.10,
            'historical_baseline': 0.10,
        }

        score = sum(factors.get(k, 0) * w for k, w in weights.items())
        return min(1.0, max(0.0, score))

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        for level, threshold in self.RISK_THRESHOLDS.items():
            if score >= threshold:
                return level
        return RiskLevel.MINIMAL

    def _calculate_trend(self, area_code: str, current_score: float) -> str:
        """Calculate risk trend."""
        history = self._score_history.get(area_code, [])

        if len(history) < 2:
            return "STABLE"

        # Compare to average of last 3 scores
        recent_scores = [s for _, s in history[-3:]]
        avg = sum(recent_scores) / len(recent_scores)

        diff = current_score - avg
        if diff > 0.1:
            return "INCREASING"
        elif diff < -0.1:
            return "DECREASING"
        return "STABLE"

    def _record_score(self, area_code: str, score: float) -> None:
        """Record score for trend tracking."""
        if area_code not in self._score_history:
            self._score_history[area_code] = []

        self._score_history[area_code].append((datetime.utcnow(), score))

        # Keep only last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self._score_history[area_code] = [
            (t, s) for t, s in self._score_history[area_code]
            if t > cutoff
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get scorer statistics."""
        return {
            'municipalities_tracked': len(self._municipalities),
            'areas_with_history': len(self._score_history),
            'risk_thresholds': {k.value: v for k, v in self.RISK_THRESHOLDS.items()},
        }
