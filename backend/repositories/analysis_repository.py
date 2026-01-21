"""
Analysis Repository.
Handles all analysis-related data access operations.
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models.database import (
    Analysis, AnalysisTopic, AnalysisRecommendation,
    AnalysisSpeech, UserMetrics
)
from .base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    """Repository for Analysis entity operations."""

    def __init__(self, session: Session):
        """Initialize analysis repository."""
        super().__init__(session, Analysis)

    def create(
        self,
        user_id: str,
        location: str,
        theme: str,
        candidate_name: Optional[str],
        analysis_data: Dict[str, Any]
    ) -> Analysis:
        """
        Create a new analysis.

        Args:
            user_id: User ID who created the analysis
            location: Location analyzed
            theme: Theme/topic analyzed
            candidate_name: Optional candidate name
            analysis_data: Analysis results data

        Returns:
            Created analysis
        """
        analysis = Analysis(
            user_id=user_id,
            location=location,
            theme=theme,
            candidate_name=candidate_name,
            analysis_data=analysis_data
        )
        self.add(analysis)
        return analysis

    def get_by_user(
        self,
        user_id: str,
        limit: int = 10,
        include_data: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get analyses for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of results
            include_data: Whether to include full analysis data

        Returns:
            List of analysis dictionaries
        """
        analyses = (
            self._session.query(Analysis)
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

    def get_by_location(self, location: str, limit: int = 50) -> List[Analysis]:
        """
        Get analyses for a specific location.

        Args:
            location: Location name
            limit: Maximum number of results

        Returns:
            List of analyses
        """
        return (
            self._session.query(Analysis)
            .filter(Analysis.location == location)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_theme(self, theme: str, limit: int = 50) -> List[Analysis]:
        """
        Get analyses for a specific theme.

        Args:
            theme: Theme name
            limit: Maximum number of results

        Returns:
            List of analyses
        """
        return (
            self._session.query(Analysis)
            .filter(Analysis.theme == theme)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most recent analyses.

        Args:
            limit: Maximum number of results

        Returns:
            List of analysis dictionaries
        """
        analyses = (
            self._session.query(Analysis)
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

    def to_dict(self, analysis: Analysis) -> Dict[str, Any]:
        """
        Convert analysis to dictionary.

        Args:
            analysis: Analysis entity

        Returns:
            Dictionary representation
        """
        return {
            'id': str(analysis.id),
            'user_id': analysis.user_id,
            'location': analysis.location,
            'theme': analysis.theme,
            'candidate_name': analysis.candidate_name,
            'tweets_analyzed': analysis.tweets_analyzed,
            'sentiment_positive': analysis.sentiment_positive,
            'sentiment_negative': analysis.sentiment_negative,
            'sentiment_neutral': analysis.sentiment_neutral,
            'trending_topic': analysis.trending_topic,
            'analysis_data': analysis.analysis_data,
            'created_at': analysis.created_at.isoformat() if analysis.created_at else None
        }

    # ==========================================
    # New normalized data queries
    # ==========================================

    def get_critical_topics(
        self,
        location: Optional[str] = None,
        min_negative: float = 0.3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get topics with highest negative sentiment.

        Args:
            location: Optional location filter
            min_negative: Minimum negative sentiment threshold
            limit: Max results

        Returns:
            List of critical topics with stats
        """
        query = (
            self._session.query(
                AnalysisTopic.topic_name,
                func.avg(AnalysisTopic.sentiment_negative).label('avg_negative'),
                func.avg(AnalysisTopic.sentiment_positive).label('avg_positive'),
                func.sum(AnalysisTopic.tweet_count).label('total_mentions'),
                func.count(AnalysisTopic.id).label('analyses_count')
            )
            .join(Analysis)
        )

        if location:
            query = query.filter(Analysis.location == location)

        results = (
            query
            .group_by(AnalysisTopic.topic_name)
            .having(func.avg(AnalysisTopic.sentiment_negative) >= min_negative)
            .order_by(desc('avg_negative'))
            .limit(limit)
            .all()
        )

        return [
            {
                'topic_name': r.topic_name,
                'avg_negative': round(r.avg_negative, 3),
                'avg_positive': round(r.avg_positive, 3),
                'total_mentions': r.total_mentions,
                'analyses_count': r.analyses_count
            }
            for r in results
        ]

    def get_location_summary(self, location: str) -> Dict[str, Any]:
        """
        Get summary statistics for a location.

        Args:
            location: Location name

        Returns:
            Summary statistics
        """
        analyses = (
            self._session.query(Analysis)
            .filter(Analysis.location == location)
            .all()
        )

        if not analyses:
            return {'location': location, 'total_analyses': 0}

        return {
            'location': location,
            'total_analyses': len(analyses),
            'candidates_analyzed': len(set(a.candidate_name for a in analyses if a.candidate_name)),
            'avg_positive': round(sum(a.sentiment_positive or 0 for a in analyses) / len(analyses), 3),
            'avg_negative': round(sum(a.sentiment_negative or 0 for a in analyses) / len(analyses), 3),
            'total_tweets': sum(a.tweets_analyzed or 0 for a in analyses),
            'last_analysis': max(a.created_at for a in analyses).isoformat() if analyses else None
        }

    def get_candidate_comparison(self, location: str) -> List[Dict[str, Any]]:
        """
        Compare candidates in a location.

        Args:
            location: Location name

        Returns:
            List of candidate stats
        """
        results = (
            self._session.query(
                Analysis.candidate_name,
                func.count(Analysis.id).label('total_analyses'),
                func.avg(Analysis.sentiment_positive).label('avg_positive'),
                func.avg(Analysis.sentiment_negative).label('avg_negative'),
                func.max(Analysis.created_at).label('last_analysis')
            )
            .filter(Analysis.location == location)
            .filter(Analysis.candidate_name.isnot(None))
            .group_by(Analysis.candidate_name)
            .order_by(desc('avg_positive'))
            .all()
        )

        return [
            {
                'candidate_name': r.candidate_name,
                'total_analyses': r.total_analyses,
                'avg_positive': round(r.avg_positive, 3) if r.avg_positive else 0,
                'avg_negative': round(r.avg_negative, 3) if r.avg_negative else 0,
                'favorability': round((r.avg_positive - r.avg_negative) * 100, 1) if r.avg_positive else 0,
                'last_analysis': r.last_analysis.isoformat() if r.last_analysis else None
            }
            for r in results
        ]

    def get_sentiment_trend(
        self,
        location: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get sentiment trend over time for a location.

        Args:
            location: Location name
            days: Number of days to look back

        Returns:
            List of daily sentiment averages
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        results = (
            self._session.query(
                func.date(Analysis.created_at).label('date'),
                func.avg(Analysis.sentiment_positive).label('avg_positive'),
                func.avg(Analysis.sentiment_negative).label('avg_negative'),
                func.count(Analysis.id).label('analyses_count')
            )
            .filter(Analysis.location == location)
            .filter(Analysis.created_at >= cutoff)
            .group_by(func.date(Analysis.created_at))
            .order_by('date')
            .all()
        )

        return [
            {
                'date': str(r.date),
                'avg_positive': round(r.avg_positive, 3) if r.avg_positive else 0,
                'avg_negative': round(r.avg_negative, 3) if r.avg_negative else 0,
                'analyses_count': r.analyses_count
            }
            for r in results
        ]

    def get_priority_recommendations(
        self,
        user_id: Optional[str] = None,
        priority: str = 'alta',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get high priority recommendations.

        Args:
            user_id: Optional user filter
            priority: Priority level
            limit: Max results

        Returns:
            List of recommendations
        """
        query = (
            self._session.query(AnalysisRecommendation)
            .join(Analysis)
            .filter(AnalysisRecommendation.priority == priority)
        )

        if user_id:
            query = query.filter(Analysis.user_id == user_id)

        results = (
            query
            .order_by(desc(Analysis.created_at))
            .limit(limit)
            .all()
        )

        return [
            {
                'id': str(r.id),
                'type': r.recommendation_type,
                'priority': r.priority,
                'content': r.content,
                'topic_related': r.topic_related,
                'location': r.analysis.location,
                'candidate': r.analysis.candidate_name,
                'created_at': r.created_at.isoformat() if r.created_at else None
            }
            for r in results
        ]

    def get_trending_topics_by_location(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending topics aggregated by location.

        Returns:
            List of trending topics with stats
        """
        results = (
            self._session.query(
                Analysis.location,
                Analysis.trending_topic,
                func.count(Analysis.id).label('appearances'),
                func.avg(Analysis.sentiment_positive).label('avg_sentiment')
            )
            .filter(Analysis.trending_topic.isnot(None))
            .group_by(Analysis.location, Analysis.trending_topic)
            .order_by(desc('appearances'))
            .limit(limit)
            .all()
        )

        return [
            {
                'location': r.location,
                'trending_topic': r.trending_topic,
                'appearances': r.appearances,
                'avg_sentiment': round(r.avg_sentiment, 3) if r.avg_sentiment else 0
            }
            for r in results
        ]
