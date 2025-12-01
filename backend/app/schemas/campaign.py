from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .core import SentimentOverview, TopicAnalysis, ChartData


class CampaignAnalysisRequest(BaseModel):
    """
    Request body for /api/campaign/analyze
    """
    location: str
    theme: str
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    max_tweets: int = Field(default=120, ge=10, le=2000)
    language: str = Field(default="es")


class ExecutiveSummary(BaseModel):
    overview: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class StrategicAction(BaseModel):
    description: str
    priority: str
    estimated_timeline: Optional[str] = None
    expected_impact: Optional[str] = None


class StrategicObjective(BaseModel):
    name: str
    description: Optional[str] = None
    actions: List[StrategicAction] = Field(default_factory=list)


class StrategicPlan(BaseModel):
    objectives: List[StrategicObjective] = Field(default_factory=list)
    timeline: Optional[Dict[str, Any]] = None
    overall_expected_impact: Optional[str] = None


class Speech(BaseModel):
    title: str
    key_points: List[str] = Field(default_factory=list)
    content: str
    duration_minutes: Optional[int] = None
    trending_topic: Optional[str] = None


class CampaignMetadata(BaseModel):
    tweets_analyzed: int
    location: str
    theme: str
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    generated_at: datetime
    trending_topic: Optional[str] = None
    raw_query: Optional[str] = None


class CampaignAnalysisResponse(BaseModel):
    success: bool = True

    executive_summary: ExecutiveSummary
    topic_analyses: List[TopicAnalysis]
    strategic_plan: StrategicPlan
    speech: Speech
    chart_data: ChartData

    metadata: CampaignMetadata
