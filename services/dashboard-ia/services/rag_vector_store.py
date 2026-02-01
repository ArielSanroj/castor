"""
SQLite Vector Store for CASTOR ELECCIONES RAG.
Persistent storage for documents and embeddings.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .rag_models import Document, RetrievalResult, cosine_similarity

logger = logging.getLogger(__name__)


class SQLiteVectorStore:
    """
    Persistent vector store using SQLite.
    Stores documents and embeddings locally.
    """

    def __init__(self, db_path: str = None, openai_client=None, embedding_model: str = None):
        """
        Initialize SQLite vector store.

        Args:
            db_path: SQLite file path
            openai_client: OpenAI client for embeddings
            embedding_model: Embedding model name
        """
        self.db_path = db_path or self._default_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.openai_client = openai_client
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self._init_db()
        logger.info(f"SQLite RAG store initialized at {self.db_path}")

    def _default_db_path(self) -> str:
        """Get default database path."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "rag_store.sqlite3"
        )

    def _init_db(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_created_at ON rag_documents(created_at)")

    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata values for JSON serialization."""
        normalized = {}
        for key, value in metadata.items():
            if isinstance(value, datetime):
                normalized[key] = value.isoformat()
            elif isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            elif value is None:
                normalized[key] = ""
            else:
                normalized[key] = json.dumps(value, ensure_ascii=False)
        return normalized

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for texts via OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured for embeddings")
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]

    def add_document(self, doc: Document, embedding: List[float] = None) -> None:
        """Add single document to store."""
        self.add_documents([doc], embeddings=[embedding] if embedding else None)

    def add_documents(self, docs: List[Document], embeddings: List[List[float]] = None) -> None:
        """Add multiple documents to store."""
        if not docs:
            return

        if embeddings is None:
            embeddings = self._embed_texts([doc.content for doc in docs])

        with sqlite3.connect(self.db_path) as conn:
            for doc, emb in zip(docs, embeddings):
                metadata = self._normalize_metadata(doc.metadata)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rag_documents (id, content, metadata, embedding, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        doc.id,
                        doc.content,
                        json.dumps(metadata, ensure_ascii=False),
                        json.dumps(emb),
                        doc.created_at.isoformat()
                    )
                )
            conn.commit()

    def _matches_where(self, metadata: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
        """Check if metadata matches where clause."""
        if not where:
            return True
        if "$and" in where:
            return all(self._matches_where(metadata, cond) for cond in where["$and"])
        for key, value in where.items():
            if metadata.get(key) != value:
                return False
        return True

    def search(self, query_text: str, top_k: int = 5, where: Dict[str, Any] = None) -> List[RetrievalResult]:
        """Search for similar documents."""
        try:
            query_embedding = self._embed_texts([query_text])[0]
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

        results = self._search_by_embedding(query_embedding, where)
        return self._rank_results(results, top_k)

    def _search_by_embedding(
        self,
        query_embedding: List[float],
        where: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """Search documents by embedding similarity."""
        results: List[RetrievalResult] = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, content, metadata, embedding, created_at FROM rag_documents")
            rows = cursor.fetchall()

        for row in rows:
            doc_id, content, metadata_json, embedding_json, created_at = row
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
                if not self._matches_where(metadata, where):
                    continue
                embedding = json.loads(embedding_json) if embedding_json else []
            except Exception:
                continue

            score = cosine_similarity(query_embedding, embedding)
            doc = Document(
                id=doc_id,
                content=content,
                metadata=metadata,
                created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(timezone.utc)
            )
            results.append(RetrievalResult(document=doc, score=score, rank=0))

        return results

    def _rank_results(self, results: List[RetrievalResult], top_k: int) -> List[RetrievalResult]:
        """Sort and rank results by score."""
        results.sort(key=lambda r: r.score, reverse=True)
        for idx, result in enumerate(results[:top_k], start=1):
            result.rank = idx
        return results[:top_k]

    def count(self) -> int:
        """Count total documents in store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(1) FROM rag_documents")
            return int(cursor.fetchone()[0])

    def delete(self, doc_ids: List[str]) -> None:
        """Delete documents by ID."""
        if not doc_ids:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("DELETE FROM rag_documents WHERE id = ?", [(doc_id,) for doc_id in doc_ids])
            conn.commit()

    def clear(self) -> None:
        """Clear all documents from store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM rag_documents")
            conn.commit()
