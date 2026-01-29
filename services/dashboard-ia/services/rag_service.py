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
import uuid

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
        Uses the new ApiCall model with tweets and PND metrics.

        Args:
            limit: Maximum number of API calls to sync

        Returns:
            Number of documents indexed
        """
        if not self.db_service:
            logger.warning("No database service configured for RAG sync")
            return 0

        try:
            indexed_count = 0

            # Get API calls from new model
            api_calls = self.db_service.get_api_calls(limit=limit)

            for api_call in api_calls:
                try:
                    api_call_id = api_call.get('id')
                    if not api_call_id:
                        continue

                    # Get full data for this API call
                    full_data = self.db_service.get_api_call_with_data(api_call_id)
                    if not full_data:
                        continue

                    metadata = {
                        "location": api_call.get('location', 'Colombia'),
                        "candidate_name": api_call.get('candidate_name', ''),
                        "politician": api_call.get('politician', ''),
                        "topic": api_call.get('topic', ''),
                        "created_at": api_call.get('fetched_at', '')
                    }

                    # 1. Index analysis snapshot
                    snapshot = full_data.get('analysis_snapshot')
                    if snapshot:
                        snapshot_data = {
                            'icce': getattr(snapshot, 'icce', 50),
                            'sov': getattr(snapshot, 'sov', 0),
                            'sna': getattr(snapshot, 'sna', 0),
                            'momentum': getattr(snapshot, 'momentum', 0),
                            'sentiment_positive': getattr(snapshot, 'sentiment_positive', 0.33),
                            'sentiment_negative': getattr(snapshot, 'sentiment_negative', 0.33),
                            'sentiment_neutral': getattr(snapshot, 'sentiment_neutral', 0.34),
                            'executive_summary': getattr(snapshot, 'executive_summary', ''),
                            'key_findings': getattr(snapshot, 'key_findings', []),
                            'trending_topics': getattr(snapshot, 'trending_topics', [])
                        }
                        self.index_analysis_snapshot(api_call_id, snapshot_data, metadata)
                        indexed_count += 1

                    # 2. Index tweets
                    tweets = self.db_service.get_tweets_by_api_call(api_call_id, limit=200)
                    if tweets:
                        docs_created = self.index_tweets(api_call_id, tweets, metadata)
                        indexed_count += docs_created

                    # 3. Index PND metrics
                    pnd_metrics = full_data.get('pnd_metrics', [])
                    if pnd_metrics:
                        pnd_data = []
                        for m in pnd_metrics:
                            pnd_data.append({
                                'pnd_axis': getattr(m, 'pnd_axis', ''),
                                'pnd_axis_display': getattr(m, 'pnd_axis_display', ''),
                                'icce': getattr(m, 'icce', 0),
                                'sov': getattr(m, 'sov', 0),
                                'sna': getattr(m, 'sna', 0),
                                'tweet_count': getattr(m, 'tweet_count', 0),
                                'trend': getattr(m, 'trend', 'stable'),
                                'sample_tweets': getattr(m, 'sample_tweets', [])
                            })
                        docs_created = self.index_pnd_metrics(api_call_id, pnd_data, metadata)
                        indexed_count += docs_created

                    logger.info(f"Synced API call {api_call_id}")

                except Exception as e:
                    logger.warning(f"Error syncing API call {api_call.get('id')}: {e}")

            # Also sync legacy analyses if they exist
            try:
                analyses = self.db_service.get_all_analyses(limit=limit)
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
                        logger.warning(f"Error syncing legacy analysis: {e}")
            except Exception as e:
                logger.debug(f"No legacy analyses to sync: {e}")

            logger.info(f"Synced {indexed_count} documents from database")
            return indexed_count

        except Exception as e:
            logger.error(f"Error syncing from database: {e}", exc_info=True)
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

    def index_tweets(
        self,
        api_call_id: str,
        tweets: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Indexar tweets individuales en el RAG para búsqueda semántica.
        Agrupa tweets por tema PND para eficiencia.

        Args:
            api_call_id: ID del API call
            tweets: Lista de tweets con contenido y metadatos
            metadata: Metadatos adicionales (location, candidate, etc.)

        Returns:
            Número de documentos indexados
        """
        if not tweets:
            return 0

        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        documents = []

        # Agrupar tweets por tema PND
        tweets_by_topic: Dict[str, List[Dict]] = {}
        for tweet in tweets:
            topic = tweet.get("pnd_topic", "general") or "general"
            if topic not in tweets_by_topic:
                tweets_by_topic[topic] = []
            tweets_by_topic[topic].append(tweet)

        # Crear documento por cada grupo de tema (máx 10 tweets por documento)
        for topic, topic_tweets in tweets_by_topic.items():
            # Dividir en chunks si hay muchos tweets
            chunk_size = 10
            for i in range(0, len(topic_tweets), chunk_size):
                chunk = topic_tweets[i:i + chunk_size]

                # Contar sentimientos
                pos_count = sum(1 for t in chunk if 'positiv' in (t.get('sentiment_label') or '').lower())
                neg_count = sum(1 for t in chunk if 'negativ' in (t.get('sentiment_label') or '').lower())
                neu_count = len(chunk) - pos_count - neg_count

                # Formatear contenido
                content_parts = [
                    f"TWEETS SOBRE {topic.upper()} - {location} ({date})",
                    f"Candidato/Tema: {candidate}" if candidate else "",
                    f"Total tweets: {len(chunk)} | Positivos: {pos_count} | Negativos: {neg_count} | Neutrales: {neu_count}",
                    "",
                    "Opiniones de ciudadanos:"
                ]

                for t in chunk:
                    author = t.get('author_username', 'usuario')
                    content = t.get('content', '')[:280]  # Limitar longitud
                    sentiment = t.get('sentiment_label', 'neutral')
                    engagement = t.get('retweet_count', 0) + t.get('like_count', 0)

                    content_parts.append(f"- @{author} [{sentiment}]: \"{content}\"")
                    if engagement > 10:
                        content_parts.append(f"  (Engagement: {engagement})")

                doc_id = f"{api_call_id}_tweets_{topic}_{i // chunk_size}"
                documents.append(Document(
                    id=doc_id,
                    content="\n".join(content_parts),
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
                ))

        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Indexed {len(documents)} tweet documents for API call {api_call_id}")

        return len(documents)

    def index_pnd_metrics(
        self,
        api_call_id: str,
        pnd_metrics: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Indexar métricas PND en el RAG.

        Args:
            api_call_id: ID del API call
            pnd_metrics: Lista de métricas por eje PND
            metadata: Metadatos adicionales

        Returns:
            Número de documentos indexados
        """
        if not pnd_metrics:
            return 0

        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        documents = []

        # Documento resumen de todos los ejes
        summary_parts = [
            f"MÉTRICAS PND COMPLETAS - {location} ({date})",
            f"Candidato: {candidate}" if candidate else "",
            "",
            "Análisis por eje del Plan Nacional de Desarrollo:"
        ]

        for m in pnd_metrics:
            axis = m.get('pnd_axis_display', m.get('pnd_axis', 'Desconocido'))
            icce = m.get('icce', 0)
            sov = m.get('sov', 0)
            sna = m.get('sna', 0)
            tweets = m.get('tweet_count', 0)
            trend = m.get('trend', 'stable')

            trend_text = "↑ subiendo" if trend == 'up' else "↓ bajando" if trend == 'down' else "→ estable"
            sentiment_text = "positivo" if sna > 10 else "negativo" if sna < -10 else "neutral"

            summary_parts.append(f"\n{axis}:")
            summary_parts.append(f"  - ICCE: {icce:.1f}/100 (Fuerza narrativa)")
            summary_parts.append(f"  - SOV: {sov:.1f}% (Presencia en conversación)")
            summary_parts.append(f"  - SNA: {sna:+.1f}% (Sentimiento {sentiment_text})")
            summary_parts.append(f"  - Tweets: {tweets} | Tendencia: {trend_text}")

            # Samples de tweets si existen
            samples = m.get('sample_tweets', [])
            if samples:
                summary_parts.append(f"  - Ejemplo: \"{samples[0][:100]}...\"" if len(samples[0]) > 100 else f"  - Ejemplo: \"{samples[0]}\"")

        # Documento resumen
        documents.append(Document(
            id=f"{api_call_id}_pnd_summary",
            content="\n".join(summary_parts),
            metadata={
                "api_call_id": api_call_id,
                "type": "pnd_metrics",
                "chunk_type": "pnd_summary",
                "location": location,
                "candidate": candidate,
                "created_at": date
            }
        ))

        # Documento individual por cada eje para búsquedas específicas
        for m in pnd_metrics:
            axis = m.get('pnd_axis_display', m.get('pnd_axis', 'Desconocido'))
            axis_key = m.get('pnd_axis', axis.lower().replace(' ', '_'))
            icce = m.get('icce', 0)
            sov = m.get('sov', 0)
            sna = m.get('sna', 0)

            interpretation = []
            if icce >= 60:
                interpretation.append(f"El candidato tiene una posición FUERTE en {axis}")
            elif icce < 45:
                interpretation.append(f"El candidato tiene una posición DÉBIL en {axis}, requiere atención")
            else:
                interpretation.append(f"El candidato tiene una posición MODERADA en {axis}")

            if sna > 15:
                interpretation.append("El sentimiento ciudadano es MUY POSITIVO")
            elif sna > 5:
                interpretation.append("El sentimiento ciudadano es positivo")
            elif sna < -15:
                interpretation.append("El sentimiento ciudadano es MUY NEGATIVO, hay críticas fuertes")
            elif sna < -5:
                interpretation.append("El sentimiento ciudadano es negativo")
            else:
                interpretation.append("El sentimiento ciudadano es neutral/dividido")

            content = f"""ANÁLISIS DEL EJE PND: {axis} - {location} ({date})
Candidato: {candidate}

MÉTRICAS:
- ICCE (Índice de Capacidad Electoral): {icce:.1f}/100
- SOV (Share of Voice): {sov:.1f}%
- SNA (Sentimiento Neto Agregado): {sna:+.1f}%
- Tweets analizados: {m.get('tweet_count', 0)}

INTERPRETACIÓN:
{chr(10).join('• ' + i for i in interpretation)}

RECOMENDACIÓN:
{'Mantener y capitalizar esta fortaleza narrativa' if icce >= 60 else 'Desarrollar propuestas y aumentar presencia en este tema' if icce < 45 else 'Incrementar acciones para consolidar posición'}
"""

            documents.append(Document(
                id=f"{api_call_id}_pnd_{axis_key}",
                content=content,
                metadata={
                    "api_call_id": api_call_id,
                    "type": "pnd_metrics",
                    "chunk_type": "pnd_axis",
                    "pnd_axis": axis_key,
                    "pnd_axis_display": axis,
                    "icce": icce,
                    "sov": sov,
                    "sna": sna,
                    "location": location,
                    "candidate": candidate,
                    "created_at": date
                }
            ))

        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Indexed {len(documents)} PND metric documents for API call {api_call_id}")

        return len(documents)

    def index_analysis_snapshot(
        self,
        api_call_id: str,
        snapshot: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Indexar snapshot de análisis en el RAG.

        Args:
            api_call_id: ID del API call
            snapshot: Datos del snapshot (ICCE, SNA, etc.)
            metadata: Metadatos adicionales

        Returns:
            Número de documentos indexados
        """
        meta = metadata or {}
        location = meta.get("location", "Colombia")
        candidate = meta.get("candidate_name", "")
        date = meta.get("created_at", datetime.now(timezone.utc).isoformat())

        icce = snapshot.get('icce', 50)
        sov = snapshot.get('sov', 0)
        sna = snapshot.get('sna', 0)
        momentum = snapshot.get('momentum', 0)
        pos = snapshot.get('sentiment_positive', 0.33)
        neg = snapshot.get('sentiment_negative', 0.33)
        neu = snapshot.get('sentiment_neutral', 0.34)

        # Interpretaciones
        icce_level = "alto" if icce >= 60 else "bajo" if icce < 45 else "moderado"
        momentum_text = "positivo (creciendo)" if momentum > 0.005 else "negativo (decreciendo)" if momentum < -0.005 else "estable"
        sentiment_text = "favorable" if pos > neg + 0.1 else "desfavorable" if neg > pos + 0.1 else "mixto"

        content = f"""RESUMEN EJECUTIVO DE ANÁLISIS - {location} ({date})
Candidato/Tema: {candidate}

INDICADORES CLAVE:
- ICCE (Índice de Capacidad Electoral): {icce:.1f}/100 - Nivel {icce_level}
- SOV (Share of Voice): {sov:.1f}% de la conversación
- SNA (Sentimiento Neto): {sna:+.1f}%
- Momentum: {momentum:+.3f} ({momentum_text})

DISTRIBUCIÓN DE SENTIMIENTO:
- Positivo: {pos*100:.1f}%
- Neutral: {neu*100:.1f}%
- Negativo: {neg*100:.1f}%
- Balance general: {sentiment_text}

RESUMEN:
{snapshot.get('executive_summary', f'Análisis de conversación sobre {candidate} en {location}')}

HALLAZGOS CLAVE:
{chr(10).join('• ' + f for f in snapshot.get('key_findings', [])) or '• No hay hallazgos específicos'}

TEMAS TRENDING:
{', '.join(snapshot.get('trending_topics', [])) or 'No identificados'}

EVALUACIÓN GENERAL:
{'La posición narrativa es sólida, mantener estrategia actual' if icce >= 60 and sna > 0 else 'La posición narrativa es favorable pero puede mejorar' if icce >= 50 else 'Se requiere atención urgente a la estrategia de comunicación' if icce < 40 else 'Hay oportunidades de mejora en la narrativa'}
"""

        doc = Document(
            id=f"{api_call_id}_snapshot",
            content=content,
            metadata={
                "api_call_id": api_call_id,
                "type": "analysis_snapshot",
                "chunk_type": "executive_summary",
                "icce": icce,
                "sov": sov,
                "sna": sna,
                "momentum": momentum,
                "location": location,
                "candidate": candidate,
                "created_at": date
            }
        )

        self.vector_store.add_documents([doc])
        logger.info(f"Indexed analysis snapshot for API call {api_call_id}")

        return 1

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

    # =========================================================================
    # E-14 ELECTORAL FORMS INDEXING
    # =========================================================================

    def index_e14_form(
        self,
        extraction_id: str,
        extraction_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Indexar un formulario E-14 procesado en el RAG.
        Soporta formato Senado/Cámara 2022 con circunscripciones y voto preferente.

        Args:
            extraction_id: ID único de la extracción OCR
            extraction_data: Datos completos del E-14 (E14ExtractionResult o dict)
            metadata: Metadatos adicionales

        Returns:
            Número de documentos indexados
        """
        meta = metadata or {}
        documents = []

        # Extraer datos del header
        header = extraction_data.get('header', {})
        departamento = header.get('departamento_name', 'Desconocido')
        municipio = header.get('municipio_name', 'Desconocido')
        mesa_id = header.get('mesa_id') or f"{header.get('departamento_code', '00')}-{header.get('municipio_code', '000')}-{header.get('zona', '00')}-{header.get('puesto', '00')}-{header.get('mesa', '000')}"
        corporacion = header.get('corporacion', 'PRESIDENCIA')
        lugar = header.get('lugar', '')
        eleccion = header.get('eleccion', '')

        # Extraer datos de nivelación
        nivelacion = extraction_data.get('nivelacion', {})
        total_sufragantes = nivelacion.get('total_sufragantes_e11', 0)
        total_urna = nivelacion.get('total_votos_urna', 0)

        # Extraer votos especiales
        votos_esp = extraction_data.get('votos_especiales', {})
        votos_blanco = votos_esp.get('votos_blanco', 0)
        votos_nulos = votos_esp.get('votos_nulos', 0)
        votos_no_marcados = votos_esp.get('votos_no_marcados', 0)

        # Extraer partidos - soporta formato nuevo (circunscripciones) y antiguo (partidos)
        partidos = []

        # Formato nuevo: circunscripcion_nacional + circunscripcion_indigena
        circ_nacional = extraction_data.get('circunscripcion_nacional', {})
        circ_indigena = extraction_data.get('circunscripcion_indigena', {})

        if circ_nacional.get('partidos'):
            for p in circ_nacional['partidos']:
                p['circunscripcion'] = 'NACIONAL'
                partidos.append(p)

        if circ_indigena.get('partidos'):
            for p in circ_indigena['partidos']:
                p['circunscripcion'] = 'INDIGENA'
                partidos.append(p)

        # Formato antiguo: partidos directos
        if not partidos:
            partidos = extraction_data.get('partidos', [])

        # Calcular totales
        total_votos_partidos = sum(p.get('total_votos', 0) for p in partidos)
        total_computado = total_votos_partidos + votos_blanco + votos_nulos + votos_no_marcados

        # Confidence global
        overall_confidence = extraction_data.get('overall_confidence', 0.0)
        fields_needing_review = extraction_data.get('fields_needing_review', 0)

        # Contar partidos por circunscripción
        partidos_nacional = [p for p in partidos if p.get('circunscripcion') == 'NACIONAL']
        partidos_indigena = [p for p in partidos if p.get('circunscripcion') == 'INDIGENA']

        # Base metadata para todos los documentos
        base_meta = {
            "type": "e14_form",
            "extraction_id": extraction_id,
            "mesa_id": mesa_id,
            "departamento": departamento,
            "municipio": municipio,
            "corporacion": corporacion,
            "eleccion": eleccion,
            "lugar": lugar,
            "overall_confidence": overall_confidence,
            **meta
        }

        # 1. Documento resumen del E-14
        resumen_parts = [
            f"FORMULARIO E-14 - ACTA DE ESCRUTINIO",
            f"Elección: {eleccion}" if eleccion else "",
            f"Mesa: {mesa_id}",
            f"Corporación: {corporacion}",
            f"Ubicación: {lugar}, {municipio}, {departamento}",
            f"",
            f"NIVELACIÓN DE MESA:",
            f"- Total sufragantes (E-11): {total_sufragantes:,}",
            f"- Total votos en urna: {total_urna:,}",
            f"- Total computado: {total_computado:,}",
            f"- Diferencia: {total_urna - total_computado:+,}",
            f"",
            f"VOTOS ESPECIALES:",
            f"- Votos en blanco: {votos_blanco:,}",
            f"- Votos nulos: {votos_nulos:,}",
            f"- Tarjetas no marcadas: {votos_no_marcados:,}",
        ]

        # Agregar info de circunscripciones si aplica (Senado/Cámara)
        if partidos_nacional or partidos_indigena:
            resumen_parts.append("")
            resumen_parts.append("CIRCUNSCRIPCIONES:")
            if partidos_nacional:
                votos_nac = sum(p.get('total_votos', 0) for p in partidos_nacional)
                resumen_parts.append(f"- Nacional: {len(partidos_nacional)} partidos, {votos_nac:,} votos")
            if partidos_indigena:
                votos_ind = sum(p.get('total_votos', 0) for p in partidos_indigena)
                resumen_parts.append(f"- Indígena: {len(partidos_indigena)} partidos, {votos_ind:,} votos")

        resumen_parts.extend([
            f"",
            f"CONFIANZA OCR: {overall_confidence*100:.1f}%",
            f"Campos que requieren revisión: {fields_needing_review}"
        ])

        # Filtrar líneas vacías consecutivas
        resumen_parts = [p for p in resumen_parts if p or p == ""]

        documents.append(Document(
            id=f"e14_{extraction_id}_resumen",
            content="\n".join(resumen_parts),
            metadata={**base_meta, "chunk_type": "e14_summary"}
        ))

        # 2. Documento de resultados por partido/candidato
        if partidos:
            resultados_parts = [
                f"RESULTADOS ELECTORALES - {corporacion}",
                f"Elección: {eleccion}" if eleccion else "",
                f"Mesa: {mesa_id} | {municipio}, {departamento}",
                f""
            ]

            # Función para agregar resultados de una lista de partidos
            def agregar_resultados(lista_partidos, titulo=None):
                if not lista_partidos:
                    return
                if titulo:
                    resultados_parts.append(f"\n{titulo}:")

                partidos_ord = sorted(lista_partidos, key=lambda p: p.get('total_votos', 0), reverse=True)
                for i, partido in enumerate(partidos_ord, 1):
                    nombre = partido.get('party_name', 'Desconocido')
                    codigo = partido.get('party_code', '')
                    votos = partido.get('total_votos', 0)
                    votos_agrup = partido.get('votos_agrupacion', 0)
                    tipo = partido.get('tipo_lista', partido.get('list_type', ''))
                    porcentaje = (votos / total_computado * 100) if total_computado > 0 else 0

                    linea = f"#{i} {nombre} ({codigo}): {votos:,} votos ({porcentaje:.1f}%)"
                    if tipo == 'CON_VOTO_PREFERENTE' and votos_agrup > 0:
                        linea += f" [Lista: {votos_agrup:,}]"
                    resultados_parts.append(linea)

                    # Agregar candidatos individuales si hay voto preferente
                    candidatos = partido.get('votos_candidatos', [])
                    if candidatos:
                        for cand in sorted(candidatos, key=lambda c: c.get('votos', c.get('votes', 0)), reverse=True)[:5]:
                            cand_num = cand.get('numero', cand.get('candidate_number', '?'))
                            cand_votos = cand.get('votos', cand.get('votes', 0))
                            if cand_votos > 0:
                                resultados_parts.append(f"   - Candidato #{cand_num}: {cand_votos:,} votos")

            # Si hay circunscripciones separadas (Senado/Cámara)
            if partidos_nacional or partidos_indigena:
                agregar_resultados(partidos_nacional, "CIRCUNSCRIPCIÓN NACIONAL")
                agregar_resultados(partidos_indigena, "CIRCUNSCRIPCIÓN ESPECIAL INDÍGENA")
            else:
                resultados_parts.append("VOTOS POR PARTIDO/CANDIDATO:")
                agregar_resultados(partidos)

            resultados_parts.append(f"")
            resultados_parts.append(f"TOTAL VOTOS VÁLIDOS: {total_votos_partidos:,}")

            documents.append(Document(
                id=f"e14_{extraction_id}_resultados",
                content="\n".join(resultados_parts),
                metadata={
                    **base_meta,
                    "chunk_type": "e14_results",
                    "total_votos": total_votos_partidos,
                    "num_partidos": len(partidos)
                }
            ))

        # 3. Documento por cada partido (para búsquedas específicas)
        for partido in partidos:
            nombre = partido.get('party_name', 'Desconocido')
            codigo = partido.get('party_code', '')
            votos = partido.get('total_votos', 0)
            votos_agrupacion = partido.get('votos_agrupacion', 0)
            tipo_lista = partido.get('tipo_lista', partido.get('list_type', 'SIN_VOTO_PREFERENTE'))
            circunscripcion = partido.get('circunscripcion', 'NACIONAL')
            confidence = partido.get('confidence_total', overall_confidence)

            partido_content = f"""VOTOS DE {nombre.upper()} - E-14
Mesa: {mesa_id}
Ubicación: {municipio}, {departamento}
Corporación: {corporacion}
Elección: {eleccion}

Partido: {nombre}
Código: {codigo}
Circunscripción: {circunscripcion}
Tipo de lista: {tipo_lista}
Votos por lista/agrupación: {votos_agrupacion:,}
Total votos: {votos:,}
Porcentaje de mesa: {(votos/total_computado*100) if total_computado > 0 else 0:.2f}%
Confianza OCR: {confidence*100:.1f}%
"""

            # Agregar candidatos si hay voto preferente
            candidatos = partido.get('votos_candidatos', [])
            if candidatos:
                partido_content += "\nVotos por candidato (voto preferente):\n"
                for cand in sorted(candidatos, key=lambda c: c.get('votos', c.get('votes', 0)), reverse=True):
                    cand_num = cand.get('numero', cand.get('candidate_number', '?'))
                    cand_votos = cand.get('votos', cand.get('votes', 0))
                    if cand_votos > 0:
                        partido_content += f"- Candidato #{cand_num}: {cand_votos:,} votos\n"

            documents.append(Document(
                id=f"e14_{extraction_id}_partido_{codigo}",
                content=partido_content,
                metadata={
                    **base_meta,
                    "chunk_type": "e14_party",
                    "party_code": codigo,
                    "party_name": nombre,
                    "party_votes": votos,
                    "circunscripcion": circunscripcion,
                    "tipo_lista": tipo_lista,
                    "confidence": confidence
                }
            ))

        # 4. Documento de alertas/problemas (si hay campos con baja confianza)
        if fields_needing_review > 0 or overall_confidence < 0.8:
            alerta_content = f"""ALERTA OCR - E-14 CON POSIBLES PROBLEMAS
Mesa: {mesa_id}
Ubicación: {municipio}, {departamento}
Corporación: {corporacion}

INDICADORES DE RIESGO:
- Confianza general: {overall_confidence*100:.1f}% {'⚠️ BAJA' if overall_confidence < 0.7 else ''}
- Campos que requieren revisión: {fields_needing_review}
- Diferencia urna vs computado: {total_urna - total_computado:+,}

{'REQUIERE REVISIÓN MANUAL' if overall_confidence < 0.7 or fields_needing_review > 3 else 'REVISAR SI ES NECESARIO'}
"""

            documents.append(Document(
                id=f"e14_{extraction_id}_alerta",
                content=alerta_content,
                metadata={
                    **base_meta,
                    "chunk_type": "e14_alert",
                    "needs_review": True,
                    "risk_level": "HIGH" if overall_confidence < 0.7 else "MEDIUM"
                }
            ))

        # Indexar todos los documentos
        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Indexed E-14 form {extraction_id}: {len(documents)} documents, mesa {mesa_id}")

        return len(documents)

    def index_e14_batch(
        self,
        extractions: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Indexar múltiples formularios E-14 en batch.

        Args:
            extractions: Lista de extracciones E-14
            metadata: Metadatos adicionales compartidos

        Returns:
            Resumen del indexado
        """
        total_indexed = 0
        successful = 0
        failed = 0
        errors = []

        for extraction in extractions:
            try:
                extraction_id = extraction.get('extraction_id', str(uuid.uuid4()))
                count = self.index_e14_form(extraction_id, extraction, metadata)
                total_indexed += count
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "extraction_id": extraction.get('extraction_id', 'unknown'),
                    "error": str(e)
                })
                logger.warning(f"Error indexing E-14: {e}")

        logger.info(f"E-14 batch indexing complete: {successful} success, {failed} failed, {total_indexed} docs")

        return {
            "total_extractions": len(extractions),
            "successful": successful,
            "failed": failed,
            "documents_indexed": total_indexed,
            "errors": errors
        }

    def search_e14(
        self,
        query: str,
        top_k: int = 10,
        departamento: str = None,
        municipio: str = None,
        corporacion: str = None,
        party_name: str = None
    ) -> List[RetrievalResult]:
        """
        Búsqueda especializada en datos E-14.

        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados
            departamento: Filtrar por departamento
            municipio: Filtrar por municipio
            corporacion: Filtrar por corporación
            party_name: Filtrar por nombre de partido

        Returns:
            Lista de resultados relevantes
        """
        # Construir filtros
        conditions = [{"type": "e14_form"}]

        if departamento:
            conditions.append({"departamento": departamento})
        if municipio:
            conditions.append({"municipio": municipio})
        if corporacion:
            conditions.append({"corporacion": corporacion})
        if party_name:
            conditions.append({"party_name": party_name})

        where = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        return self.vector_store.search(
            query_text=query,
            top_k=top_k,
            where=where
        )

    def get_e14_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de E-14 indexados.

        Returns:
            Estadísticas de formularios indexados
        """
        stats = {
            "total_e14_documents": 0,
            "by_corporacion": {},
            "by_departamento": {},
            "alerts_count": 0
        }

        # Contar documentos E-14 en el store
        with sqlite3.connect(self.vector_store.db_path) as conn:
            cursor = conn.execute(
                "SELECT metadata FROM rag_documents WHERE metadata LIKE '%e14_form%'"
            )
            rows = cursor.fetchall()

            for row in rows:
                try:
                    metadata = json.loads(row[0])
                    if metadata.get('type') == 'e14_form':
                        stats["total_e14_documents"] += 1

                        # Por corporación
                        corp = metadata.get('corporacion', 'UNKNOWN')
                        stats["by_corporacion"][corp] = stats["by_corporacion"].get(corp, 0) + 1

                        # Por departamento
                        dept = metadata.get('departamento', 'UNKNOWN')
                        stats["by_departamento"][dept] = stats["by_departamento"].get(dept, 0) + 1

                        # Alertas
                        if metadata.get('chunk_type') == 'e14_alert':
                            stats["alerts_count"] += 1
                except:
                    pass

        return stats

    def chat_e14(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 10,
        departamento: str = None,
        municipio: str = None,
        corporacion: str = None
    ) -> Dict[str, Any]:
        """
        Chat especializado para consultas sobre E-14 electorales.

        Args:
            query: Pregunta del usuario sobre datos electorales
            conversation_history: Historial de conversación
            top_k: Documentos a recuperar
            departamento: Filtrar por departamento
            municipio: Filtrar por municipio
            corporacion: Filtrar por corporación

        Returns:
            Respuesta con datos electorales
        """
        # Sistema prompt especializado para E-14
        e14_system_prompt = """Eres CASTOR Electoral, un asistente experto en análisis de resultados electorales de Colombia basado en formularios E-14.

