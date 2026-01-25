"""
Schemas for narrative electoral metrics.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NarrativeIndices(BaseModel):
    """Narrative electoral indices."""
    sve: float = Field(..., ge=0.0, le=1.0, description="Share of Voice Electoral")
    sna: float = Field(..., ge=-1.0, le=1.0, description="Sentiment Net Adjusted")
    cp: float = Field(..., ge=0.0, le=1.0, description="Comparative Preference")
    nmi: float = Field(..., ge=-1.0, le=1.0, description="Narrative Motivation Index")


class IVNResult(BaseModel):
    """Intención de Voto Narrativa result."""
    ivn: float = Field(..., ge=0.0, le=1.0, description="IVN score 0-1")
    interpretation: str
    risk_level: str = Field(..., description="'bajo', 'medio-bajo', 'medio', 'medio-alto', 'alto'")
    components: Dict[str, float]


class NarrativeMetricsResponse(BaseModel):
    """Response with narrative metrics."""
    success: bool = True
    narrative_indices: NarrativeIndices
    ivn: IVNResult
    metadata: Dict[str, Any] = Field(default_factory=dict)

