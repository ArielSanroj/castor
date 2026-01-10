"""
RAG (Retrieval Augmented Generation) Service for CASTOR ELECCIONES.
Uses SQLite for persistent vector storage and integrates with historical data.
"""
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import math

import openai

from config import Config

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A document in the RAG knowledge base."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RetrievalResult:
    """Result from retrieval with similarity score."""
    document: Document
    score: float
    rank: int


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "rag_store.sqlite3"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.openai_client = openai_client
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self._init_db()
        logger.info(f"SQLite RAG store initialized at {self.db_path}")

    def _init_db(self) -> None:
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
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured for embeddings")
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]

    def add_document(self, doc: Document, embedding: List[float] = None) -> None:
        self.add_documents([doc], embeddings=[embedding] if embedding else None)

    def add_documents(self, docs: List[Document], embeddings: List[List[float]] = None) -> None:
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
        if not where:
            return True
        if "$and" in where:
            return all(self._matches_where(metadata, cond) for cond in where["$and"])
        for key, value in where.items():
            if metadata.get(key) != value:
                return False
        return True

    def search(self, query_text: str, top_k: int = 5, where: Dict[str, Any] = None) -> List[RetrievalResult]:
        try:
            query_embedding = self._embed_texts([query_text])[0]
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

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

            score = _cosine_similarity(query_embedding, embedding)
            doc = Document(
                id=doc_id,
                content=content,
                metadata=metadata,
                created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(timezone.utc)
            )
            results.append(RetrievalResult(document=doc, score=score, rank=0))

        results.sort(key=lambda r: r.score, reverse=True)
        for idx, result in enumerate(results[:top_k], start=1):
            result.rank = idx
        return results[:top_k]

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(1) FROM rag_documents")
            return int(cursor.fetchone()[0])

    def delete(self, doc_ids: List[str]) -> None:
        if not doc_ids:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("DELETE FROM rag_documents WHERE id = ?", [(doc_id,) for doc_id in doc_ids])
            conn.commit()

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM rag_documents")
            conn.commit()


