"""
Chat endpoint routes.
AI assistant for campaign advice with RAG support.
Implements fallback chain: RAG -> OpenAI -> Llama (local)
"""
import logging
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from models.schemas import ChatRequest, ChatResponse
from services import OpenAIService
from services.rag_service import get_rag_service
from services.llm.local_provider import LocalLLMProvider
from services.llm.base import LLMMessage
from app.schemas.rag import (
    RAGChatRequest,
    RAGChatResponse,
    RAGSource,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGStatsResponse
)
from utils.rate_limiter import limiter
from utils.response_helpers import service_factory

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)


def get_openai_service():
    """Thread-safe lazy initialization of OpenAI service."""
    return service_factory.get_or_create('openai', OpenAIService)


def get_rag():
    """Get RAG service instance."""
    try:
        return get_rag_service()
    except Exception as e:
        logger.warning(f"RAG service unavailable: {e}")
        return None


def get_local_llm():
    """Get Local LLM (Llama) service instance."""
    try:
        provider = LocalLLMProvider()
        if provider._available:
            return provider
        return None
    except Exception as e:
        logger.warning(f"Local LLM unavailable: {e}")
        return None


# Minimum documents required for RAG to be considered sufficient
MIN_RAG_DOCUMENTS = 2
# Minimum score threshold for relevant documents
MIN_RELEVANCE_SCORE = 0.4


@chat_bp.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")  # Chat can be more frequent
@jwt_required(optional=True)
def chat():
    """
    Chat endpoint for AI campaign assistant.
    
    Request body:
    {
        "message": "¿Cómo puedo mejorar mi campaña?",
        "context": {...},
        "conversation_id": "optional-id"
    }
    
    Returns:
        ChatResponse with AI response
    """
    try:
        req_data = request.get_json() or {}
        
        # Validate request
        try:
            chat_req = ChatRequest(**req_data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Invalid request data',
                'details': str(e)
            }), 400
        
        # Get OpenAI service
        openai_svc = get_openai_service()
        
        # Generate response
        response_text = openai_svc.chat(
            message=chat_req.message,
            context=chat_req.context
        )
        
        # Build response
        response = ChatResponse(
            success=True,
            response=response_text,
            conversation_id=chat_req.conversation_id
        )
        
        return jsonify(response.dict()), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@chat_bp.route('/chat/topic', methods=['POST'])
@limiter.limit("20 per minute")
def chat_about_topic():
    """
    Answer questions about a specific topic using the analysis context.

    Request body:
    {
        "question": "Que dicen sobre reforma pensional?",
        "topic": "Reforma pensional",
        "context": { topic data },
        "analysis_data": { full analysis }
    }
    """
    try:
        payload = request.get_json() or {}

        question = payload.get("question", "").strip()
        topic = payload.get("topic")
        context = payload.get("context", {})
        analysis_data = payload.get("analysis_data", {})

        if not question:
            return jsonify({
                "success": False,
                "error": "La pregunta es requerida"
            }), 400

        # Build context for the LLM
        topic_context = build_topic_context(topic, context, analysis_data)

        # Try to use OpenAI service
        try:
            openai_svc = get_openai_service()
            answer = generate_topic_answer(openai_svc, question, topic, topic_context)
        except Exception as e:
            logger.warning(f"OpenAI unavailable, using fallback: {e}")
            answer = generate_fallback_answer(question, topic, context, analysis_data)

        return jsonify({
            "success": True,
            "answer": answer,
            "topic": topic
        })

    except Exception as e:
        logger.error(f"Error in chat_about_topic: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error procesando la pregunta"
        }), 500


