"""
Analysis repository for database operations.
Handles analysis CRUD operations.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from models.database import Analysis

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """Repository for analysis database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    def save_analysis(
        self,
        user_id: str,
        location: str,
        theme: str,
        candidate_name: Optional[str],
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save analysis to database."""
        session = self._db.get_session()
        try:
            analysis = Analysis(
                user_id=user_id,
                location=location,
                theme=theme,
                candidate_name=candidate_name,
                analysis_data=analysis_data
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)

            logger.info(f"Analysis saved: {analysis.id}")
            return str(analysis.id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving analysis: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        include_data: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's analysis history."""
        session = self._db.get_session()
        try:
            analyses = (
                session.query(Analysis)
                .filter(Analysis.user_id == user_id)
                .order_by(Analysis.created_at.desc())
                .limit(limit)
                .all()
            )

            result = []
            for a in analyses:
                item = {
                    'id': str(a.id),
                    'user_id': a.user_id,
                    'location': a.location,
                    'theme': a.theme,
                    'candidate_name': a.candidate_name,
                    'created_at': a.created_at.isoformat() if a.created_at else None
                }
                if include_data:
                    item['analysis_data'] = a.analysis_data
                result.append(item)

            return result
        except Exception as e:
            logger.error(f"Error getting user analyses: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_all_analyses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all analyses from database (for RAG indexing)."""
        session = self._db.get_session()
        try:
            analyses = (
                session.query(Analysis)
                .order_by(Analysis.created_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    'id': str(a.id),
                    'user_id': a.user_id,
                    'location': a.location,
                    'theme': a.theme,
                    'candidate_name': a.candidate_name,
                    'analysis_data': a.analysis_data,
                    'created_at': a.created_at.isoformat() if a.created_at else None
                }
                for a in analyses
            ]
        except Exception as e:
            logger.error(f"Error getting all analyses: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific analysis by ID."""
        session = self._db.get_session()
        try:
            analysis = session.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                return {
                    'id': str(analysis.id),
                    'user_id': analysis.user_id,
                    'location': analysis.location,
                    'theme': analysis.theme,
                    'candidate_name': analysis.candidate_name,
                    'analysis_data': analysis.analysis_data,
                    'created_at': analysis.created_at.isoformat() if analysis.created_at else None
                }
            return None
        except Exception as e:
            logger.error(f"Error getting analysis by ID: {e}", exc_info=True)
            return None
        finally:
            session.close()
