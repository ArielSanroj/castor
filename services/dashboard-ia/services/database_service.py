"""
Database service using SQLAlchemy.
Main service delegating to domain-specific repositories.
"""
import logging
from typing import Optional, Dict, Any, List, Generator

from sqlalchemy.orm import Session

from models.database import User, TrendingTopic, CampaignAction, Lead, ApiCall

from .db_base import DatabaseBase
from .db_user_repository import UserRepository
from .db_analysis_repository import AnalysisRepository
from .db_lead_repository import LeadRepository
from .db_campaign_repository import CampaignRepository
from .db_api_call_repository import ApiCallRepository
from .db_tweet_repository import TweetRepository
from .db_snapshot_repository import SnapshotRepository

logger = logging.getLogger(__name__)


class DatabaseService(DatabaseBase):
    """Service for database operations using SQLAlchemy."""

    def __init__(self):
        """Initialize database connection and repositories."""
        super().__init__()
        self._users = UserRepository(self)
        self._analyses = AnalysisRepository(self)
        self._leads = LeadRepository(self)
        self._campaigns = CampaignRepository(self)
        self._api_calls = ApiCallRepository(self)
        self._tweets = TweetRepository(self)
        self._snapshots = SnapshotRepository(self)
        logger.info("DatabaseService initialized with all repositories")

    # =========================================================================
    # User operations (delegated to UserRepository)
    # =========================================================================

    def create_user(
        self,
        email: str,
        password: str,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        campaign_role: Optional[str] = None,
        candidate_position: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        whatsapp_opt_in: bool = False
    ) -> Optional[User]:
        """Create a new user."""
        return self._users.create_user(
            email, password, phone, first_name, last_name,
            campaign_role, candidate_position, whatsapp_number, whatsapp_opt_in
        )

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user and return user if valid."""
        return self._users.authenticate_user(email, password)

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get_user(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self._users.get_user_by_email(email)

    # =========================================================================
    # Analysis operations (delegated to AnalysisRepository)
    # =========================================================================

    def save_analysis(
        self,
        user_id: str,
        location: str,
        theme: str,
        candidate_name: Optional[str],
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save analysis to database."""
        return self._analyses.save_analysis(user_id, location, theme, candidate_name, analysis_data)

    def get_user_analyses(self, user_id: str, limit: int = 10, include_data: bool = False) -> List[Dict[str, Any]]:
        """Get user's analysis history."""
        return self._analyses.get_user_analyses(user_id, limit, include_data)

    def get_all_analyses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all analyses from database (for RAG indexing)."""
        return self._analyses.get_all_analyses(limit)

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific analysis by ID."""
        return self._analyses.get_analysis_by_id(analysis_id)

    # =========================================================================
    # Lead operations (delegated to LeadRepository)
    # =========================================================================

    def create_lead(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        interest: str,
        location: str,
        candidacy_type: Optional[str] = None,
        status: str = "nuevo",
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Lead]:
        """Create a new lead (demo request)."""
        return self._leads.create_lead(
            first_name, last_name, email, phone, interest, location,
            candidacy_type, status, notes, metadata
        )

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        return self._leads.get_lead(lead_id)

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email."""
        return self._leads.get_lead_by_email(email)

    def get_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Lead]:
        """Get leads with optional filters."""
        return self._leads.get_leads(status, candidacy_type, limit, offset)

    def update_lead_status(self, lead_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update lead status."""
        return self._leads.update_lead_status(lead_id, status, notes)

    def count_leads(self, status: Optional[str] = None, candidacy_type: Optional[str] = None) -> int:
        """Count leads with optional filters."""
        return self._leads.count_leads(status, candidacy_type)

    # =========================================================================
    # Campaign operations (delegated to CampaignRepository)
    # =========================================================================

    def save_trending_topic(self, topic_data: Dict[str, Any]) -> Optional[str]:
        """Save trending topic."""
        return self._campaigns.save_trending_topic(topic_data)

    def get_active_trending_topics(self, location: Optional[str] = None, limit: int = 10) -> List[TrendingTopic]:
        """Get active trending topics."""
        return self._campaigns.get_active_trending_topics(location, limit)

    def add_signature(
        self,
        user_id: str,
        campaign_id: str,
        signer_name: str,
        signer_email: str,
        signer_phone: Optional[str] = None,
        signer_id_number: Optional[str] = None,
        location: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """Add a signature to a campaign."""
        return self._campaigns.add_signature(
            user_id, campaign_id, signer_name, signer_email,
            signer_phone, signer_id_number, location, ip_address, user_agent
        )

    def get_campaign_signatures(self, campaign_id: str) -> int:
        """Get count of signatures for a campaign."""
        return self._campaigns.get_campaign_signatures(campaign_id)

    def save_campaign_action(self, action_data: Dict[str, Any]) -> Optional[str]:
        """Save campaign action."""
        return self._campaigns.save_campaign_action(action_data)

    def get_effective_strategies(self, user_id: str, limit: int = 5) -> List[CampaignAction]:
        """Get most effective campaign strategies."""
        return self._campaigns.get_effective_strategies(user_id, limit)

    def save_vote_strategy(self, strategy_data: Dict[str, Any]) -> Optional[str]:
        """Save vote-winning strategy."""
        return self._campaigns.save_vote_strategy(strategy_data)

    # =========================================================================
    # API Call operations (delegated to ApiCallRepository)
    # =========================================================================

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
        return self._api_calls.create_api_call(
            location, candidate_name, politician, topic,
            max_tweets_requested, time_window_days, forecast_days,
            twitter_query, language
        )

    def update_api_call_status(
        self,
        api_call_id: str,
        status: str,
        tweets_retrieved: int = 0,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update API call status."""
        return self._api_calls.update_api_call_status(
            api_call_id, status, tweets_retrieved, processing_time_ms, error_message
        )

    def get_api_calls(
        self,
        candidate_name: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get API call history with filters."""
        return self._api_calls.get_api_calls(candidate_name, location, limit, offset)

    def get_api_call_with_data(self, api_call_id: str) -> Optional[Dict[str, Any]]:
        """Get full API call with all related data."""
        return self._api_calls.get_api_call_with_data(api_call_id)

    # =========================================================================
    # Tweet operations (delegated to TweetRepository)
    # =========================================================================

    def save_tweets(self, api_call_id: str, tweets_data: List[Dict[str, Any]]) -> int:
        """Save multiple tweets to database. Returns count of tweets saved."""
        return self._tweets.save_tweets(api_call_id, tweets_data)

    def get_tweets_by_api_call(
        self,
        api_call_id: str,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tweets for a specific API call."""
        return self._tweets.get_tweets_by_api_call(api_call_id, limit, offset)

    # =========================================================================
    # Snapshot operations (delegated to SnapshotRepository)
    # =========================================================================

    def save_analysis_snapshot(self, api_call_id: str, snapshot_data: Dict[str, Any]) -> Optional[str]:
        """Save analysis snapshot (aggregated metrics)."""
        return self._snapshots.save_analysis_snapshot(api_call_id, snapshot_data)

    def save_pnd_metrics(self, api_call_id: str, pnd_metrics: List[Dict[str, Any]]) -> int:
        """Save PND axis metrics. Returns count saved."""
        return self._snapshots.save_pnd_metrics(api_call_id, pnd_metrics)

    def save_forecast_snapshot(self, api_call_id: str, forecast_data: Dict[str, Any]) -> Optional[str]:
        """Save forecast snapshot."""
        return self._snapshots.save_forecast_snapshot(api_call_id, forecast_data)

    def save_campaign_strategy(self, api_call_id: str, strategy_data: Dict[str, Any]) -> Optional[str]:
        """Save campaign strategy."""
        return self._snapshots.save_campaign_strategy(api_call_id, strategy_data)