def build_topic_context(topic: str, context: dict, analysis_data: dict) -> str:
    """Build a comprehensive context string for the LLM."""
    parts = []

    if topic:
        parts.append(f"Tema principal: {topic}")

    if context:
        if context.get("tweet_count"):
            parts.append(f"Menciones totales: {context['tweet_count']}")

        sentiment = context.get("sentiment", {})
        if sentiment:
            pos = round((sentiment.get("positive", 0)) * 100)
            neg = round((sentiment.get("negative", 0)) * 100)
            neu = round((sentiment.get("neutral", 0)) * 100)
            parts.append(f"Sentimiento: {pos}% favorable, {neu}% neutral, {neg}% critico")

    # Add other topics for context
    if analysis_data:
        topics = analysis_data.get("topics", [])
        if topics:
            other_topics = [t["topic"] for t in topics if t["topic"] != topic][:5]
            if other_topics:
                parts.append(f"Otros temas en la conversacion: {', '.join(other_topics)}")

        overall = analysis_data.get("sentiment_overview", {})
        if overall:
            parts.append(f"Tono general: {round(overall.get('positive', 0) * 100)}% favorable")

    return "\n".join(parts)


def generate_topic_answer(openai_svc, question: str, topic: str, context: str) -> str:
    """Generate an answer using OpenAI."""
    system_prompt = """Eres un analista politico experto en Colombia.
Respondes preguntas sobre temas de conversacion en redes sociales de manera concisa.
Usa el contexto proporcionado para dar respuestas informadas.
Responde en espanol, de manera directa y accionable.
Limita tu respuesta a 2-3 oraciones maximo."""

    user_prompt = f"""Contexto del analisis:
{context}

Pregunta sobre el tema "{topic or 'general'}":
{question}

Responde concisamente:"""

    response = openai_svc.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=200,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


def generate_fallback_answer(question: str, topic: str, context: dict, analysis_data: dict) -> str:
    """Generate a basic answer without LLM when OpenAI is unavailable."""
    question_lower = question.lower()

    sentiment = context.get("sentiment", {})
    pos = round((sentiment.get("positive", 0)) * 100)
    neg = round((sentiment.get("negative", 0)) * 100)
    mentions = context.get("tweet_count", 0)

    if any(word in question_lower for word in ["critica", "criticas", "negativo", "problema"]):
        if neg > 40:
            return f"El tema '{topic}' tiene nivel critico alto ({neg}% negativo). Las preocupaciones se centran en implementacion e impactos."
        elif neg > 20:
            return f"Criticas moderadas ({neg}%) sobre '{topic}'. Se recomienda monitorear la evolucion."
        else:
            return f"Las criticas sobre '{topic}' son bajas ({neg}%). El tono general es favorable."

    if any(word in question_lower for word in ["oportunidad", "positivo", "favorable"]):
        if pos > 50:
            return f"'{topic}' tiene buena recepcion ({pos}% favorable). Oportunidad para reforzar el mensaje."
        else:
            return f"Espacio para mejorar percepcion de '{topic}' (actualmente {pos}% favorable)."

    if any(word in question_lower for word in ["tono", "sentimiento", "percepcion"]):
        tone = "favorable" if pos > neg + 20 else "critico" if neg > pos + 20 else "mixto"
        return f"Tono sobre '{topic}': {tone} - {pos}% favorable, {neg}% critico ({mentions} menciones)."

    if any(word in question_lower for word in ["cuanto", "menciones", "volumen"]):
        return f"Se detectaron {mentions} menciones sobre '{topic}'. Presencia {'significativa' if mentions > 100 else 'moderada'}."

    return f"'{topic}': {mentions} menciones, {pos}% favorable, {neg}% critico. Especifica que aspecto explorar."


# =============================================================================
# RAG CHAT ENDPOINTS
# =============================================================================

