"""
RAG Data Indexer for CASTOR ELECCIONES.
Handles indexing of tweets, PND metrics, and snapshots.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .rag_models import Document
from .rag_formatters import format_tweets_chunk
from .rag_formatters_pnd import format_pnd_summary, format_pnd_axis, format_analysis_snapshot

logger = logging.getLogger(__name__)


class DataIndexer:
    """Handles indexing of tweets, PND metrics, and snapshots."""

    def __init__(self, vector_store):
        """Initialize with vector store."""
        self.vector_store = vector_store

    def index_tweets(
        self,
        api_call_id: str,
        tweets: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index tweets grouped by PND topic."""
        if not tweets:
            return 0

        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        documents = self._create_tweet_documents(tweets, api_call_id, location, candidate, date)

        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Indexed {len(documents)} tweet documents for API call {api_call_id}")

        return len(documents)

    def _create_tweet_documents(
        self,
        tweets: List[Dict],
        api_call_id: str,
        location: str,
        candidate: str,
        date: str
    ) -> List[Document]:
        """Create documents from tweets grouped by topic."""
        tweets_by_topic = self._group_tweets_by_topic(tweets)
        documents = []

        for topic, topic_tweets in tweets_by_topic.items():
            chunk_docs = self._chunk_topic_tweets(
                topic_tweets, topic, api_call_id, location, candidate, date
            )
            documents.extend(chunk_docs)

        return documents

    def _group_tweets_by_topic(self, tweets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group tweets by PND topic."""
        tweets_by_topic: Dict[str, List[Dict]] = {}
        for tweet in tweets:
            topic = tweet.get("pnd_topic", "general") or "general"
            if topic not in tweets_by_topic:
                tweets_by_topic[topic] = []
            tweets_by_topic[topic].append(tweet)
        return tweets_by_topic

    def _chunk_topic_tweets(
        self,
        tweets: List[Dict],
        topic: str,
        api_call_id: str,
        location: str,
        candidate: str,
        date: str
    ) -> List[Document]:
        """Create documents from tweets in chunks of 10."""
        documents = []
        chunk_size = 10

        for i in range(0, len(tweets), chunk_size):
            chunk = tweets[i:i + chunk_size]
            doc = self._create_tweet_chunk_doc(chunk, topic, api_call_id, i // chunk_size, location, candidate, date)
            documents.append(doc)

        return documents

    def _create_tweet_chunk_doc(
        self,
        chunk: List[Dict],
        topic: str,
        api_call_id: str,
        chunk_idx: int,
        location: str,
        candidate: str,
        date: str
    ) -> Document:
        """Create a single document from a chunk of tweets."""
        pos_count = sum(1 for t in chunk if 'positiv' in (t.get('sentiment_label') or '').lower())
        neg_count = sum(1 for t in chunk if 'negativ' in (t.get('sentiment_label') or '').lower())

        return Document(
            id=f"{api_call_id}_tweets_{topic}_{chunk_idx}",
            content=format_tweets_chunk(chunk, topic, location, date, candidate),
            metadata={
                "api_call_id": api_call_id,
                "type": "tweets",
                "chunk_type": "tweets",
                "pnd_topic": topic,
                "location": location,
                "candidate": candidate,
                "tweet_count": len(chunk),
                "sentiment_positive_count": pos_count,
                "sentiment_negative_count": neg_count,
                "created_at": date
            }
        )

    def index_pnd_metrics(
        self,
        api_call_id: str,
        pnd_metrics: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index PND metrics."""
        if not pnd_metrics:
            return 0

        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        documents = [self._create_pnd_summary_doc(pnd_metrics, api_call_id, location, candidate, date)]
        documents.extend([self._create_pnd_axis_doc(m, api_call_id, location, candidate, date) for m in pnd_metrics])

        self.vector_store.add_documents(documents)
        logger.info(f"Indexed {len(documents)} PND metric documents for API call {api_call_id}")

        return len(documents)

    def _create_pnd_summary_doc(
        self, metrics: List[Dict], api_call_id: str, location: str, candidate: str, date: str
    ) -> Document:
        """Create PND summary document."""
        return Document(
            id=f"{api_call_id}_pnd_summary",
            content=format_pnd_summary(metrics, location, date, candidate),
            metadata={
                "api_call_id": api_call_id,
                "type": "pnd_metrics",
                "chunk_type": "pnd_summary",
                "location": location,
                "candidate": candidate,
                "created_at": date
            }
        )

    def _create_pnd_axis_doc(
        self, metric: Dict, api_call_id: str, location: str, candidate: str, date: str
    ) -> Document:
        """Create individual PND axis document."""
        axis = metric.get('pnd_axis_display', metric.get('pnd_axis', 'Desconocido'))
        axis_key = metric.get('pnd_axis', axis.lower().replace(' ', '_'))

        return Document(
            id=f"{api_call_id}_pnd_{axis_key}",
            content=format_pnd_axis(metric, location, date, candidate),
            metadata={
                "api_call_id": api_call_id,
                "type": "pnd_metrics",
                "chunk_type": "pnd_axis",
                "pnd_axis": axis_key,
                "pnd_axis_display": axis,
                "icce": metric.get('icce', 0),
                "sov": metric.get('sov', 0),
                "sna": metric.get('sna', 0),
                "location": location,
                "candidate": candidate,
                "created_at": date
            }
        )

    def index_analysis_snapshot(
        self,
        api_call_id: str,
        snapshot: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index analysis snapshot."""
        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        doc = Document(
            id=f"{api_call_id}_snapshot",
            content=format_analysis_snapshot(snapshot, location, date, candidate),
            metadata={
                "api_call_id": api_call_id,
                "type": "analysis_snapshot",
                "chunk_type": "executive_summary",
                "icce": snapshot.get('icce', 50),
                "sov": snapshot.get('sov', 0),
                "sna": snapshot.get('sna', 0),
                "momentum": snapshot.get('momentum', 0),
                "location": location,
                "candidate": candidate,
                "created_at": date
            }
        )

        self.vector_store.add_documents([doc])
        logger.info(f"Indexed analysis snapshot for API call {api_call_id}")

        return 1
