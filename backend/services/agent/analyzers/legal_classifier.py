"""
Legal Classifier.
Classifies incidents by CPACA article and calculates nullity viability.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class CPACAArticle(int, Enum):
    """CPACA articles relevant to electoral matters."""
    ART_223 = 223  # Causales de nulidad de elecciones
    ART_224 = 224  # Causales de nulidad de actos de escrutinio
    ART_225 = 225  # Solicitud de recuento
    ART_226 = 226  # Recursos y apelaciones


class NullityCausal(str, Enum):
    """Specific causals for nullity under CPACA."""
    # Art. 223 - Nulidad de elecciones
    VIOLENCE_OR_FRAUD = "VIOLENCE_OR_FRAUD"
    VOTE_COUNT_ERROR = "VOTE_COUNT_ERROR"
    INELIGIBLE_CANDIDATE = "INELIGIBLE_CANDIDATE"
    REGISTRATION_FRAUD = "REGISTRATION_FRAUD"

    # Art. 224 - Nulidad de actos de escrutinio
    ARITHMETIC_ERROR = "ARITHMETIC_ERROR"
    IRREGULAR_RECOUNT = "IRREGULAR_RECOUNT"
    SIGNATURE_VIOLATION = "SIGNATURE_VIOLATION"
    DOCUMENT_ALTERATION = "DOCUMENT_ALTERATION"


@dataclass
class LegalClassification:
    """Legal classification of an incident."""
    incident_id: int
    mesa_id: str
    primary_article: CPACAArticle
    secondary_articles: List[CPACAArticle]
    causals: List[NullityCausal]
    deadline: datetime
    deadline_hours: int
    nullity_viability: float  # 0.0 to 1.0
    viability_factors: Dict[str, float]
    recommended_actions: List[str]
    evidence_requirements: List[str]
    classified_at: datetime
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'incident_id': self.incident_id,
            'mesa_id': self.mesa_id,
            'primary_article': self.primary_article.value,
            'secondary_articles': [a.value for a in self.secondary_articles],
            'causals': [c.value for c in self.causals],
            'deadline': self.deadline.isoformat(),
            'deadline_hours': self.deadline_hours,
            'nullity_viability': self.nullity_viability,
            'viability_factors': self.viability_factors,
            'recommended_actions': self.recommended_actions,
            'evidence_requirements': self.evidence_requirements,
            'classified_at': self.classified_at.isoformat(),
            'confidence': self.confidence,
        }


# Mapping of incident types to CPACA articles
INCIDENT_TO_ARTICLE_MAP = {
    'ARITHMETIC_FAIL': (CPACAArticle.ART_224, [NullityCausal.ARITHMETIC_ERROR]),
    'DISCREPANCY_RNEC': (CPACAArticle.ART_224, [NullityCausal.VOTE_COUNT_ERROR]),
    'OCR_LOW_CONF': (CPACAArticle.ART_225, []),  # Needs recount
    'E11_VS_URNA': (CPACAArticle.ART_224, [NullityCausal.ARITHMETIC_ERROR]),
    'RECOUNT_MARKED': (CPACAArticle.ART_225, [NullityCausal.IRREGULAR_RECOUNT]),
    'SIGNATURE_MISSING': (CPACAArticle.ART_224, [NullityCausal.SIGNATURE_VIOLATION]),
    'RNEC_DELAY': (CPACAArticle.ART_223, []),  # Informational
    'SOURCE_MISMATCH': (CPACAArticle.ART_224, [NullityCausal.DOCUMENT_ALTERATION]),
    'GEOGRAPHIC_CLUSTER': (CPACAArticle.ART_223, [NullityCausal.VIOLENCE_OR_FRAUD]),
}

# Deadline durations by article (hours)
ARTICLE_DEADLINES = {
    CPACAArticle.ART_223: 48,
    CPACAArticle.ART_224: 48,
    CPACAArticle.ART_225: 120,  # 5 days
    CPACAArticle.ART_226: 240,  # 10 days
}


class LegalClassifier:
    """
    Classifies incidents by CPACA article and calculates nullity viability.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the legal classifier.

        Args:
            config: Agent configuration
        """
        self.config = config or get_agent_config()
        self._classifications_count = 0

        logger.info("LegalClassifier initialized")

    def classify(self, incident: Dict[str, Any]) -> LegalClassification:
        """
        Classify an incident by CPACA article.

        Args:
            incident: Incident data

        Returns:
            LegalClassification with article, causals, and viability
        """
        incident_id = incident.get('id', 0)
        incident_type = incident.get('incident_type', 'UNKNOWN')
        mesa_id = incident.get('mesa_id', '')
        delta_value = incident.get('delta_value', 0)
        ocr_confidence = incident.get('ocr_confidence')

        # Get primary article and causals
        article_info = INCIDENT_TO_ARTICLE_MAP.get(
            incident_type,
            (CPACAArticle.ART_223, [])
        )
        primary_article = article_info[0]
        causals = article_info[1]

        # Determine secondary articles
        secondary_articles = self._get_secondary_articles(incident_type, incident)

        # Calculate deadline
        deadline_hours = ARTICLE_DEADLINES.get(primary_article, 48)
        created_at = incident.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif created_at is None:
            created_at = datetime.utcnow()

        deadline = created_at + timedelta(hours=deadline_hours)

        # Calculate nullity viability
        viability, factors = self._calculate_viability(
            incident_type=incident_type,
            delta_value=delta_value,
            ocr_confidence=ocr_confidence,
            causals=causals,
            incident=incident
        )

        # Get recommended actions and evidence requirements
        recommended_actions = self._get_recommended_actions(primary_article, causals, viability)
        evidence_requirements = self._get_evidence_requirements(primary_article, causals)

        # Calculate confidence
        confidence = self._calculate_classification_confidence(incident)

        self._classifications_count += 1

        classification = LegalClassification(
            incident_id=incident_id,
            mesa_id=mesa_id,
            primary_article=primary_article,
            secondary_articles=secondary_articles,
            causals=causals,
            deadline=deadline,
            deadline_hours=deadline_hours,
            nullity_viability=viability,
            viability_factors=factors,
            recommended_actions=recommended_actions,
            evidence_requirements=evidence_requirements,
            classified_at=datetime.utcnow(),
            confidence=confidence,
        )

        logger.info(
            f"Classified incident {incident_id} as Art. {primary_article.value}, "
            f"viability: {viability:.1%}"
        )

        return classification

    def calculate_nullity_viability(self, incident: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate nullity viability score.

        Args:
            incident: Incident data

        Returns:
            Tuple of (viability_score, factors)
        """
        incident_type = incident.get('incident_type', 'UNKNOWN')
        delta_value = incident.get('delta_value', 0)
        ocr_confidence = incident.get('ocr_confidence')

        article_info = INCIDENT_TO_ARTICLE_MAP.get(
            incident_type,
            (CPACAArticle.ART_223, [])
        )
        causals = article_info[1]

        return self._calculate_viability(
            incident_type=incident_type,
            delta_value=delta_value,
            ocr_confidence=ocr_confidence,
            causals=causals,
            incident=incident
        )

    def _calculate_viability(
        self,
        incident_type: str,
        delta_value: Optional[float],
        ocr_confidence: Optional[float],
        causals: List[NullityCausal],
        incident: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate nullity viability with factor breakdown."""
        factors = {}

        # Factor 1: Severity of the issue (based on incident type)
        severity_weights = {
            'ARITHMETIC_FAIL': 0.9,
            'DISCREPANCY_RNEC': 0.85,
            'GEOGRAPHIC_CLUSTER': 0.95,
            'E11_VS_URNA': 0.8,
            'RECOUNT_MARKED': 0.7,
            'SOURCE_MISMATCH': 0.75,
            'SIGNATURE_MISSING': 0.6,
            'OCR_LOW_CONF': 0.5,
            'RNEC_DELAY': 0.3,
        }
        factors['severity'] = severity_weights.get(incident_type, 0.5)

        # Factor 2: Vote impact (higher impact = higher viability)
        if delta_value and delta_value > 0:
            if delta_value >= 1000:
                factors['vote_impact'] = 1.0
            elif delta_value >= 500:
                factors['vote_impact'] = 0.9
            elif delta_value >= 100:
                factors['vote_impact'] = 0.7
            elif delta_value >= 10:
                factors['vote_impact'] = 0.5
            else:
                factors['vote_impact'] = 0.3
        else:
            factors['vote_impact'] = 0.3

        # Factor 3: Evidence quality
        if ocr_confidence is not None:
            # Higher OCR confidence = better evidence
            factors['evidence_quality'] = ocr_confidence
        else:
            factors['evidence_quality'] = 0.7  # Default

        # Factor 4: Legal basis strength (number of causals)
        if causals:
            factors['legal_basis'] = min(1.0, len(causals) * 0.4 + 0.2)
        else:
            factors['legal_basis'] = 0.3

        # Factor 5: Pattern indicator (is part of a cluster?)
        if incident_type == 'GEOGRAPHIC_CLUSTER':
            factors['pattern_indicator'] = 1.0
        else:
            factors['pattern_indicator'] = 0.5

        # Calculate weighted average
        weights = {
            'severity': 0.25,
            'vote_impact': 0.30,
            'evidence_quality': 0.20,
            'legal_basis': 0.15,
            'pattern_indicator': 0.10,
        }

        viability = sum(factors[k] * weights[k] for k in factors)

        return viability, factors

    def _get_secondary_articles(
        self,
        incident_type: str,
        incident: Dict[str, Any]
    ) -> List[CPACAArticle]:
        """Determine secondary applicable articles."""
        secondary = []

        # Art. 225 (recount) often applies with 224
        if incident_type in ('ARITHMETIC_FAIL', 'E11_VS_URNA', 'OCR_LOW_CONF'):
            secondary.append(CPACAArticle.ART_225)

        # Art. 226 (appeals) applies when escalated
        if incident.get('escalated_to_legal'):
            secondary.append(CPACAArticle.ART_226)

        return secondary

    def _get_recommended_actions(
        self,
        article: CPACAArticle,
        causals: List[NullityCausal],
        viability: float
    ) -> List[str]:
        """Get recommended legal actions."""
        actions = []

        if article == CPACAArticle.ART_223:
            actions.append("Documentar irregularidades con evidencia fotográfica")
            if viability > self.config.NULLITY_VIABILITY_THRESHOLD:
                actions.append("Preparar demanda de nulidad electoral")
            actions.append("Notificar a testigos electorales")

        elif article == CPACAArticle.ART_224:
            actions.append("Solicitar recuento de votos")
            actions.append("Impugnar acta de escrutinio")
            if NullityCausal.ARITHMETIC_ERROR in causals:
                actions.append("Documentar error aritmético con cálculos")

        elif article == CPACAArticle.ART_225:
            actions.append("Solicitar recuento formal ante autoridad electoral")
            actions.append("Preservar cadena de custodia de documentos")

        elif article == CPACAArticle.ART_226:
            actions.append("Interponer recurso de apelación")
            actions.append("Preparar memorial con evidencia completa")

        return actions

    def _get_evidence_requirements(
        self,
        article: CPACAArticle,
        causals: List[NullityCausal]
    ) -> List[str]:
        """Get evidence requirements for the classification."""
        requirements = []

        # Common requirements
        requirements.append("Copia del E-14 original")
        requirements.append("Registro fotográfico de la mesa")

        if article == CPACAArticle.ART_223:
            requirements.append("Testimonios de testigos electorales")
            requirements.append("Actas de incidentes del puesto de votación")
            if NullityCausal.VIOLENCE_OR_FRAUD in causals:
                requirements.append("Denuncia ante autoridades")
                requirements.append("Registro de video si disponible")

        elif article == CPACAArticle.ART_224:
            requirements.append("E-14 de comparación (RNEC vs testigo)")
            if NullityCausal.ARITHMETIC_ERROR in causals:
                requirements.append("Análisis detallado de sumas y totales")
            if NullityCausal.SIGNATURE_VIOLATION in causals:
                requirements.append("Listado de jurados designados vs firmantes")

        elif article == CPACAArticle.ART_225:
            requirements.append("Solicitud formal de recuento")
            requirements.append("Poder de representación legal")

        return requirements

    def _calculate_classification_confidence(self, incident: Dict[str, Any]) -> float:
        """Calculate confidence in the classification."""
        confidence = 0.7  # Base confidence

        # Higher confidence if we have clear incident type
        if incident.get('incident_type') in INCIDENT_TO_ARTICLE_MAP:
            confidence += 0.15

        # Higher confidence with delta value
        if incident.get('delta_value'):
            confidence += 0.1

        # Higher confidence with good OCR
        ocr_conf = incident.get('ocr_confidence')
        if ocr_conf and ocr_conf > 0.8:
            confidence += 0.05

        return min(1.0, confidence)

    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            'classifications_count': self._classifications_count,
            'viability_threshold': self.config.NULLITY_VIABILITY_THRESHOLD,
        }
