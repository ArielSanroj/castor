from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)
    tone: Optional[str] = Field(default="institucional", max_length=80)
    values: List[str] = Field(default_factory=list, max_length=12)
    red_lines: List[str] = Field(default_factory=list, max_length=12)


class AdvisorRequest(BaseModel):
    location: str = Field(..., min_length=2, max_length=200)
    topics: List[str] = Field(default_factory=list, max_length=10)
    candidate_profile: CandidateProfile = Field(default_factory=CandidateProfile)
    goals: List[str] = Field(default_factory=list, max_length=8)
    constraints: List[str] = Field(default_factory=list, max_length=8)
    language: str = Field(default="es", max_length=5)
    max_drafts: int = Field(default=4, ge=1, le=6)
    source_summary: Optional[str] = Field(default=None, max_length=1200)


class AdvisorDraft(BaseModel):
    kind: str = Field(..., description="post or comment")
    intent: str
    draft: str
    rationale: str
    risk_level: str
    best_time: Optional[str] = None


class AdvisorResponse(BaseModel):
    success: bool = True
    approval_required: bool = True
    guidance: str
    drafts: List[AdvisorDraft]