@chat_bp.route('/chat/rag', methods=['POST'])
@limiter.limit("15 per minute")
@jwt_required(optional=True)
def rag_chat():
    """
    RAG-powered chat endpoint.
    Uses indexed analysis data to provide context-aware responses.

    Request body:
    {
        "message": "Que temas tienen mejor recepcion?",
        "conversation_id": "optional-id",
        "conversation_history": [...],
        "top_k": 5,
        "min_score": 0.3,
        "filter_location": "Bogota",
        "filter_topic": "Seguridad"
    }

    Returns:
        RAGChatResponse with answer and sources
    """
    try:
        payload = request.get_json() or {}

        # Validate request
        try:
            req = RAGChatRequest(**payload)
        except ValidationError as e:
            return jsonify({
                "success": False,
                "error": "Invalid request data",
                "details": e.errors()
            }), 400

        # Get RAG service
        rag = get_rag()
        if rag is None:
            # Fallback to regular chat
            return _fallback_to_regular_chat(req.message)

        # Build metadata filters
        filters = {}
        if req.filter_location:
            filters["location"] = req.filter_location
        if req.filter_topic:
            filters["topic_name"] = req.filter_topic

        # Perform RAG chat
        result = rag.chat(
            query=req.message,
            conversation_history=req.conversation_history,
            top_k=req.top_k,
            location_filter=req.filter_location,
            topic_filter=req.filter_topic
        )

        docs_retrieved = result.get("documents_retrieved", 0)
        sources_data = result.get("sources", [])

        # Check if RAG has sufficient information
        # Criteria: at least MIN_RAG_DOCUMENTS with good relevance scores
        has_sufficient_info = docs_retrieved >= MIN_RAG_DOCUMENTS

        # Also check if the answer indicates lack of information
        answer_text = result.get("answer", "").lower()
        lacks_info_phrases = [
            "no tengo información",
            "no hay datos",
            "no se encontr",
            "no puedo proporcionar",
            "no dispongo",
            "no cuento con",
            "contexto proporcionado no",
            "no ofrece suficiente",
            "no contienen",
            "no contiene",
            "insuficiente",
            "no se han analizado",
            "tweets analizados: 0",
            "sin información",
            "falta de datos",
            "sugiero realizar",
            "sería necesario realizar",
            "para obtener un análisis más completo",
            "limita la capacidad"
        ]
        answer_lacks_info = any(phrase in answer_text for phrase in lacks_info_phrases)

        # If insufficient RAG info, use fallback chain (OpenAI -> Llama)
        # Use fallback if: no docs, OR answer indicates lack of info
        if docs_retrieved == 0 or answer_lacks_info:
            logger.info(f"RAG insufficient (docs={docs_retrieved}, lacks_info={answer_lacks_info}), using fallback")

            # Build context from whatever RAG found (if any)
            rag_context = ""
            if sources_data:
                rag_context = "Información parcial encontrada:\n"
                for s in sources_data[:3]:
                    rag_context += f"- {s.get('title', 'Análisis')}: {s.get('content', '')[:200]}...\n"

            fallback_response, status = _fallback_to_regular_chat(req.message, context=rag_context)
            if status == 200:
                resp_payload = fallback_response.get_json()
                resp_payload["rag_documents_found"] = docs_retrieved
                resp_payload["message"] = "Información insuficiente en RAG, respuesta generada con IA"
                return jsonify(resp_payload), 200
            return fallback_response, status

        # Build response with RAG data
        sources = [
            RAGSource(**s) for s in sources_data
        ]

        response = RAGChatResponse(
            success=True,
            answer=result["answer"],
            sources=sources,
            conversation_id=req.conversation_id or str(uuid.uuid4()),
            documents_searched=result.get("documents_searched", 0),
            documents_retrieved=result.get("documents_retrieved", 0)
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error in RAG chat: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error processing question"
        }), 500


@chat_bp.route('/chat/rag/index', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required(optional=True)
def rag_index():
    """
    Index an analysis into the RAG knowledge base.

    Request body:
    {
        "analysis_id": "unique-id",
        "analysis_data": {...},
        "metadata": {...}
    }

    Returns:
        RAGIndexResponse with document IDs
    """
    try:
        payload = request.get_json() or {}

        # Validate request
        try:
            req = RAGIndexRequest(**payload)
        except ValidationError as e:
            return jsonify({
                "success": False,
                "error": "Invalid request data",
                "details": e.errors()
            }), 400

        # Get RAG service
        rag = get_rag()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        # Index the analysis
        doc_ids = rag.index_analysis(
            analysis_id=req.analysis_id,
            analysis_data=req.analysis_data,
            metadata=req.metadata
        )

        response = RAGIndexResponse(
            success=True,
            analysis_id=req.analysis_id,
            documents_created=len(doc_ids),
            document_ids=doc_ids
        )

        return jsonify(response.model_dump()), 201

    except Exception as e:
        logger.error(f"Error indexing analysis: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error indexing analysis"
        }), 500


