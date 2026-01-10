"""
RAG (Retrieval Augmented Generation) Service for CASTOR ELECCIONES.
Provides context-aware chat using indexed analysis data.
"""
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

import openai
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A document in the RAG knowledge base."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
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


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, model: str = "text-embedding-3-small"):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = model
        self.dimension = 1536  # text-embedding-3-small dimension
        logger.info(f"EmbeddingService initialized with model: {model}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise


class VectorStore:
    """
    Simple in-memory vector store using cosine similarity.
    For production, consider using FAISS, ChromaDB, or Pinecone.
    """

    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self._embeddings_matrix: Optional[np.ndarray] = None
        self._doc_ids: List[str] = []
        logger.info("VectorStore initialized (in-memory)")

    def add_document(self, doc: Document) -> None:
        """Add a document to the store."""
        self.documents[doc.id] = doc
        self._invalidate_matrix()

    def add_documents(self, docs: List[Document]) -> None:
        """Add multiple documents."""
        for doc in docs:
            self.documents[doc.id] = doc
        self._invalidate_matrix()

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._invalidate_matrix()
            return True
        return False

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(doc_id)

    def _invalidate_matrix(self) -> None:
        """Invalidate the cached embeddings matrix."""
        self._embeddings_matrix = None
        self._doc_ids = []

    def _build_matrix(self) -> None:
        """Build the embeddings matrix for similarity search."""
        docs_with_embeddings = [
            (doc_id, doc) for doc_id, doc in self.documents.items()
            if doc.embedding is not None
        ]

        if not docs_with_embeddings:
            self._embeddings_matrix = None
            self._doc_ids = []
            return

        self._doc_ids = [doc_id for doc_id, _ in docs_with_embeddings]
        embeddings = [doc.embedding for _, doc in docs_with_embeddings]
        self._embeddings_matrix = np.array(embeddings)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[RetrievalResult]:
        """
        Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of RetrievalResult sorted by similarity
        """
        if self._embeddings_matrix is None:
            self._build_matrix()

        if self._embeddings_matrix is None or len(self._doc_ids) == 0:
            return []

        # Compute cosine similarity
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        # Normalize query
        query_vec = query_vec / query_norm

        # Normalize document vectors
        doc_norms = np.linalg.norm(self._embeddings_matrix, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1  # Avoid division by zero
        normalized_docs = self._embeddings_matrix / doc_norms

        # Compute similarities
        similarities = np.dot(normalized_docs, query_vec)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            score = float(similarities[idx])
            if score >= min_score:
                doc_id = self._doc_ids[idx]
                doc = self.documents[doc_id]
                results.append(RetrievalResult(
                    document=doc,
                    score=score,
                    rank=rank + 1
                ))

        return results

    def count(self) -> int:
        """Return number of documents."""
        return len(self.documents)

    def clear(self) -> None:
        """Clear all documents."""
        self.documents.clear()
        self._invalidate_matrix()


class RAGService:
    """
    Main RAG service combining retrieval and generation.
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL

        # Default system prompt for RAG
        self.system_prompt = """Eres CASTOR AI, un asistente experto en análisis electoral y campañas políticas en Colombia.

Tu rol es responder preguntas usando el CONTEXTO proporcionado de análisis previos.

Reglas:
1. Basa tus respuestas PRINCIPALMENTE en el contexto proporcionado
2. Si el contexto no tiene información suficiente, indícalo claramente
3. Responde en español, de manera concisa y profesional
4. Proporciona datos específicos cuando estén disponibles (porcentajes, números)
5. Da recomendaciones accionables cuando sea apropiado
6. No inventes datos que no estén en el contexto"""

        logger.info("RAGService initialized")

    def index_analysis(
        self,
        analysis_id: str,
        analysis_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Index an analysis into the vector store.
        Chunks the analysis into searchable documents.

        Args:
            analysis_id: Unique identifier for the analysis
            analysis_data: The analysis data to index
            metadata: Additional metadata

        Returns:
            List of document IDs created
        """
        documents = self._chunk_analysis(analysis_id, analysis_data, metadata or {})

        # Generate embeddings
        texts = [doc.content for doc in documents]
        if texts:
            embeddings = self.embedding_service.embed_texts(texts)
            for doc, embedding in zip(documents, embeddings):
                doc.embedding = embedding

        # Add to vector store
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

        # 1. Index executive summary
        if "executive_summary" in data:
            summary = data["executive_summary"]
            content = self._format_executive_summary(summary)
            documents.append(Document(
                id=f"{analysis_id}_summary",
                content=content,
                metadata={**base_meta, "chunk_type": "executive_summary"}
            ))

        # 2. Index each topic analysis
        topics = data.get("topics", data.get("topic_analyses", []))
        for i, topic in enumerate(topics):
            content = self._format_topic(topic)
            documents.append(Document(
                id=f"{analysis_id}_topic_{i}",
                content=content,
                metadata={
                    **base_meta,
                    "chunk_type": "topic",
                    "topic_name": topic.get("topic", f"topic_{i}")
                }
            ))

        # 3. Index sentiment overview
        sentiment = data.get("sentiment_overview")
        if sentiment:
            content = self._format_sentiment(sentiment, data.get("location", ""))
            documents.append(Document(
                id=f"{analysis_id}_sentiment",
                content=content,
                metadata={**base_meta, "chunk_type": "sentiment"}
            ))

        # 4. Index strategic plan if present
        if "strategic_plan" in data:
            plan = data["strategic_plan"]
            content = self._format_strategic_plan(plan)
            documents.append(Document(
                id=f"{analysis_id}_strategy",
                content=content,
                metadata={**base_meta, "chunk_type": "strategic_plan"}
            ))

        # 5. Index forecast data if present
        if "forecast" in data:
            forecast = data["forecast"]
            content = self._format_forecast(forecast)
            documents.append(Document(
                id=f"{analysis_id}_forecast",
                content=content,
                metadata={**base_meta, "chunk_type": "forecast"}
            ))

        return documents

    def _format_executive_summary(self, summary: Dict[str, Any]) -> str:
        """Format executive summary for indexing."""
        parts = ["RESUMEN EJECUTIVO:"]

        if summary.get("overview"):
            parts.append(f"Vision general: {summary['overview']}")

        findings = summary.get("key_findings", [])
        if findings:
            parts.append("Hallazgos clave:")
            for f in findings:
                parts.append(f"- {f}")

        recommendations = summary.get("recommendations", [])
        if recommendations:
            parts.append("Recomendaciones:")
            for r in recommendations:
                parts.append(f"- {r}")

        return "\n".join(parts)

    def _format_topic(self, topic: Dict[str, Any]) -> str:
        """Format a topic analysis for indexing."""
        parts = [f"TEMA: {topic.get('topic', 'Sin nombre')}"]

        sentiment = topic.get("sentiment", {})
        if sentiment:
            pos = sentiment.get("positive", 0) * 100
            neg = sentiment.get("negative", 0) * 100
            neu = sentiment.get("neutral", 0) * 100
            parts.append(f"Sentimiento: {pos:.1f}% positivo, {neu:.1f}% neutral, {neg:.1f}% negativo")

        count = topic.get("tweet_count", 0)
        if count:
            parts.append(f"Menciones: {count}")

        insights = topic.get("key_insights", [])
        if insights:
            parts.append("Insights:")
            for insight in insights[:5]:
                parts.append(f"- {insight}")

        return "\n".join(parts)

    def _format_sentiment(self, sentiment: Dict[str, Any], location: str) -> str:
        """Format sentiment overview for indexing."""
        pos = sentiment.get("positive", 0) * 100
        neg = sentiment.get("negative", 0) * 100
        neu = sentiment.get("neutral", 0) * 100

        return f"""ANALISIS DE SENTIMIENTO en {location}:
Positivo: {pos:.1f}%
Neutral: {neu:.1f}%
Negativo: {neg:.1f}%
Tono general: {'Favorable' if pos > neg else 'Crítico' if neg > pos else 'Neutral'}"""

    def _format_strategic_plan(self, plan: Dict[str, Any]) -> str:
        """Format strategic plan for indexing."""
        parts = ["PLAN ESTRATEGICO:"]

        objectives = plan.get("objectives", [])
        if objectives:
            parts.append("Objetivos:")
            for obj in objectives:
                parts.append(f"- {obj}")

        actions = plan.get("actions", [])
        if actions:
            parts.append("Acciones:")
            for action in actions:
                if isinstance(action, dict):
                    parts.append(f"- {action.get('action', action)}")
                else:
                    parts.append(f"- {action}")

        if plan.get("timeline"):
            parts.append(f"Timeline: {plan['timeline']}")

        if plan.get("expected_impact"):
            parts.append(f"Impacto esperado: {plan['expected_impact']}")

        return "\n".join(parts)

    def _format_forecast(self, forecast: Dict[str, Any]) -> str:
        """Format forecast data for indexing."""
        parts = ["PRONOSTICO ELECTORAL:"]

        if forecast.get("icce"):
            parts.append(f"ICCE (Indice de Clima): {forecast['icce']}")

        if forecast.get("momentum"):
            parts.append(f"Momentum: {forecast['momentum']}")

        if forecast.get("trend"):
            parts.append(f"Tendencia: {forecast['trend']}")

        if forecast.get("prediction"):
            parts.append(f"Prediccion: {forecast['prediction']}")

        return "\n".join(parts)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            min_score: Minimum similarity threshold
            filter_metadata: Optional metadata filters

        Returns:
            List of RetrievalResult
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more, then filter
            min_score=min_score
        )

        # Apply metadata filters if provided
        if filter_metadata:
            results = [
                r for r in results
                if all(
                    r.document.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
            ]

        return results[:top_k]

    def generate_response(
        self,
        query: str,
        context_docs: List[RetrievalResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a response using retrieved context.

        Args:
            query: User's question
            context_docs: Retrieved documents
            conversation_history: Previous messages
            temperature: LLM temperature

        Returns:
            Generated response
        """
        # Build context from retrieved documents
        context_parts = []
        for result in context_docs:
            doc = result.document
            context_parts.append(f"[Relevancia: {result.score:.2f}]\n{doc.content}")

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No hay contexto disponible."

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-6:])  # Last 3 exchanges

        # Add context and query
        user_message = f"""CONTEXTO DE ANÁLISIS:
{context}

---

PREGUNTA DEL USUARIO:
{query}

Responde basándote en el contexto proporcionado:"""

        messages.append({"role": "user", "content": user_message})

        # Generate response
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            raise

    def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        Main RAG chat interface.

        Args:
            query: User's question
            conversation_history: Previous messages
            top_k: Number of documents to retrieve
            min_score: Minimum relevance score

        Returns:
            Response with answer and sources
        """
        # Retrieve relevant documents
        results = self.retrieve(query, top_k=top_k, min_score=min_score)

        # Generate response
        answer = self.generate_response(
            query=query,
            context_docs=results,
            conversation_history=conversation_history
        )

        # Build sources list
        sources = [
            {
                "id": r.document.id,
                "score": round(r.score, 3),
                "type": r.document.metadata.get("chunk_type", "unknown"),
                "topic": r.document.metadata.get("topic_name"),
                "preview": r.document.content[:200] + "..." if len(r.document.content) > 200 else r.document.content
            }
            for r in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "documents_searched": self.vector_store.count(),
            "documents_retrieved": len(results)
        }

    def index_from_database(self, db_service, user_id: Optional[str] = None, limit: int = 50) -> int:
        """
        Index analyses from the database.

        Args:
            db_service: DatabaseService instance
            user_id: Optional user ID to filter
            limit: Maximum analyses to index

        Returns:
            Number of analyses indexed
        """
        try:
            # Get recent analyses
            if user_id:
                analyses = db_service.get_user_analyses(user_id, limit=limit)
            else:
                # Get all recent analyses (would need a new method in db_service)
                analyses = []

            indexed = 0
            for analysis in analyses:
                try:
                    self.index_analysis(
                        analysis_id=analysis["id"],
                        analysis_data=analysis.get("analysis_data", {}),
                        metadata={
                            "user_id": user_id,
                            "location": analysis.get("location"),
                            "theme": analysis.get("theme"),
                            "candidate": analysis.get("candidate_name")
                        }
                    )
                    indexed += 1
                except Exception as e:
                    logger.warning(f"Error indexing analysis {analysis['id']}: {e}")

            return indexed
        except Exception as e:
            logger.error(f"Error indexing from database: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG service statistics."""
        return {
            "documents_indexed": self.vector_store.count(),
            "embedding_model": self.embedding_service.model,
            "generation_model": self.model
        }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
