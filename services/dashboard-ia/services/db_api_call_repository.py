"""
API Call repository for database operations.
Handles API calls, tweets, and analysis snapshots storage.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from models.database import (
    ApiCall, Tweet, AnalysisSnapshot, PndAxisMetric,
    ForecastSnapshot, CampaignStrategy
)

logger = logging.getLogger(__name__)


class ApiCallRepository:
    """Repository for API call database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    def create_api_call(
        self,
        location: str,
        candidate_name: Optional[str] = None,
        politician: Optional[str] = None,
        topic: Optional[str] = None,
        max_tweets_requested: int = 100,
        time_window_days: int = 7,
        forecast_days: int = 14,
        twitter_query: Optional[str] = None,
        language: str = "es"
    ) -> Optional[ApiCall]:
        """Create a new API call record."""
        session = self._db.get_session()
        try:
            api_call = ApiCall(
                location=location,
                candidate_name=candidate_name,
                politician=politician,
                topic=topic,
                max_tweets_requested=max_tweets_requested,
                time_window_days=time_window_days,
                forecast_days=forecast_days,
                twitter_query=twitter_query,
                language=language,
                status="processing"
            )
            session.add(api_call)
            session.commit()
            session.refresh(api_call)
            logger.info(f"API call created: {api_call.id}")
            return api_call
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating API call: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def update_api_call_status(
        self,
        api_call_id: str,
        status: str,
        tweets_retrieved: int = 0,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update API call status."""
        session = self._db.get_session()
        try:
            api_call = session.query(ApiCall).filter(ApiCall.id == api_call_id).first()
            if not api_call:
                return False

            api_call.status = status
            api_call.tweets_retrieved = tweets_retrieved
            if processing_time_ms:
                api_call.processing_time_ms = processing_time_ms
            if error_message:
                api_call.error_message = error_message

            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating API call: {e}", exc_info=True)
            return False
        finally:
            session.close()

    def get_api_calls(
        self,
        candidate_name: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get API call history with filters."""
        session = self._db.get_session()
        try:
            query = session.query(ApiCall)

            if candidate_name:
                query = query.filter(ApiCall.candidate_name.ilike(f"%{candidate_name}%"))
            if location:
                query = query.filter(ApiCall.location.ilike(f"%{location}%"))

            api_calls = query.order_by(ApiCall.fetched_at.desc()).offset(offset).limit(limit).all()

            return [
                {
                    'id': ac.id,
                    'location': ac.location,
                    'topic': ac.topic,
                    'candidate_name': ac.candidate_name,
                    'politician': ac.politician,
                    'tweets_retrieved': ac.tweets_retrieved,
                    'fetched_at': ac.fetched_at.isoformat() if ac.fetched_at else None,
                    'status': ac.status
                }
                for ac in api_calls
            ]
        except Exception as e:
            logger.error(f"Error getting API calls: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_api_call_with_data(self, api_call_id: str) -> Optional[Dict[str, Any]]:
        """Get full API call with all related data."""
        session = self._db.get_session()
        try:
            api_call = session.query(ApiCall).filter(ApiCall.id == api_call_id).first()
            if not api_call:
                return None

            return {
                'api_call': {
                    'id': api_call.id,
                    'location': api_call.location,
                    'topic': api_call.topic,
                    'candidate_name': api_call.candidate_name,
                    'politician': api_call.politician,
                    'tweets_retrieved': api_call.tweets_retrieved,
                    'fetched_at': api_call.fetched_at.isoformat() if api_call.fetched_at else None,
                    'status': api_call.status
                },
                'tweets_count': len(api_call.tweets),
                'analysis_snapshot': api_call.analysis_snapshot,
                'pnd_metrics': api_call.pnd_metrics,
                'forecast_snapshot': api_call.forecast_snapshot,
                'campaign_strategy': api_call.campaign_strategy
            }
        except Exception as e:
            logger.error(f"Error getting API call with data: {e}", exc_info=True)
            return None
        finally:
            session.close()