@chat_bp.route('/chat/rag/stats', methods=['GET'])
@limiter.limit("30 per minute")
def rag_stats():
    """
    Get RAG service statistics.

    Returns:
        RAGStatsResponse with index stats
    """
    try:
        rag = get_rag()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        stats = rag.get_stats()

        response = RAGStatsResponse(
            success=True,
            documents_indexed=stats["documents_indexed"],
            embedding_model=stats["embedding_model"],
            generation_model=stats["generation_model"]
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error getting stats"
        }), 500


@chat_bp.route('/chat/rag/search', methods=['POST'])
@limiter.limit("20 per minute")
def rag_search():
    """
    Search the RAG knowledge base without generating a response.
    Useful for debugging and exploring indexed content.

    Request body:
    {
        "query": "search query",
        "top_k": 5,
        "min_score": 0.3
    }
    """
    try:
        payload = request.get_json() or {}
        query = payload.get("query", "").strip()
        top_k = payload.get("top_k", 5)
        min_score = payload.get("min_score", 0.3)

        if not query:
            return jsonify({
                "success": False,
                "error": "Query is required"
            }), 400

        rag = get_rag()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        # Perform search
        results = rag.retrieve(query, top_k=top_k, min_score=min_score)

        documents = [
            {
                "id": r.document.id,
                "score": round(r.score, 4),
                "rank": r.rank,
                "content": r.document.content,
                "metadata": r.document.metadata
            }
            for r in results
        ]

        return jsonify({
            "success": True,
            "query": query,
            "results": documents,
            "total_found": len(documents)
        }), 200

    except Exception as e:
        logger.error(f"Error in RAG search: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error searching"
        }), 500


def _fallback_to_regular_chat(message: str, context: str = "") -> tuple:
    """
    Fallback chain: OpenAI -> Llama (local)
    Used when RAG doesn't have sufficient information.
    """
    # Build the prompt with context if available
    system_prompt = """Eres CASTOR, un asistente experto en estrategia electoral y análisis político en Colombia.
Responde de manera clara, estructurada y útil. Usa formato con negritas (**texto**) para resaltar puntos importantes.
Si no tienes información específica sobre un candidato, proporciona recomendaciones generales basadas en buenas prácticas de estrategia electoral."""

    full_message = message
    if context:
        full_message = f"Contexto disponible:\n{context}\n\nPregunta: {message}"

    # Try OpenAI first
    try:
        logger.info("Attempting OpenAI fallback...")
        openai_svc = get_openai_service()
        response_text = openai_svc.chat(message=full_message, context={"system_prompt": system_prompt})
        return jsonify({
            "success": True,
            "answer": response_text,
            "sources": [],
            "fallback": "openai",
            "message": "Respuesta generada con OpenAI"
        }), 200
    except Exception as e:
        logger.warning(f"OpenAI fallback failed: {e}")

    # Try Llama (local) as last resort
    try:
        logger.info("Attempting Llama (local) fallback...")
        local_llm = get_local_llm()
        if local_llm:
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=full_message)
            ]
            response = local_llm.complete(messages)
            return jsonify({
                "success": True,
                "answer": response.content,
                "sources": [],
                "fallback": "llama",
                "message": "Respuesta generada con Llama (local)"
            }), 200
    except Exception as e:
        logger.warning(f"Llama fallback failed: {e}")

    # All fallbacks failed
    logger.error("All chat fallbacks failed")
    return jsonify({
        "success": False,
        "error": "No hay servicios de chat disponibles. Verifica la conexión."
    }), 503


