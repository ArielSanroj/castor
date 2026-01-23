from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.schemas.core import (
    CoreAnalysisResult,
    SentimentOverview,
    TopicAnalysis,
    PeakEvent,
    ChartData,
    TweetData,
)
from app.services.narrative_metrics_service import NarrativeMetricsService
from services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


class AnalysisCorePipeline:
    """
    Core pipeline reused by media and campaign products.
    Reuses existing services to avoid behavior changes.
    """

    def __init__(
        self,
        twitter_service,
        sentiment_service,
        trending_service,
        topic_classifier_service,
        chart_service,
        db_service=None,
    ):
        self.twitter_service = twitter_service
        self.sentiment_service = sentiment_service
        self.trending_service = trending_service
        self.topic_classifier_service = topic_classifier_service
        self.chart_service = chart_service
        self.db_service = db_service
        self.narrative_metrics = NarrativeMetricsService()

    def run_core_pipeline(
        self,
        *,
        location: str,
        topic: Optional[str],
        candidate_name: Optional[str],
        politician: Optional[str],
        max_tweets: int,
        time_window_days: int,
        language: str = "es",
    ) -> CoreAnalysisResult:
        import time
        start_time = time.time()

        now = datetime.utcnow()
        time_from = now - timedelta(days=time_window_days)
        time_to = now

        # Crear registro de API call en la BD
        api_call = None
        if self.db_service:
            try:
                api_call = self.db_service.create_api_call(
                    location=location,
                    candidate_name=candidate_name,
                    politician=politician.lstrip('@') if politician else None,
                    topic=topic,
                    max_tweets_requested=max_tweets,
                    time_window_days=time_window_days,
                    language=language
                )
            except Exception as exc:
                logger.warning(f"Could not create API call record: {exc}")

        trending_topic = None
        try:
            trending_topic = self.trending_service.get_trending_for_speech(
                location=location,
                candidate_name=candidate_name or "el candidato",
            )
        except Exception as exc:
            logger.warning(f"Trending service unavailable: {exc}")

        raw_query = self._build_query(
            location=location,
            topic=topic,
            candidate_name=candidate_name,
            politician=politician,
            language=language,
        )

        tweets = self.twitter_service.search_by_pnd_topic(
            topic=topic or "todos",
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            max_results=max_tweets,
        )

        if not tweets:
            empty_sentiment = SentimentOverview(
                positive=0.0, neutral=0.0, negative=0.0
            )
            empty_chart = ChartData(
                by_topic_sentiment={},
                volume_over_time={},
                sentiment_overall={},
                peaks_over_time={},
            )
            return CoreAnalysisResult(
                tweets_analyzed=0,
                location=location,
                topic=topic,
                time_window_from=time_from,
                time_window_to=time_to,
                sentiment_overview=empty_sentiment,
                topics=[],
                peaks=[],
                chart_data=empty_chart,
                trending_topic=trending_topic.get("topic") if (trending_topic and isinstance(trending_topic, dict)) else None,
                raw_query=raw_query,
            )

        tweets_with_sentiment = self.sentiment_service.analyze_tweets(tweets)

        topics_analysis = self.topic_classifier_service.classify_tweets_by_pnd_topic(
            tweets_with_sentiment,
            theme=topic or "Todos",
        )

        sentiment_overview = self._build_sentiment_overview(tweets_with_sentiment)

        peaks: List[PeakEvent] = []

        chart_data = self.chart_service.generate_charts(
            topics_analysis=topics_analysis,
            sentiment_overview=sentiment_overview,
            tweets=tweets_with_sentiment,
            peaks=peaks,
        )

        # Calculate narrative metrics if candidate_name is provided
        narrative_metrics_result = None
        if candidate_name:
            try:
                sentiment_scores = [
                    {
                        "positive": t.get("sentiment", {}).get("positive", 0.0),
                        "negative": t.get("sentiment", {}).get("negative", 0.0),
                        "neutral": t.get("sentiment", {}).get("neutral", 0.0)
                    }
                    for t in tweets_with_sentiment
                ]
                narrative_metrics_result = self.narrative_metrics.calculate_all_metrics(
                    tweets=tweets_with_sentiment,
                    sentiment_scores=sentiment_scores,
                    candidate_name=candidate_name,
                    topic=topic
                )
            except Exception as exc:
                logger.warning(f"Could not calculate narrative metrics: {exc}")

        # Convert tweets to TweetData for frontend display
        tweets_data = [
            TweetData(
                tweet_id=t.get('tweet_id', ''),
                author_username=t.get('author_username', ''),
                author_name=t.get('author_name'),
                content=t.get('content', ''),
                sentiment_label=t.get('dominant_sentiment') or t.get('sentiment_label'),
                pnd_topic=t.get('pnd_topic'),
                retweet_count=t.get('retweet_count', 0),
                like_count=t.get('like_count', 0),
                reply_count=t.get('reply_count', 0),
            )
            for t in tweets_with_sentiment[:100]  # Limit to 100 tweets for response size
        ]

        core_result = CoreAnalysisResult(
            tweets_analyzed=len(tweets_with_sentiment),
            location=location,
            topic=topic,
            time_window_from=time_from,
            time_window_to=time_to,
            sentiment_overview=sentiment_overview,
            topics=topics_analysis,
            peaks=peaks,
            chart_data=chart_data,
            tweets_data=tweets_data,
            trending_topic=trending_topic.get("topic") if (trending_topic and isinstance(trending_topic, dict)) else None,
            raw_query=raw_query,
        )

        # Attach narrative metrics to result (will be used by forecast endpoints)
        if narrative_metrics_result:
            core_result.narrative_metrics = narrative_metrics_result  # type: ignore

        # Guardar en BD si tenemos api_call
        if api_call and self.db_service:
            try:
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Preparar tweets para guardar (mapear dominant_sentiment a sentiment_label)
                tweets_to_save = []
                for t in tweets_with_sentiment:
                    tweet_copy = dict(t)
                    # Asegurar que sentiment_label esté presente
                    if not tweet_copy.get('sentiment_label') and tweet_copy.get('dominant_sentiment'):
                        tweet_copy['sentiment_label'] = tweet_copy['dominant_sentiment']
                    tweets_to_save.append(tweet_copy)

                # Guardar tweets
                self.db_service.save_tweets(api_call.id, tweets_to_save)

                # Guardar analysis snapshot
                snapshot_data = {
                    'icce': narrative_metrics_result.get('icce', 50) if narrative_metrics_result else 50,
                    'sov': narrative_metrics_result.get('sov', 0) if narrative_metrics_result else 0,
                    'sna': narrative_metrics_result.get('sna', 0) if narrative_metrics_result else 0,
                    'momentum': narrative_metrics_result.get('momentum', 0) if narrative_metrics_result else 0,
                    'sentiment_positive': sentiment_overview.positive,
                    'sentiment_negative': sentiment_overview.negative,
                    'sentiment_neutral': sentiment_overview.neutral,
                    'key_findings': [],
                    'executive_summary': f"Análisis de {len(tweets_with_sentiment)} tweets sobre {candidate_name or 'tema general'}",
                    'trending_topics': [trending_topic.get("topic")] if trending_topic and isinstance(trending_topic, dict) else []
                }
                self.db_service.save_analysis_snapshot(api_call.id, snapshot_data)

                # Guardar PND metrics (métricas por eje temático)
                if topics_analysis:
                    pnd_metrics_to_save = []
                    for topic_data in topics_analysis:
                        # topic_data puede ser TopicAnalysis o dict
                        if hasattr(topic_data, 'model_dump'):
                            td = topic_data.model_dump()
                        elif hasattr(topic_data, 'dict'):
                            td = topic_data.dict()
                        else:
                            td = topic_data if isinstance(topic_data, dict) else {}

                        topic_name = td.get('topic', '')
                        sentiment_data = td.get('sentiment', {})

                        # Calcular métricas para este eje
                        topic_tweets = [t for t in tweets_with_sentiment
                                       if t.get('pnd_topic', '').lower() == topic_name.lower()]
                        topic_tweet_count = len(topic_tweets) if topic_tweets else td.get('tweet_count', 0)

                        # Calcular SNA para este tema
                        pos = sentiment_data.get('positive', 0.33) if isinstance(sentiment_data, dict) else 0.33
                        neg = sentiment_data.get('negative', 0.33) if isinstance(sentiment_data, dict) else 0.33
                        topic_sna = (pos - neg) * 100

                        # ICCE estimado basado en sentimiento y volumen
                        base_icce = 50 + topic_sna * 0.3
                        volume_bonus = min(topic_tweet_count / 10, 15)
                        topic_icce = max(20, min(95, base_icce + volume_bonus))

                        # SOV (share of voice) como porcentaje del total
                        total_tweets = len(tweets_with_sentiment) if tweets_with_sentiment else 1
                        topic_sov = (topic_tweet_count / total_tweets) * 100

                        pnd_metrics_to_save.append({
                            'pnd_axis': topic_name.lower().replace(' ', '_'),
                            'pnd_axis_display': topic_name,
                            'icce': round(topic_icce, 1),
                            'sov': round(topic_sov, 1),
                            'sna': round(topic_sna, 1),
                            'tweet_count': topic_tweet_count,
                            'trend': 'stable' if abs(topic_sna) < 10 else ('up' if topic_sna > 0 else 'down'),
                            'trend_change': 0.0,
                            'sentiment_positive': pos,
                            'sentiment_negative': neg,
                            'sentiment_neutral': sentiment_data.get('neutral', 0.34) if isinstance(sentiment_data, dict) else 0.34,
                            'key_insights': [],
                            'sample_tweets': [t.get('content', '')[:200] for t in topic_tweets[:3]]
                        })

                    if pnd_metrics_to_save:
                        self.db_service.save_pnd_metrics(api_call.id, pnd_metrics_to_save)
                        logger.info(f"Saved {len(pnd_metrics_to_save)} PND metrics for API call {api_call.id}")

                # Actualizar status
                self.db_service.update_api_call_status(
                    api_call_id=api_call.id,
                    status="completed",
                    tweets_retrieved=len(tweets_with_sentiment),
                    processing_time_ms=processing_time_ms
                )
                logger.info(f"API call {api_call.id} saved with {len(tweets_with_sentiment)} tweets")

                # =====================================================
                # INDEXAR EN RAG PARA BÚSQUEDA SEMÁNTICA Y CHAT
                # =====================================================
                try:
                    rag_service = get_rag_service()
                    rag_metadata = {
                        "location": location,
                        "candidate_name": candidate_name,
                        "politician": politician,
                        "topic": topic,
                        "created_at": datetime.utcnow().isoformat()
                    }

                    # 1. Indexar snapshot de análisis
                    rag_service.index_analysis_snapshot(
                        api_call_id=api_call.id,
                        snapshot=snapshot_data,
                        metadata=rag_metadata
                    )

                    # 2. Indexar tweets (agrupados por tema)
                    rag_service.index_tweets(
                        api_call_id=api_call.id,
                        tweets=tweets_to_save,
                        metadata=rag_metadata
                    )

                    # 3. Indexar métricas PND
                    if pnd_metrics_to_save:
                        rag_service.index_pnd_metrics(
                            api_call_id=api_call.id,
                            pnd_metrics=pnd_metrics_to_save,
                            metadata=rag_metadata
                        )

                    logger.info(f"RAG indexing completed for API call {api_call.id}")

                except Exception as rag_exc:
                    # RAG indexing failure should not break the main flow
                    logger.warning(f"RAG indexing failed (non-critical): {rag_exc}")
            except Exception as exc:
                logger.error(f"Error saving API call data: {exc}", exc_info=True)
                if api_call:
                    self.db_service.update_api_call_status(
                        api_call_id=api_call.id,
                        status="failed",
                        error_message=str(exc)
                    )

        return core_result

    def _build_query(
        self,
        *,
        location: str,
        topic: Optional[str],
        candidate_name: Optional[str],
        politician: Optional[str],
        language: str,
    ) -> str:
        parts = []

        if location:
            parts.append(location)

        if topic:
            topic_query = self.topic_classifier_service.build_topic_query(topic)
            if topic_query:
                parts.append(f"({topic_query})")

        if candidate_name:
            parts.append(candidate_name)

        if politician:
            parts.append(politician)

        if language:
            parts.append(f"lang:{language}")

        return " ".join(parts)

    def _build_sentiment_overview(self, tweets: List[Dict[str, Any]]) -> SentimentOverview:
        total = len(tweets)
        if total == 0:
            return SentimentOverview(positive=0.0, neutral=0.0, negative=0.0)

        pos = sum(1 for t in tweets if t.get("dominant_sentiment") == "positivo")
        neu = sum(1 for t in tweets if t.get("dominant_sentiment") == "neutral")
        neg = sum(1 for t in tweets if t.get("dominant_sentiment") == "negativo")

        return SentimentOverview(
            positive=pos / total,
            neutral=neu / total,
            negative=neg / total,
        )
