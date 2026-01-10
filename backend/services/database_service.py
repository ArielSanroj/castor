"""
Database service using SQLAlchemy.
Replaces Supabase service.
"""
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models.database import (
    Base, User, Analysis, TrendingTopic, Speech, Signature,
    CampaignAction, VoteStrategy, Lead
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations using SQLAlchemy."""
    
    def __init__(self):
        """Initialize database connection."""
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")

        self.engine = create_engine(
            Config.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_timeout=Config.DB_POOL_TIMEOUT
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        logger.info(f"DatabaseService initialized (pool_size={Config.DB_POOL_SIZE})")
    
    def init_db(self):
        """Initialize database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            raise
    
    def get_session(self) -> Session:
        """Get database session (legacy - prefer session_scope for new code)."""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        Usage:
            with db_service.session_scope() as session:
                session.add(obj)
                # auto-commits on success, auto-rollbacks on exception
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # User operations
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
        session = self.get_session()
        try:
            # Check if user exists
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                logger.warning(f"User with email {email} already exists")
                return None
            
            # Create user
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                campaign_role=campaign_role,
                candidate_position=candidate_position,
                whatsapp_number=whatsapp_number,
                whatsapp_opt_in=whatsapp_opt_in
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"User created: {user.id}")
            return user
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user and return user if valid."""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.email == email).first()
            if user and check_password_hash(user.password_hash, password) and user.is_active:
                return user
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        session = self.get_session()
        try:
            return session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        session = self.get_session()
        try:
            return session.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    # Analysis operations
    def save_analysis(
        self,
        user_id: str,
        location: str,
        theme: str,
        candidate_name: Optional[str],
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save analysis to database."""
        session = self.get_session()
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
    
    def get_user_analyses(self, user_id: str, limit: int = 10, include_data: bool = False) -> List[Dict[str, Any]]:
        """Get user's analysis history."""
        session = self.get_session()
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
        session = self.get_session()
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
        session = self.get_session()
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
    
    # Trending topics operations
    def save_trending_topic(self, topic_data: Dict[str, Any]) -> Optional[str]:
        """Save trending topic."""
        session = self.get_session()
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
    
    def get_active_trending_topics(self, location: Optional[str] = None, limit: int = 10) -> List[TrendingTopic]:
        """Get active trending topics."""
        session = self.get_session()
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
        session = self.get_session()
        try:
            # Check if email already signed this campaign
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
        session = self.get_session()
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
        session = self.get_session()
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
        session = self.get_session()
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
        session = self.get_session()
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
    
    # Lead operations
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
        session = self.get_session()
        try:
            # Check if lead with email already exists
            existing_lead = session.query(Lead).filter(Lead.email == email).first()
            if existing_lead:
                logger.warning(f"Lead with email {email} already exists")
                return None
            
            # Create lead
            lead = Lead(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                interest=interest,
                location=location,
                candidacy_type=candidacy_type,
                status=status,
                notes=notes,
                extra_metadata=metadata or {}
            )
            
            session.add(lead)
            session.commit()
            session.refresh(lead)
            
            logger.info(f"Lead created: {lead.id} - {lead.email}")
            return lead
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating lead: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        session = self.get_session()
        try:
            return session.query(Lead).filter(Lead.id == lead_id).first()
        except Exception as e:
            logger.error(f"Error getting lead: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email."""
        session = self.get_session()
        try:
            return session.query(Lead).filter(Lead.email == email).first()
        except Exception as e:
            logger.error(f"Error getting lead by email: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def get_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Lead]:
        """Get leads with optional filters."""
        session = self.get_session()
        try:
            query = session.query(Lead)
            
            if status:
                query = query.filter(Lead.status == status)
            
            if candidacy_type:
                query = query.filter(Lead.candidacy_type == candidacy_type)
            
            return query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting leads: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def update_lead_status(self, lead_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update lead status."""
        session = self.get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                logger.warning(f"Lead {lead_id} not found")
                return False
            
            lead.status = status
            if notes:
                lead.notes = notes
            
            session.commit()
            logger.info(f"Lead {lead_id} status updated to {status}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating lead status: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def count_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None
    ) -> int:
        """Count leads with optional filters."""
        session = self.get_session()
        try:
            query = session.query(Lead)
            
            if status:
                query = query.filter(Lead.status == status)
            
            if candidacy_type:
                query = query.filter(Lead.candidacy_type == candidacy_type)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting leads: {e}", exc_info=True)
            return 0
        finally:
            session.close()

