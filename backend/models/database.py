"""
SQLAlchemy ORM models for CASTOR ELECCIONES.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Reusable timestamp fields."""

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class User(Base, TimestampMixin):
    """Campaign user."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(32))
    first_name = Column(String(120))
    last_name = Column(String(120))
    campaign_role = Column(String(120))
    candidate_position = Column(String(120))
    whatsapp_number = Column(String(32))
    whatsapp_opt_in = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")


class Analysis(Base, TimestampMixin):
    """Stored analysis history with normalized sentiment data."""

    __tablename__ = "analyses"
    __table_args__ = (
        Index('ix_analyses_location_date', 'location', 'created_at'),
        Index('ix_analyses_sentiment', 'sentiment_positive', 'sentiment_negative'),
        {"sqlite_autoincrement": True},
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    location = Column(String(120), nullable=False, index=True)
    theme = Column(String(120), nullable=False, index=True)
    candidate_name = Column(String(120), index=True)

    # Normalized sentiment (queryable)
    tweets_analyzed = Column(Integer, default=0)
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)
    trending_topic = Column(String(255))

    # Keep JSON for backward compatibility and full data
    analysis_data = Column(JSON, nullable=False)

    # Relationships
    user = relationship("User", back_populates="analyses")
    topics = relationship("AnalysisTopic", back_populates="analysis", cascade="all, delete-orphan")
    recommendations = relationship("AnalysisRecommendation", back_populates="analysis", cascade="all, delete-orphan")
    speech = relationship("AnalysisSpeech", back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class AnalysisTopic(Base):
    """Normalized topic analysis for queryable insights."""

    __tablename__ = "analysis_topics"
    __table_args__ = (
        Index('ix_topics_sentiment', 'topic_name', 'sentiment_negative'),
        Index('ix_topics_location', 'topic_name', 'sentiment_positive'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    topic_name = Column(String(120), nullable=False, index=True)  # Seguridad, Salud, etc.
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)
    tweet_count = Column(Integer, default=0)
    key_insights = Column(JSON, default=list)  # Array of strings
    sample_tweets = Column(JSON, default=list)  # Array of tweet texts

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    analysis = relationship("Analysis", back_populates="topics")


class AnalysisRecommendation(Base):
    """Normalized recommendations for filtering and tracking."""

    __tablename__ = "analysis_recommendations"
    __table_args__ = (
        Index('ix_recommendations_type_priority', 'recommendation_type', 'priority'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    recommendation_type = Column(String(50), nullable=False, index=True)  # finding, recommendation, action
    priority = Column(String(20), default="media")  # alta, media, baja
    content = Column(Text, nullable=False)
    topic_related = Column(String(120))  # Related PND topic

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    analysis = relationship("Analysis", back_populates="recommendations")


class AnalysisSpeech(Base, TimestampMixin):
    """Normalized speech linked to analysis."""

    __tablename__ = "analysis_speeches"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True)

    title = Column(String(255))
    content = Column(Text, nullable=False)
    key_points = Column(JSON, default=list)
    duration_minutes = Column(Integer, default=7)

    analysis = relationship("Analysis", back_populates="speech")


class UserMetrics(Base, TimestampMixin):
    """Aggregated user metrics for quick dashboard access."""

    __tablename__ = "user_metrics"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    total_analyses = Column(Integer, default=0)
    total_topics_analyzed = Column(Integer, default=0)
    avg_sentiment_positive = Column(Float, default=0.0)
    avg_sentiment_negative = Column(Float, default=0.0)
    most_analyzed_location = Column(String(120))
    most_analyzed_topic = Column(String(120))
    last_analysis_at = Column(DateTime(timezone=True))

    # Trend data (last 30 days)
    sentiment_trend = Column(JSON, default=list)  # [{date, positive, negative}, ...]


class TrendingTopic(Base):
    """Trending topics cached for quick reuse."""

    __tablename__ = "trending_topics"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    topic = Column(String(255), nullable=False, index=True)
    location = Column(String(120), nullable=False, index=True)
    tweet_count = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0)
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)
    keywords = Column(JSON, default=list)
    sample_tweets = Column(JSON, default=list)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True)


class Speech(Base, TimestampMixin):
    """Persisted speeches when needed for auditing."""

    __tablename__ = "speeches"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    location = Column(String(120))
    candidate_name = Column(String(120))
    topic = Column(String(255))
    content = Column(Text, nullable=False)
    extra_metadata = Column(JSON, default=dict)


class Signature(Base):
    """Collected campaign signatures."""

    __tablename__ = "signatures"
    __table_args__ = (
        # Composite index for duplicate checking
        Index('ix_signatures_campaign_email', 'campaign_id', 'signer_email'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36))
    campaign_id = Column(String(120), nullable=False, index=True)
    signer_name = Column(String(255), nullable=False)
    signer_email = Column(String(255), nullable=False, index=True)
    signer_phone = Column(String(32))
    signer_id_number = Column(String(64))
    location = Column(String(120))
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CampaignAction(Base, TimestampMixin):
    """Historical campaign actions used for learning."""

    __tablename__ = "campaign_actions"
    __table_args__ = (
        # Composite index for user_id + roi queries (common pattern for getting effective strategies)
        Index('ix_campaign_actions_user_roi', 'user_id', 'roi'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(120), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    channels = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    predicted_votes = Column(Integer, default=0)
    actual_votes = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    roi = Column(Float, default=0.0)


class VoteStrategy(Base, TimestampMixin):
    """Recommended strategies generated by the AI agent."""

    __tablename__ = "vote_strategies"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    location = Column(String(120), index=True)
    target_demographic = Column(String(255))
    strategy_name = Column(String(255), nullable=False)
    strategy_description = Column(Text)
    key_messages = Column(JSON, default=list)
    channels = Column(JSON, default=list)
    timing = Column(String(120))
    predicted_votes = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)
    risk_level = Column(String(32), default="medio")
    based_on_trending_topics = Column(JSON, default=list)
    sentiment_alignment = Column(Float, default=0.0)


class Lead(Base, TimestampMixin):
    """Demo request leads for campaign tracking."""

    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    interest = Column(String(50), nullable=False, index=True)  # forecast, campañas, medios
    location = Column(String(120), nullable=False)  # ciudad
    candidacy_type = Column(String(50), index=True)  # congreso, regionales, presidencia (opcional)
    status = Column(String(50), default="nuevo", index=True)  # nuevo, contactado, convertido, rechazado
    notes = Column(Text)
    extra_metadata = Column(JSON, default=dict)