@chat_bp.route('/chat/rag/sync', methods=['POST'])
@limiter.limit("5 per minute")
@jwt_required(optional=True)
def rag_sync():
    """
    Sync RAG index with database history.
    Loads all historical analyses into the vector store.

    Request body (optional):
    {
        "limit": 100  // Max analyses to sync
    }
    """
    try:
        from flask import current_app
        from services.rag_service import get_rag_service
        from services.database_service import DatabaseService

        payload = request.get_json() or {}
        limit = payload.get("limit", 100)

        rag = get_rag_service()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        # Get database service from app extensions or create new one
        db_service = current_app.extensions.get("database_service")
        if not db_service:
            try:
                db_service = DatabaseService()
            except Exception as db_exc:
                logger.error(f"Could not create database service: {db_exc}")
                return jsonify({
                    "success": False,
                    "error": f"Database service not available: {str(db_exc)}"
                }), 503

        rag.set_db_service(db_service)
        count = rag.sync_from_database(limit=limit)

        return jsonify({
            "success": True,
            "documents_synced": count,
            "total_indexed": rag.vector_store.count()
        }), 200

    except Exception as e:
        logger.error(f"Error syncing RAG: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Error syncing with database: {str(e)}"
        }), 500


@chat_bp.route('/chat/rag/sync-latest', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required(optional=True)
def rag_sync_latest():
    """
    Sync RAG with the latest API call only.
    Quick sync for chat initialization.
    """
    try:
        from flask import current_app
        from services.rag_service import get_rag_service
        from services.database_service import DatabaseService

        rag = get_rag_service()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        # Get database service
        db_service = current_app.extensions.get("database_service")
        if not db_service:
            try:
                db_service = DatabaseService()
            except Exception as db_exc:
                return jsonify({
                    "success": False,
                    "error": f"Database not available: {str(db_exc)}"
                }), 503

        # Get latest API call
        api_calls = db_service.get_api_calls(limit=1)
        if not api_calls:
            return jsonify({
                "success": True,
                "message": "No hay análisis en la base de datos",
                "documents_synced": 0,
                "total_indexed": rag.vector_store.count()
            }), 200

        api_call = api_calls[0]
        api_call_id = api_call.get('id')
        indexed_count = 0

        # Get full data
        full_data = db_service.get_api_call_with_data(api_call_id)
        if full_data:
            metadata = {
                "location": api_call.get('location', 'Colombia'),
                "candidate_name": api_call.get('candidate_name', ''),
                "politician": api_call.get('politician', ''),
                "topic": api_call.get('topic', ''),
                "created_at": api_call.get('fetched_at', '')
            }

            # Index snapshot
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
                rag.index_analysis_snapshot(api_call_id, snapshot_data, metadata)
                indexed_count += 1

            # Index tweets
            tweets = db_service.get_tweets_by_api_call(api_call_id, limit=200)
            if tweets:
                docs = rag.index_tweets(api_call_id, tweets, metadata)
                indexed_count += docs

            # Index PND metrics
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
                docs = rag.index_pnd_metrics(api_call_id, pnd_data, metadata)
                indexed_count += docs

        return jsonify({
            "success": True,
            "message": f"Sincronizado con análisis de {api_call.get('candidate_name', 'N/A')} en {api_call.get('location', 'N/A')}",
            "api_call_id": api_call_id,
            "documents_synced": indexed_count,
            "total_indexed": rag.vector_store.count(),
            "tweets_count": api_call.get('tweets_retrieved', 0)
        }), 200

    except Exception as e:
        logger.error(f"Error syncing latest: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Error: {str(e)}"
        }), 500


@chat_bp.route('/chat/rag/clear', methods=['POST'])
@limiter.limit("2 per minute")
@jwt_required()
def rag_clear():
    """Clear the RAG index (admin only)."""
    try:
        from services.rag_service import get_rag_service

        rag = get_rag_service()
        if rag is None:
            return jsonify({
                "success": False,
                "error": "RAG service unavailable"
            }), 503

        rag.clear_index()

        return jsonify({
            "success": True,
            "message": "RAG index cleared"
        }), 200

    except Exception as e:
        logger.error(f"Error clearing RAG: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Error clearing index"
        }), 500
