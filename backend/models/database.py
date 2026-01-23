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


# ============================================================================
# NUEVAS TABLAS: Almacenamiento completo de datos del Dashboard
# ============================================================================

class ApiCall(Base, TimestampMixin):
    """
    Registro de cada llamada a la API (cada "Generar Dashboard").
    Agrupa todos los tweets y métricas de una sesión de análisis.
    """
    __tablename__ = "api_calls"
    __table_args__ = (
        Index('ix_api_calls_candidate_date', 'candidate_name', 'fetched_at'),
        Index('ix_api_calls_location_date', 'location', 'fetched_at'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)

    # Parámetros de búsqueda
    location = Column(String(120), nullable=False, index=True)
    topic = Column(String(120), index=True)  # PND topic o None para "Todas"
    candidate_name = Column(String(200), index=True)
    politician = Column(String(50))  # Twitter handle sin @

    # Configuración de la búsqueda
    max_tweets_requested = Column(Integer, default=100)
    tweets_retrieved = Column(Integer, default=0)
    time_window_days = Column(Integer, default=7)
    forecast_days = Column(Integer, default=14)
    language = Column(String(5), default="es")

    # Metadatos de la llamada
    fetched_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    processing_time_ms = Column(Integer)  # Tiempo de procesamiento
    twitter_query = Column(Text)  # Query enviado a Twitter
    api_version = Column(String(20), default="v2")

    # Estado
    status = Column(String(20), default="completed")  # pending, processing, completed, failed
    error_message = Column(Text)

    # Relaciones
    tweets = relationship("Tweet", back_populates="api_call", cascade="all, delete-orphan")
    analysis_snapshot = relationship("AnalysisSnapshot", back_populates="api_call", uselist=False, cascade="all, delete-orphan")
    pnd_metrics = relationship("PndAxisMetric", back_populates="api_call", cascade="all, delete-orphan")
    forecast_snapshot = relationship("ForecastSnapshot", back_populates="api_call", uselist=False, cascade="all, delete-orphan")
    campaign_strategy = relationship("CampaignStrategy", back_populates="api_call", uselist=False, cascade="all, delete-orphan")


class Tweet(Base):
    """
    Tweet individual recuperado de la API de Twitter.
    Almacena datos crudos + análisis de sentimiento y clasificación PND.
    """
    __tablename__ = "tweets"
    __table_args__ = (
        Index('ix_tweets_author_date', 'author_username', 'tweet_created_at'),
        Index('ix_tweets_sentiment', 'sentiment_positive', 'sentiment_negative'),
        Index('ix_tweets_pnd', 'pnd_topic', 'tweet_created_at'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    api_call_id = Column(String(36), ForeignKey("api_calls.id", ondelete="CASCADE"), nullable=False, index=True)

    # Datos de Twitter
    tweet_id = Column(String(30), nullable=False, index=True)  # ID de Twitter
    author_id = Column(String(30))
    author_username = Column(String(50), index=True)
    author_name = Column(String(100))
    author_verified = Column(Boolean, default=False)
    author_followers_count = Column(Integer, default=0)

    # Contenido
    content = Column(Text, nullable=False)
    content_cleaned = Column(Text)  # Texto limpio sin URLs/menciones
    tweet_created_at = Column(DateTime(timezone=True), index=True)
    language = Column(String(5))
    source = Column(String(100))  # Twitter Web App, iPhone, etc.

    # Métricas de engagement
    retweet_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    quote_count = Column(Integer, default=0)
    impression_count = Column(Integer, default=0)

    # Tipo de tweet
    is_retweet = Column(Boolean, default=False)
    is_reply = Column(Boolean, default=False)
    is_quote = Column(Boolean, default=False)
    replied_to_tweet_id = Column(String(30))
    quoted_tweet_id = Column(String(30))

    # Entidades extraídas
    hashtags = Column(JSON, default=list)  # ["elecciones2026", "Colombia"]
    mentions = Column(JSON, default=list)  # ["@usuario1", "@usuario2"]
    urls = Column(JSON, default=list)

    # Geolocalización (si disponible)
    geo_country = Column(String(50))
    geo_city = Column(String(100))
    geo_coordinates = Column(JSON)  # {"lat": x, "lon": y}

    # Análisis de sentimiento (BETO)
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)
    sentiment_label = Column(String(20))  # positivo, negativo, neutral
    sentiment_confidence = Column(Float, default=0.0)

    # Clasificación PND
    pnd_topic = Column(String(50), index=True)  # seguridad, educacion, salud, etc.
    pnd_confidence = Column(Float, default=0.0)
    pnd_secondary_topic = Column(String(50))  # Segundo tema más probable

    # Bot detection
    is_potential_bot = Column(Boolean, default=False)
    bot_score = Column(Float, default=0.0)

    # Metadatos de procesamiento
    processed_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relación
    api_call = relationship("ApiCall", back_populates="tweets")


class AnalysisSnapshot(Base, TimestampMixin):
    """
    Métricas agregadas del análisis (ICCE, SOV, SNA, etc.)
    Una por cada ApiCall.
    """
    __tablename__ = "analysis_snapshots"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    api_call_id = Column(String(36), ForeignKey("api_calls.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Métricas principales
    icce = Column(Float, default=0.0)  # Índice Compuesto de Capacidad Electoral (0-100)
    sov = Column(Float, default=0.0)   # Share of Voice (0-100%)
    sna = Column(Float, default=0.0)   # Sentimiento Neto Agregado (-100 a +100)
    momentum = Column(Float, default=0.0)  # Cambio de ICCE

    # Sentimiento global
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)

    # Resumen ejecutivo
    executive_summary = Column(Text)
    key_findings = Column(JSON, default=list)  # Lista de hallazgos clave
    key_stats = Column(JSON, default=list)     # ["ICCE 68.2", "Momentum +0.018", ...]
    recommendations = Column(JSON, default=list)

    # Trending topics detectados
    trending_topics = Column(JSON, default=list)

    # Distribución geográfica
    geo_distribution = Column(JSON, default=list)  # [{"name": "Bogotá", "weight": 0.32}, ...]

    # Insights adicionales
    opportunity = Column(Text)
    risk_level = Column(String(20))  # bajo, medio, alto
    risk_description = Column(Text)

    # Relación
    api_call = relationship("ApiCall", back_populates="analysis_snapshot")


class PndAxisMetric(Base):
    """
    Métricas por cada eje del Plan Nacional de Desarrollo.
    Múltiples registros por ApiCall (uno por eje).
    """
    __tablename__ = "pnd_axis_metrics"
    __table_args__ = (
        Index('ix_pnd_metrics_axis_date', 'pnd_axis', 'created_at'),
    )

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    api_call_id = Column(String(36), ForeignKey("api_calls.id", ondelete="CASCADE"), nullable=False, index=True)

    # Eje PND
    pnd_axis = Column(String(50), nullable=False, index=True)  # seguridad, educacion, salud, etc.
    pnd_axis_display = Column(String(100))  # "Seguridad", "Educación", etc.

    # Métricas del eje
    icce = Column(Float, default=0.0)
    sov = Column(Float, default=0.0)
    sna = Column(Float, default=0.0)
    tweet_count = Column(Integer, default=0)

    # Tendencia
    trend = Column(String(20))  # subiendo, bajando, estable
    trend_change = Column(Float, default=0.0)  # Cambio porcentual

    # Sentimiento del eje
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)

    # Insights del eje
    key_insights = Column(JSON, default=list)
    sample_tweets = Column(JSON, default=list)  # Tweets de ejemplo

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relación
    api_call = relationship("ApiCall", back_populates="pnd_metrics")


class ForecastSnapshot(Base, TimestampMixin):
    """
    Datos de forecast y series temporales.
    Una por cada ApiCall.
    """
    __tablename__ = "forecast_snapshots"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    api_call_id = Column(String(36), ForeignKey("api_calls.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Series históricas
    historical_dates = Column(JSON, default=list)      # ["2026-01-01", "2026-01-02", ...]
    icce_values = Column(JSON, default=list)           # [0.54, 0.56, 0.58, ...]
    icce_smooth = Column(JSON, default=list)           # Valores suavizados
    momentum_values = Column(JSON, default=list)       # Momentum por día

    # Series de pronóstico
    forecast_dates = Column(JSON, default=list)        # Fechas futuras
    icce_pred = Column(JSON, default=list)             # Predicción ICCE
    pred_low = Column(JSON, default=list)              # Límite inferior
    pred_high = Column(JSON, default=list)             # Límite superior

    # Configuración del modelo
    model_type = Column(String(50), default="holt_winters")
    model_confidence = Column(Float, default=0.0)
    days_back = Column(Integer, default=30)
    forecast_days = Column(Integer, default=14)

    # Predicción resumida
    icce_current = Column(Float, default=0.0)
    icce_predicted_end = Column(Float, default=0.0)
    icce_change_predicted = Column(Float, default=0.0)  # Cambio esperado en pts

    # Relación
    api_call = relationship("ApiCall", back_populates="forecast_snapshot")


class CampaignStrategy(Base, TimestampMixin):
    """
    Estrategias y contenido generado por IA.
    Una por cada ApiCall.
    """
    __tablename__ = "campaign_strategies"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    api_call_id = Column(String(36), ForeignKey("api_calls.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Análisis estratégico
    executive_summary = Column(Text)
    data_analysis = Column(Text)
    strategic_plan = Column(Text)
    general_analysis = Column(Text)

    # Discurso generado
    speech = Column(Text)
    speech_title = Column(String(255))
    speech_duration_minutes = Column(Integer, default=5)

    # Teoría de juegos
    game_main_move = Column(Text)
    game_alternatives = Column(JSON, default=list)
    game_rival_signal = Column(Text)
    game_trigger = Column(Text)
    game_payoff = Column(Text)
    game_confidence = Column(String(20))

    # Comparación con rival
    rival_name = Column(String(200))
    rival_comparison = Column(JSON)  # {labels: [...], campaign: [...], rival: [...]}
    gap_analysis = Column(JSON)      # {labels: [...], values: [...]}
    comparison_context = Column(JSON)

    # Ejes PND scores
    ejes_scores = Column(JSON)  # {seguridad: 72, educacion: 52, ...}

    # Drivers y riesgos
    drivers = Column(JSON, default=list)
    risks = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)

    # Plan de acción del día
    action_plan = Column(JSON, default=list)  # Lista de acciones priorizadas

    # Chart suggestions
    chart_suggestion = Column(Text)

    # Relación
    api_call = relationship("ApiCall", back_populates="campaign_strategy")
