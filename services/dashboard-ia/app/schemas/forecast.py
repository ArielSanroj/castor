from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ICCEValue(BaseModel):
    """Índice Compuesto de Conversación Electoral para un día."""
    date: datetime
    value: float = Field(..., ge=0.0, le=100.0, description="ICCE value 0-100")
    volume: int = Field(..., ge=0, description="Number of mentions")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Net sentiment -1 to 1")
    conversation_share: float = Field(..., ge=0.0, le=1.0, description="Share of total conversation")


class MomentumValue(BaseModel):
    """Momentum Electoral de Conversación para un día."""
    date: datetime
    momentum: float = Field(..., description="Momentum score (can be negative)")
    change: float = Field(..., description="Change from previous day")
    trend: str = Field(..., description="'up', 'down', or 'stable'")


class ForecastPoint(BaseModel):
    """Un punto de proyección futura."""
    date: datetime
    projected_value: float
    lower_bound: float
    upper_bound: float
    confidence: float = Field(..., ge=0.0, le=1.0)


class ScenarioSimulation(BaseModel):
    """Resultado de simulación de escenario."""
    scenario_name: str
    baseline_icce: float
    simulated_icce: float
    impact: float = Field(..., description="Change in ICCE")
    impact_percentage: float = Field(..., description="Percentage change")


class ForecastRequest(BaseModel):
    """Request body for forecast endpoints."""
    location: str
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    topic: Optional[str] = None
    days_back: int = Field(default=30, ge=7, le=90, description="Days of historical data")
    forecast_days: int = Field(default=14, ge=7, le=30, description="Days to forecast ahead")


class ICCEResponse(BaseModel):
    """Response for ICCE endpoint."""
    success: bool = True
    candidate_name: Optional[str] = None
    location: str
    current_icce: float = Field(..., ge=0.0, le=100.0)
    historical_values: List[ICCEValue]
    metadata: Dict[str, Any]


class MomentumResponse(BaseModel):
    """Response for Momentum endpoint."""
    success: bool = True
    candidate_name: Optional[str] = None
    location: str
    current_momentum: float
    historical_momentum: List[MomentumValue]
    trend: str
    metadata: Dict[str, Any]


class ForecastResponse(BaseModel):
    """Response for Forecast endpoint."""
    success: bool = True
    candidate_name: Optional[str] = None
    location: str
    forecast_points: List[ForecastPoint]
    model_type: str = Field(..., description="'prophet', 'holt_winters', or 'arima'")
    metadata: Dict[str, Any]


class ScenarioRequest(BaseModel):
    """Request for scenario simulation."""
    location: str
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    scenario_type: str = Field(..., description="'announcement', 'debate', 'crisis', 'positive_news'")
    scenario_description: Optional[str] = None
    expected_sentiment_shift: float = Field(default=0.0, ge=-1.0, le=1.0)


class ScenarioResponse(BaseModel):
    """Response for scenario simulation."""
    success: bool = True
    simulation: ScenarioSimulation
    baseline_forecast: List[ForecastPoint]
    simulated_forecast: List[ForecastPoint]
    metadata: Dict[str, Any]


class ForecastDashboardResponse(BaseModel):
    """Complete forecast dashboard response."""
    success: bool = True
    candidate_name: Optional[str] = None
    location: str
    icce: ICCEResponse
    momentum: MomentumResponse
    forecast: ForecastResponse
    metadata: Dict[str, Any]