Tu rol es responder preguntas sobre resultados electorales usando ÚNICAMENTE los datos de los formularios E-14 indexados.

DATOS DISPONIBLES EN E-14:
- Resultados por mesa de votación (votos por partido/candidato)
- Ubicación: departamento, municipio, zona, puesto, mesa
- Nivelación: sufragantes, votos en urna, votos computados
- Votos especiales: blancos, nulos, no marcados
- Confianza del OCR y campos que requieren revisión

REGLAS:
1. Responde SOLO con datos del contexto proporcionado
2. Menciona siempre la ubicación (departamento, municipio, mesa) de los datos
3. Si hay alertas de OCR baja confianza, menciónalas
4. Presenta números con formato de miles (ej: 1,234)
5. Si no hay datos suficientes, indica qué información falta
6. NO inventes datos - solo usa lo que está en el contexto

FORMATO DE RESPUESTA:
- Usa listas con viñetas para claridad
- Incluye porcentajes cuando sea relevante
- Agrupa por ubicación si hay múltiples mesas"""

        # Buscar documentos E-14 relevantes
        results = self.search_e14(
            query=query,
            top_k=top_k,
            departamento=departamento,
            municipio=municipio,
            corporacion=corporacion
        )

        # Construir contexto
        context_parts = []
        for result in results:
            doc = result.document
            relevance = f"[Relevancia: {result.score:.0%}]"
            context_parts.append(f"{relevance}\n{doc.content}")

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No hay formularios E-14 indexados para esta consulta."

        # Construir mensajes
        messages = [{"role": "system", "content": e14_system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-6:])

        user_message = f"""DATOS DE FORMULARIOS E-14 INDEXADOS:
{context}

---

PREGUNTA SOBRE RESULTADOS ELECTORALES:
{query}

Responde basándote ÚNICAMENTE en los datos E-14 proporcionados:"""

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Más bajo para respuestas más precisas
                max_tokens=800
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating E-14 chat response: {e}")
            answer = "Error al procesar la consulta. Por favor intenta de nuevo."

        # Construir fuentes
        sources = [
            {
                "id": r.document.id,
                "score": round(r.score, 3),
                "type": r.document.metadata.get("chunk_type", "e14_form"),
                "mesa_id": r.document.metadata.get("mesa_id"),
                "departamento": r.document.metadata.get("departamento"),
                "municipio": r.document.metadata.get("municipio"),
                "corporacion": r.document.metadata.get("corporacion"),
                "preview": r.document.content[:150] + "..." if len(r.document.content) > 150 else r.document.content
            }
            for r in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "e14_documents_found": len(results),
            "filters_applied": {
                "departamento": departamento,
                "municipio": municipio,
                "corporacion": corporacion
            }
        }


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
