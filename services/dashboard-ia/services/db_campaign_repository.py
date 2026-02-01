"""
Campaign repository for database operations.
Handles trending topics, signatures, campaign actions, and vote strategies.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from models.database import TrendingTopic, Signature, CampaignAction, VoteStrategy

logger = logging.getLogger(__name__)


class CampaignRepository:
    """Repository for campaign-related database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    # Trending topics operations

    def save_trending_topic(self, topic_data: Dict[str, Any]) -> Optional[str]:
        """Save trending topic."""
        session = self._db.get_session()
        try:
            topic = TrendingTopic(**topic_data)
            session.add(topic)
            session.commit()
            session.refresh(topic)

            logger.info(f"Trending topic saved: {topic.id}")
            return str(topic.id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving trending topic: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_active_trending_topics(
        self,
        location: Optional[str] = None,
        limit: int = 10
    ) -> List[TrendingTopic]:
        """Get active trending topics."""
        session = self._db.get_session()
        try:
            query = session.query(TrendingTopic).filter(TrendingTopic.is_active == True)

            if location:
                query = query.filter(TrendingTopic.location == location)

            return query.order_by(TrendingTopic.engagement_score.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}", exc_info=True)
            return []
        finally:
            session.close()

    # Signature operations

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
        session = self._db.get_session()
        try:
            existing = (
                session.query(Signature)
                .filter(
                    Signature.campaign_id == campaign_id,
                    Signature.signer_email == signer_email
                )
                .first()
            )

            if existing:
                logger.warning(f"Email {signer_email} already signed campaign {campaign_id}")
                return None

            signature = Signature(
                user_id=user_id,
                campaign_id=campaign_id,
                signer_name=signer_name,
                signer_email=signer_email,
                signer_phone=signer_phone,
                signer_id_number=signer_id_number,
                location=location,
                ip_address=ip_address,
                user_agent=user_agent
            )

            session.add(signature)
            session.commit()
            session.refresh(signature)

            logger.info(f"Signature added: {signature.id}")
            return str(signature.id)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding signature: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_campaign_signatures(self, campaign_id: str) -> int:
        """Get count of signatures for a campaign."""
        session = self._db.get_session()
        try:
            return session.query(Signature).filter(Signature.campaign_id == campaign_id).count()
        except Exception as e:
            logger.error(f"Error getting signature count: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    # Campaign actions operations

    def save_campaign_action(self, action_data: Dict[str, Any]) -> Optional[str]:
        """Save campaign action."""
        session = self._db.get_session()
        try:
            action = CampaignAction(**action_data)
            session.add(action)
            session.commit()
            session.refresh(action)

            logger.info(f"Campaign action saved: {action.id}")
            return str(action.id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving campaign action: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_effective_strategies(self, user_id: str, limit: int = 5) -> List[CampaignAction]:
        """Get most effective campaign strategies."""
        session = self._db.get_session()
        try:
            return (
                session.query(CampaignAction)
                .filter(CampaignAction.user_id == user_id)
                .order_by(CampaignAction.roi.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting effective strategies: {e}", exc_info=True)
            return []
        finally:
            session.close()

    # Vote strategy operations

    def save_vote_strategy(self, strategy_data: Dict[str, Any]) -> Optional[str]:
        """Save vote-winning strategy."""
        session = self._db.get_session()
        try:
            strategy = VoteStrategy(**strategy_data)
            session.add(strategy)
            session.commit()
            session.refresh(strategy)

            logger.info(f"Vote strategy saved: {strategy.id}")
            return str(strategy.id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving vote strategy: {e}", exc_info=True)
            return None
        finally:
            session.close()
