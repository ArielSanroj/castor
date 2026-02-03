"""
RAG (Retrieval Augmented Generation) schemas.
Schemas for chat and document retrieval endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RAGSource(BaseModel):
    """Source document reference from RAG retrieval."""
    document_id: str = ""
    content: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_type: str = ""  # tweet, analysis, report, etc.


class RAGChatRequest(BaseModel):
    """Request for RAG-enhanced chat."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    include_sources: bool = True
    max_sources: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class RAGChatResponse(BaseModel):
    """Response from RAG-enhanced chat."""
    response: str = ""
    session_id: str = ""
    sources: List[RAGSource] = Field(default_factory=list)
    confidence: float = 0.0
    model_used: str = ""
    tokens_used: int = 0
    processing_time_ms: int = 0


class RAGIndexRequest(BaseModel):
    """Request to index documents for RAG."""
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    document_type: str = ""  # tweet, analysis, report
    metadata: Dict[str, Any] = Field(default_factory=dict)
    batch_id: Optional[str] = None


class RAGIndexResponse(BaseModel):
    """Response from RAG indexing."""
    success: bool = True
    indexed_count: int = 0
    failed_count: int = 0
    batch_id: str = ""
    errors: List[str] = Field(default_factory=list)


class RAGStatsResponse(BaseModel):
    """Statistics about the RAG index."""
    total_documents: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    index_size_mb: float = 0.0
    last_indexed_at: Optional[datetime] = None
    embedding_model: str = ""
    vector_dimensions: int = 0
