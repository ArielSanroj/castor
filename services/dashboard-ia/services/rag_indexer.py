"""
RAG Indexer for CASTOR ELECCIONES.
Handles indexing of analyses into the vector store.
"""
import logging
from typing import Any, Dict, List, Optional

from .rag_models import Document
from .rag_formatters import (
    format_executive_summary,
    format_topic,
    format_sentiment,
    format_strategic_plan,
    format_speech,
    format_metadata
)
from .rag_indexer_data import DataIndexer

logger = logging.getLogger(__name__)


class RAGIndexer:
    """Handles indexing operations for the RAG system."""

    def __init__(self, vector_store):
        """
        Initialize indexer with vector store.

        Args:
            vector_store: SQLiteVectorStore instance
        """
        self.vector_store = vector_store
        self._data_indexer = DataIndexer(vector_store)

    def index_analysis(
        self,
        analysis_id: str,
        analysis_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Index an analysis into the vector store.

        Returns:
            List of document IDs created
        """
        documents = self._chunk_analysis(analysis_id, analysis_data, metadata or {})
        self.vector_store.add_documents(documents)

        logger.info(f"Indexed analysis {analysis_id}: {len(documents)} documents")
        return [doc.id for doc in documents]

    def _chunk_analysis(
        self,
        analysis_id: str,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Break down an analysis into indexable chunks."""
        documents = []
        base_meta = {"analysis_id": analysis_id, "type": "analysis", **metadata}

        location = metadata.get("location", data.get("metadata", {}).get("location", "Colombia"))
        created_at = metadata.get("created_at", "fecha no especificada")

        documents.extend(self._chunk_executive_summary(data, base_meta, location, created_at, analysis_id))
        documents.extend(self._chunk_topics(data, base_meta, location, created_at, analysis_id))
        documents.extend(self._chunk_sentiment(data, base_meta, location, created_at, analysis_id))
        documents.extend(self._chunk_strategy(data, base_meta, location, created_at, analysis_id))
        documents.extend(self._chunk_speech(data, base_meta, location, created_at, analysis_id))
        documents.extend(self._chunk_metadata(data, base_meta, location, created_at, analysis_id))

        return documents

    def _chunk_executive_summary(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract executive summary document."""
        exec_summary = data.get("executive_summary", {})
        if not exec_summary:
            return []

        return [Document(
            id=f"{analysis_id}_summary",
            content=format_executive_summary(exec_summary, location, date),
            metadata={**base_meta, "chunk_type": "executive_summary"}
        )]

    def _chunk_topics(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract topic documents."""
        documents = []
        topics = data.get("topics", data.get("topic_analyses", []))

        for i, topic in enumerate(topics):
            if isinstance(topic, dict):
                topic_name = topic.get("topic", f"topic_{i}")
                documents.append(Document(
                    id=f"{analysis_id}_topic_{i}",
                    content=format_topic(topic, location, date),
                    metadata={**base_meta, "chunk_type": "topic", "topic_name": topic_name}
                ))

        return documents

    def _chunk_sentiment(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract sentiment document."""
        sentiment = data.get("sentiment_overview")
        if not sentiment:
            return []

        return [Document(
            id=f"{analysis_id}_sentiment",
            content=format_sentiment(sentiment, location, date),
            metadata={**base_meta, "chunk_type": "sentiment"}
        )]

    def _chunk_strategy(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract strategic plan document."""
        plan = data.get("strategic_plan")
        if not plan:
            return []

        return [Document(
            id=f"{analysis_id}_strategy",
            content=format_strategic_plan(plan, location, date),
            metadata={**base_meta, "chunk_type": "strategic_plan"}
        )]

    def _chunk_speech(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract speech document."""
        speech = data.get("speech")
        if not speech:
            return []

        return [Document(
            id=f"{analysis_id}_speech",
            content=format_speech(speech, location, date),
            metadata={**base_meta, "chunk_type": "speech"}
        )]

    def _chunk_metadata(
        self, data: Dict, base_meta: Dict, location: str, date: str, analysis_id: str
    ) -> List[Document]:
        """Extract metadata document."""
        meta = data.get("metadata", {})
        if not meta:
            return []

        return [Document(
            id=f"{analysis_id}_meta",
            content=format_metadata(meta, location, date),
            metadata={**base_meta, "chunk_type": "metadata"}
        )]

    # Delegate data indexing methods
    def index_tweets(self, api_call_id: str, tweets: List[Dict], metadata: Dict = None) -> int:
        """Index tweets grouped by PND topic."""
        return self._data_indexer.index_tweets(api_call_id, tweets, metadata)

    def index_pnd_metrics(self, api_call_id: str, pnd_metrics: List[Dict], metadata: Dict = None) -> int:
        """Index PND metrics."""
        return self._data_indexer.index_pnd_metrics(api_call_id, pnd_metrics, metadata)

    def index_analysis_snapshot(self, api_call_id: str, snapshot: Dict, metadata: Dict = None) -> int:
        """Index analysis snapshot."""
        return self._data_indexer.index_analysis_snapshot(api_call_id, snapshot, metadata)
