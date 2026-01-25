"""
API v1 RAG (Retrieval Augmented Generation) endpoints.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

rag_v1_bp = Blueprint('rag_v1', __name__, url_prefix='/rag')


class QueryRequest(BaseModel):
    """RAG query request."""
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    """RAG index request."""
    documents: List[Dict[str, Any]]
    source: str = Field(..., min_length=1)


def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, status_code: int = 400):
    return jsonify({"ok": False, "error": error}), status_code


@rag_v1_bp.route('/query', methods=['POST'])
def query():
    """
    POST /api/v1/rag/query

    Query the RAG knowledge base.

    Request:
        {
            "query": "Cual es la propuesta de seguridad?",
            "top_k": 5,
            "filters": { "source": "twitter" }
        }

    Response:
        {
            "ok": true,
            "data": {
                "answer": "Segun los datos...",
                "sources": [
                    { "text": "...", "score": 0.92, "source": "twitter" }
                ]
            }
        }
    """
    try:
        try:
            req = QueryRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        rag_service = current_app.extensions.get('rag_service')
        if not rag_service:
            return error_response("RAG service not available", status_code=503)

        # Retrieve relevant documents
        results = rag_service.retrieve(
            query=req.query,
            top_k=req.top_k,
            filters=req.filters
        )

        # Generate response
        answer = rag_service.generate_response(
            query=req.query,
            context=results
        )

        return success_response({
            "answer": answer,
            "sources": [
                {
                    "text": r.get("text", "")[:200],
                    "score": round(r.get("score", 0.0), 4),
                    "source": r.get("source", "unknown")
                }
                for r in results
            ]
        })

    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@rag_v1_bp.route('/search', methods=['POST'])
def search():
    """
    POST /api/v1/rag/search

    Semantic search without generation.

    Request:
        {
            "query": "propuestas economicas",
            "top_k": 10
        }

    Response:
        {
            "ok": true,
            "data": {
                "results": [
                    { "text": "...", "score": 0.95, "metadata": {...} }
                ]
            }
        }
    """
    try:
        try:
            req = QueryRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        rag_service = current_app.extensions.get('rag_service')
        if not rag_service:
            return error_response("RAG service not available", status_code=503)

        results = rag_service.retrieve(
            query=req.query,
            top_k=req.top_k,
            filters=req.filters
        )

        return success_response({
            "results": [
                {
                    "text": r.get("text", ""),
                    "score": round(r.get("score", 0.0), 4),
                    "metadata": r.get("metadata", {})
                }
                for r in results
            ]
        })

    except Exception as e:
        logger.error(f"RAG search error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@rag_v1_bp.route('/index', methods=['POST'])
def index():
    """
    POST /api/v1/rag/index

    Index documents into RAG knowledge base.

    Request:
        {
            "documents": [
                { "text": "...", "metadata": {...} }
            ],
            "source": "analysis"
        }
    """
    try:
        try:
            req = IndexRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        rag_service = current_app.extensions.get('rag_service')
        if not rag_service:
            return error_response("RAG service not available", status_code=503)

        indexed = rag_service.index_documents(
            documents=req.documents,
            source=req.source
        )

        return success_response({
            "indexed_count": indexed,
            "source": req.source
        }, status_code=201)

    except Exception as e:
        logger.error(f"RAG index error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@rag_v1_bp.route('/stats', methods=['GET'])
def stats():
    """
    GET /api/v1/rag/stats

    Get RAG index statistics.
    """
    try:
        rag_service = current_app.extensions.get('rag_service')
        if not rag_service:
            return error_response("RAG service not available", status_code=503)

        return success_response({
            "document_count": rag_service.vector_store.count() if hasattr(rag_service, 'vector_store') else 0,
            "sources": rag_service.get_sources() if hasattr(rag_service, 'get_sources') else []
        })

    except Exception as e:
        logger.error(f"RAG stats error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)