class RAGService:
    """
    Main RAG service combining retrieval and generation.
    Uses SQLite for persistence and integrates with database history.
    """

    def __init__(self, db_service=None):
        """
        Initialize RAG service.

        Args:
            db_service: Optional DatabaseService for loading historical data
        """
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.vector_store = SQLiteVectorStore(
            openai_client=self.openai_client,
            embedding_model=getattr(Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )
        self.model = Config.OPENAI_MODEL
        self.db_service = db_service

        # System prompt for RAG
        self.system_prompt = """Eres CASTOR AI, un asistente experto en análisis electoral y campañas políticas en Colombia.

Tu rol es responder preguntas usando el CONTEXTO proporcionado de análisis históricos guardados.

Reglas:
1. Basa tus respuestas PRINCIPALMENTE en el contexto proporcionado (datos históricos reales)
2. Menciona fechas, ubicaciones y datos específicos cuando estén disponibles
3. Si el contexto no tiene información suficiente, indícalo y sugiere qué análisis realizar
4. Responde en español, de manera concisa y profesional
5. Da recomendaciones accionables basadas en los datos históricos
6. Compara tendencias entre diferentes análisis si es relevante
7. No inventes datos - solo usa lo que está en el contexto"""

        logger.info(f"RAGService initialized with SQLite ({self.vector_store.count()} documents)")

    def set_db_service(self, db_service) -> None:
        """Set database service for historical data access."""
        self.db_service = db_service

    def sync_from_database(self, limit: int = 100) -> int:
        """
        Sync historical analyses from database to vector store.

        Args:
            limit: Maximum number of analyses to sync

        Returns:
            Number of documents indexed
        """
        if not self.db_service:
            logger.warning("No database service configured for RAG sync")
            return 0

        try:
            # Get all historical analyses
            analyses = self.db_service.get_all_analyses(limit=limit)

            indexed_count = 0
            for analysis in analyses:
                try:
                    analysis_id = analysis.get('id') or str(analysis.get('created_at', ''))
                    analysis_data = analysis.get('analysis_data', {})

                    if analysis_data:
                        doc_ids = self.index_analysis(
                            analysis_id=analysis_id,
                            analysis_data=analysis_data,
                            metadata={
                                "location": analysis.get('location'),
                                "theme": analysis.get('theme'),
                                "candidate": analysis.get('candidate_name'),
                                "created_at": str(analysis.get('created_at', '')),
                                "user_id": analysis.get('user_id')
                            }
                        )
                        indexed_count += len(doc_ids)

                except Exception as e:
                    logger.warning(f"Error syncing analysis {analysis.get('id')}: {e}")

            logger.info(f"Synced {indexed_count} documents from database")
            return indexed_count

        except Exception as e:
            logger.error(f"Error syncing from database: {e}")
            return 0

    def index_analysis(
        self,
        analysis_id: str,
        analysis_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Index an analysis into the vector store.

        Args:
            analysis_id: Unique identifier
            analysis_data: Analysis data to index
            metadata: Additional metadata

        Returns:
            List of document IDs created
        """
        documents = self._chunk_analysis(analysis_id, analysis_data, metadata or {})

        # Add to SQLite store (embeddings computed via OpenAI)
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
        base_meta = {
            "analysis_id": analysis_id,
            "type": "analysis",
            **metadata
        }

        # Get location and date for context
        location = metadata.get("location", data.get("metadata", {}).get("location", "Colombia"))
        created_at = metadata.get("created_at", "fecha no especificada")

        # 1. Index executive summary
        exec_summary = data.get("executive_summary", {})
        if exec_summary:
            content = self._format_executive_summary(exec_summary, location, created_at)
            documents.append(Document(
                id=f"{analysis_id}_summary",
                content=content,
                metadata={**base_meta, "chunk_type": "executive_summary"}
            ))

        # 2. Index each topic analysis
        topics = data.get("topics", data.get("topic_analyses", []))
        for i, topic in enumerate(topics):
            if isinstance(topic, dict):
                content = self._format_topic(topic, location, created_at)
                topic_name = topic.get("topic", f"topic_{i}")
                documents.append(Document(
                    id=f"{analysis_id}_topic_{i}",
                    content=content,
                    metadata={
                        **base_meta,
                        "chunk_type": "topic",
                        "topic_name": topic_name
                    }
                ))

        # 3. Index sentiment overview
        sentiment = data.get("sentiment_overview")
        if sentiment:
            content = self._format_sentiment(sentiment, location, created_at)
            documents.append(Document(
                id=f"{analysis_id}_sentiment",
                content=content,
                metadata={**base_meta, "chunk_type": "sentiment"}
            ))

        # 4. Index strategic plan
        plan = data.get("strategic_plan")
        if plan:
            content = self._format_strategic_plan(plan, location, created_at)
            documents.append(Document(
                id=f"{analysis_id}_strategy",
                content=content,
                metadata={**base_meta, "chunk_type": "strategic_plan"}
            ))

        # 5. Index speech if present
        speech = data.get("speech")
        if speech:
            content = self._format_speech(speech, location, created_at)
            documents.append(Document(
                id=f"{analysis_id}_speech",
                content=content,
                metadata={**base_meta, "chunk_type": "speech"}
            ))

        # 6. Index metadata summary
        meta = data.get("metadata", {})
        if meta:
            content = self._format_metadata(meta, location, created_at)
            documents.append(Document(
                id=f"{analysis_id}_meta",
                content=content,
                metadata={**base_meta, "chunk_type": "metadata"}
            ))

        return documents

    def _format_executive_summary(self, summary: Dict, location: str, date: str) -> str:
        """Format executive summary for indexing."""
        parts = [f"RESUMEN EJECUTIVO - Análisis de {location} ({date}):"]

        if summary.get("overview"):
            parts.append(f"Visión general: {summary['overview']}")

        findings = summary.get("key_findings", [])
        if findings:
            parts.append("Hallazgos clave:")
            for f in findings[:5]:
                parts.append(f"- {f}")

        recommendations = summary.get("recommendations", [])
        if recommendations:
            parts.append("Recomendaciones estratégicas:")
            for r in recommendations[:5]:
                parts.append(f"- {r}")

        return "\n".join(parts)

    def _format_topic(self, topic: Dict, location: str, date: str) -> str:
        """Format topic analysis for indexing."""
        topic_name = topic.get("topic", "Sin nombre")
        parts = [f"ANÁLISIS DE TEMA: {topic_name} en {location} ({date})"]

        sentiment = topic.get("sentiment", {})
        if sentiment:
            pos = sentiment.get("positive", 0) * 100
            neg = sentiment.get("negative", 0) * 100
            neu = sentiment.get("neutral", 0) * 100
            parts.append(f"Sentimiento: {pos:.1f}% positivo, {neu:.1f}% neutral, {neg:.1f}% negativo")

        count = topic.get("tweet_count", 0)
        if count:
            parts.append(f"Menciones analizadas: {count}")

        insights = topic.get("key_insights", [])
        if insights:
            parts.append("Insights principales:")
            for insight in insights[:5]:
                parts.append(f"- {insight}")

        return "\n".join(parts)

    def _format_sentiment(self, sentiment: Dict, location: str, date: str) -> str:
        """Format sentiment overview."""
        pos = sentiment.get("positive", 0) * 100
        neg = sentiment.get("negative", 0) * 100
        neu = sentiment.get("neutral", 0) * 100

        tone = "Favorable" if pos > neg + 10 else "Crítico" if neg > pos + 10 else "Mixto"

        return f"""ANÁLISIS DE SENTIMIENTO GENERAL - {location} ({date}):
Sentimiento positivo: {pos:.1f}%
Sentimiento neutral: {neu:.1f}%
Sentimiento negativo: {neg:.1f}%
Tono general de la conversación: {tone}
Interpretación: {'La percepción ciudadana es mayormente favorable' if pos > 50 else 'Existen preocupaciones significativas en la ciudadanía' if neg > 40 else 'La opinión está dividida'}"""

    def _format_strategic_plan(self, plan: Dict, location: str, date: str) -> str:
        """Format strategic plan."""
        parts = [f"PLAN ESTRATÉGICO - {location} ({date}):"]

        objectives = plan.get("objectives", [])
        if objectives:
            parts.append("Objetivos estratégicos:")
            for obj in objectives[:5]:
                parts.append(f"- {obj}")

        actions = plan.get("actions", [])
        if actions:
            parts.append("Acciones recomendadas:")
            for action in actions[:5]:
                if isinstance(action, dict):
                    parts.append(f"- {action.get('action', action)} (Prioridad: {action.get('priority', 'media')})")
                else:
                    parts.append(f"- {action}")

        if plan.get("timeline"):
            parts.append(f"Timeline sugerido: {plan['timeline']}")

        if plan.get("expected_impact"):
            parts.append(f"Impacto esperado: {plan['expected_impact']}")

        return "\n".join(parts)

    def _format_speech(self, speech: Dict, location: str, date: str) -> str:
        """Format speech content."""
        parts = [f"DISCURSO GENERADO - {location} ({date}):"]

        if speech.get("title"):
            parts.append(f"Título: {speech['title']}")

        key_points = speech.get("key_points", [])
        if key_points:
            parts.append("Puntos clave del discurso:")
            for point in key_points[:5]:
                parts.append(f"- {point}")

        # Include a preview of content if available
        content = speech.get("content", "")
        if content:
            preview = content[:500] + "..." if len(content) > 500 else content
            parts.append(f"Extracto: {preview}")

        return "\n".join(parts)

    def _format_metadata(self, meta: Dict, location: str, date: str) -> str:
        """Format analysis metadata."""
        parts = [f"DATOS DEL ANÁLISIS - {location} ({date}):"]

        if meta.get("tweets_analyzed"):
            parts.append(f"Tweets analizados: {meta['tweets_analyzed']}")

        if meta.get("theme"):
            parts.append(f"Tema principal: {meta['theme']}")

        if meta.get("trending_topic"):
            parts.append(f"Tema trending: {meta['trending_topic']}")

        if meta.get("trending_engagement"):
            parts.append(f"Engagement del trending: {meta['trending_engagement']}")

        return "\n".join(parts)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        location_filter: str = None,
        topic_filter: str = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            top_k: Number of results
            location_filter: Filter by location
            topic_filter: Filter by topic

        Returns:
            List of RetrievalResult
        """
        # Build where filter
        where = None
        if location_filter or topic_filter:
            conditions = []
            if location_filter:
                conditions.append({"location": location_filter})
            if topic_filter:
                conditions.append({"topic_name": topic_filter})

            if len(conditions) == 1:
                where = conditions[0]
            else:
                where = {"$and": conditions}

        return self.vector_store.search(
            query_text=query,
            top_k=top_k,
            where=where
        )

    def generate_response(
        self,
        query: str,
        context_docs: List[RetrievalResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7
    ) -> str:
        """Generate response using retrieved context."""
        # Build context from retrieved documents
        context_parts = []
        for result in context_docs:
            doc = result.document
            relevance = f"[Relevancia: {result.score:.0%}]"
            context_parts.append(f"{relevance}\n{doc.content}")

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No hay datos históricos disponibles. Sugiere al usuario realizar un análisis primero."

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-6:])

        # Add context and query
        user_message = f"""DATOS HISTÓRICOS DE ANÁLISIS:
{context}

---

PREGUNTA DEL USUARIO:
{query}

Responde basándote en los datos históricos proporcionados. Si no hay suficiente información, indícalo claramente:"""

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return "Lo siento, hubo un error generando la respuesta. Por favor intenta de nuevo."

    def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        location_filter: str = None,
        topic_filter: str = None
    ) -> Dict[str, Any]:
        """
        Main RAG chat interface.

        Args:
            query: User's question
            conversation_history: Previous messages
            top_k: Documents to retrieve
            location_filter: Optional location filter
            topic_filter: Optional topic filter

        Returns:
            Response with answer and sources
        """
        # Retrieve relevant documents
        results = self.retrieve(
            query=query,
            top_k=top_k,
            location_filter=location_filter,
            topic_filter=topic_filter
        )

        # Generate response
        answer = self.generate_response(
            query=query,
            context_docs=results,
            conversation_history=conversation_history
        )

        # Build sources
        sources = [
            {
                "id": r.document.id,
                "score": round(r.score, 3),
                "type": r.document.metadata.get("chunk_type", "unknown"),
                "topic": r.document.metadata.get("topic_name"),
                "location": r.document.metadata.get("location"),
                "date": r.document.metadata.get("created_at"),
                "preview": r.document.content[:200] + "..." if len(r.document.content) > 200 else r.document.content
            }
            for r in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "documents_indexed": self.vector_store.count(),
            "documents_retrieved": len(results)
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG service statistics."""
        return {
            "documents_indexed": self.vector_store.count(),
            "embedding_model": getattr(Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "generation_model": self.model,
            "sqlite_path": self.vector_store.db_path
        }

    def clear_index(self) -> None:
        """Clear all indexed documents."""
        self.vector_store.clear()
        logger.info("RAG index cleared")


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def init_rag_service(db_service=None) -> RAGService:
    """Initialize RAG service with database connection."""
    global _rag_service
    _rag_service = RAGService(db_service=db_service)
    return _rag_service
