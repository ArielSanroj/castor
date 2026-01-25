"""
API v1 Twitter Search endpoints.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List

logger = logging.getLogger(__name__)

twitter_v1_bp = Blueprint('twitter_v1', __name__, url_prefix='/twitter')


class SearchRequest(BaseModel):
    """Twitter search request."""
    query: str = Field(..., min_length=2, max_length=500)
    max_results: int = Field(10, ge=10, le=100)
    location: Optional[str] = None
    lang: str = Field("es")


def success_response(data: dict, status_code: int = 200):
    return jsonify({"ok": True, "data": data}), status_code


def error_response(error: str, status_code: int = 400):
    return jsonify({"ok": False, "error": error}), status_code


@twitter_v1_bp.route('/search', methods=['POST'])
def search():
    """
    POST /api/v1/twitter/search

    Search tweets.

    Request:
        {
            "query": "elecciones Colombia",
            "max_results": 50,
            "location": "Bogota",
            "lang": "es"
        }

    Response:
        {
            "ok": true,
            "data": {
                "tweets": [
                    {
                        "id": "123456",
                        "text": "...",
                        "author": "usuario",
                        "created_at": "2024-01-01T00:00:00Z",
                        "metrics": { "likes": 10, "retweets": 5 }
                    }
                ],
                "meta": {
                    "result_count": 50,
                    "query": "elecciones Colombia"
                }
            }
        }
    """
    try:
        try:
            req = SearchRequest(**request.get_json())
        except ValidationError as e:
            return error_response("Validation error")

        twitter_service = current_app.extensions.get('twitter_service')
        if not twitter_service:
            return error_response("Twitter service not available", status_code=503)

        # Search tweets
        tweets = twitter_service.search_tweets(
            query=req.query,
            max_results=req.max_results,
            location=req.location
        )

        # Format response
        formatted_tweets = []
        for tweet in tweets:
            formatted_tweets.append({
                "id": tweet.get("id"),
                "text": tweet.get("text"),
                "author": tweet.get("author_username"),
                "author_name": tweet.get("author_name"),
                "created_at": tweet.get("created_at"),
                "metrics": {
                    "likes": tweet.get("like_count", 0),
                    "retweets": tweet.get("retweet_count", 0),
                    "replies": tweet.get("reply_count", 0)
                }
            })

        return success_response({
            "tweets": formatted_tweets,
            "meta": {
                "result_count": len(formatted_tweets),
                "query": req.query
            }
        })

    except Exception as e:
        logger.error(f"Twitter search error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)


@twitter_v1_bp.route('/trending', methods=['GET'])
def trending():
    """
    GET /api/v1/twitter/trending

    Get trending topics.

    Query params:
        - location: Location filter
        - limit: Max results (default 20)

    Response:
        {
            "ok": true,
            "data": {
                "topics": [
                    { "topic": "#Elecciones2026", "score": 0.95, "tweet_count": 1500 }
                ]
            }
        }
    """
    try:
        location = request.args.get('location', 'Colombia')
        limit = min(int(request.args.get('limit', 20)), 50)

        trending_service = current_app.extensions.get('trending_service')
        if not trending_service:
            return error_response("Trending service not available", status_code=503)

        topics = trending_service.detect_trending_topics(
            location=location,
            limit=limit
        )

        return success_response({
            "topics": topics,
            "location": location
        })

    except Exception as e:
        logger.error(f"Trending error: {e}", exc_info=True)
        return error_response("Internal server error", status_code=500)
