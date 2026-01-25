"""
Schemas para el Dashboard de Equipo de Campaña Electoral.
Integra datos de E-14 (OCR) con análisis de redes sociales.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class AlertSeverity(str, Enum):
    """Severidad de alertas."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Estado de alertas."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ActionPriority(str, Enum):
    """Prioridad de acciones."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================
# WAR ROOM SCHEMAS
# ============================================================

class WarRoomStats(BaseModel):
    """Estadísticas del War Room."""
    total_mesas: int = Field(0, description="Total de mesas de votación")
    validated: int = Field(0, description="Mesas validadas")
    needs_review: int = Field(0, description="Mesas pendientes de revisión")
    pending: int = Field(0, description="Mesas pendientes de procesar")
    processing: int = Field(0, description="Mesas en procesamiento")
    failed: int = Field(0, description="Mesas con error")

    critical_alerts: int = Field(0, description="Alertas críticas abiertas")
    high_alerts: int = Field(0, description="Alertas altas abiertas")

    validation_rate: float = Field(0.0, description="Tasa de validación (0-100)")
    processing_rate: float = Field(0.0, description="Tasa de procesamiento (0-100)")

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ProcessingProgress(BaseModel):
    """Progreso de procesamiento por municipio."""
    dept_code: str
    dept_name: Optional[str] = None
    muni_code: str
    muni_name: Optional[str] = None
    total_mesas: int = 0
    validated: int = 0
    needs_review: int = 0
    pending: int = 0
    critical_alerts: int = 0
    validation_rate: float = 0.0


class AlertResponse(BaseModel):
    """Respuesta de alerta individual."""
    id: int
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: Optional[str] = None

    mesa_id: Optional[str] = None
    dept_code: Optional[str] = None
    muni_code: Optional[str] = None

    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    evidence: Optional[Dict[str, Any]] = None


class AlertAssignRequest(BaseModel):
    """Request para asignar una alerta."""
    user_id: int
    notes: Optional[str] = None


class AlertsListResponse(BaseModel):
    """Lista de alertas."""
    success: bool = True
    alerts: List[AlertResponse]
    total: int
    open_count: int
    critical_count: int


# ============================================================
# REPORTES SCHEMAS
# ============================================================

class CandidateVoteSummary(BaseModel):
    """Resumen de votos por candidato."""
    candidate_name: str
    party_name: Optional[str] = None
    ballot_code: str
    total_votes: int
    percentage: float = Field(..., ge=0, le=100)
    mesas_count: int = 0


class VotesByParty(BaseModel):
    """Votos agrupados por partido."""
    party_name: str
    party_code: Optional[str] = None
    total_votes: int
    percentage: float
    candidates_count: int


class VotesReportResponse(BaseModel):
    """Reporte de votos por candidato."""
    success: bool = True
    contest_id: int
    contest_name: str
    total_votes: int
    total_mesas: int
    mesas_counted: int
    coverage_percentage: float

    by_candidate: List[CandidateVoteSummary]
    by_party: List[VotesByParty]

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class RegionalTrend(BaseModel):
    """Tendencia regional."""
    dept_code: str
    dept_name: str
    muni_code: Optional[str] = None
    muni_name: Optional[str] = None

    total_votes: int
    total_mesas: int
    coverage: float

    # Top candidato en la región
    leading_candidate: Optional[str] = None
    leading_votes: int = 0
    leading_percentage: float = 0.0

    # Participación
    total_voters: int = 0  # Sufragantes E-11
    participation_rate: float = 0.0


class RegionalTrendsResponse(BaseModel):
    """Tendencias regionales."""
    success: bool = True
    contest_id: int
    trends: List[RegionalTrend]
    total_departments: int
    total_municipalities: int


# ============================================================
# PLAN DE ACCIÓN SCHEMAS
# ============================================================

class ActionItem(BaseModel):
    """Acción priorizada."""
    id: str
    action: str
    priority: ActionPriority
    zone: str
    zone_name: Optional[str] = None

    resources: List[str] = Field(default_factory=list)
    reason: str

    related_alert_id: Optional[int] = None
    related_mesa_id: Optional[str] = None

    estimated_impact: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActionPlanResponse(BaseModel):
    """Plan de acción priorizado."""
    success: bool = True
    contest_id: int
    total_actions: int

    critical_actions: List[ActionItem]
    high_actions: List[ActionItem]
    medium_actions: List[ActionItem]
    low_actions: List[ActionItem]

    generated_at: datetime = Field(default_factory=datetime.utcnow)


class OpportunityZone(BaseModel):
    """Zona con oportunidad de movilización."""
    dept_code: str
    dept_name: str
    muni_code: str
    muni_name: str

    habilitados: int = Field(..., description="Votantes habilitados (E-11)")
    votaron: int = Field(..., description="Votantes que votaron")
    participation: float = Field(..., description="Tasa de participación")

    potential_votes: int = Field(0, description="Votos potenciales a movilizar")
    priority_score: float = Field(0.0, description="Score de prioridad")


class OpportunityZonesResponse(BaseModel):
    """Zonas de oportunidad."""
    success: bool = True
    contest_id: int
    zones: List[OpportunityZone]
    total_potential: int = 0
    average_participation: float = 0.0


# ============================================================
# CORRELACIÓN SCHEMAS
# ============================================================

class E14SocialCorrelation(BaseModel):
    """Correlación E-14 vs métricas sociales."""
    dept_code: str
    dept_name: str
    muni_code: Optional[str] = None
    muni_name: Optional[str] = None

    # Datos E-14
    total_votes: int
    vote_percentage: float

    # Métricas sociales
    icce_score: Optional[float] = None
    sov_score: Optional[float] = None
    sentiment_score: Optional[float] = None

    # Discrepancia
    expected_vs_actual: Optional[float] = None  # % diferencia


class E14SocialCorrelationResponse(BaseModel):
    """Respuesta de correlación E-14 vs Social."""
    success: bool = True
    contest_id: int
    candidate_name: Optional[str] = None

    data_points: List[E14SocialCorrelation]

    # Estadísticas
    r_squared: Optional[float] = None
    rmse: Optional[float] = None
    correlation_coefficient: Optional[float] = None

    insights: List[str] = Field(default_factory=list)


class ForecastVsReality(BaseModel):
    """Forecast vs resultados reales."""
    date: str

    # Forecast
    forecast_votes: Optional[int] = None
    forecast_percentage: Optional[float] = None
    forecast_icce: Optional[float] = None

    # Real
    actual_votes: Optional[int] = None
    actual_percentage: Optional[float] = None

    # Delta
    delta_votes: Optional[int] = None
    delta_percentage: Optional[float] = None
    accuracy: Optional[float] = None


class ForecastVsRealityResponse(BaseModel):
    """Respuesta de forecast vs realidad."""
    success: bool = True
    contest_id: int
    candidate_name: Optional[str] = None

    timeline: List[ForecastVsReality]

    overall_accuracy: Optional[float] = None
    mean_absolute_error: Optional[float] = None

    insights: List[str] = Field(default_factory=list)


# ============================================================
# DASHBOARD GENERAL
# ============================================================

class DashboardSummary(BaseModel):
    """Resumen general del dashboard."""
    success: bool = True
    contest_id: int
    contest_name: str
    election_date: str

    war_room: WarRoomStats

    # Quick stats
    total_votes_counted: int = 0
    leading_candidate: Optional[str] = None
    leading_percentage: float = 0.0

    pending_alerts: int = 0
    pending_actions: int = 0

    last_updated: datetime = Field(default_factory=datetime.utcnow)
