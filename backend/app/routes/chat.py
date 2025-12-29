"""
Chat endpoint routes.
AI assistant for campaign advice.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from models.schemas import ChatRequest, ChatResponse
from services import OpenAIService
from utils.rate_limiter import limiter

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize service
openai_service = None


def get_openai_service():
    """Lazy initialization of OpenAI service."""
    global openai_service
    if openai_service is None:
        openai_service = OpenAIService()
    return openai_service


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

