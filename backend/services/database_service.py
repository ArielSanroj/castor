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
    CampaignAction, VoteStrategy, Lead,
    # Nuevos modelos para almacenamiento completo
    ApiCall, Tweet, AnalysisSnapshot, PndAxisMetric, ForecastSnapshot, CampaignStrategy
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations using SQLAlchemy."""
    
    def __init__(self):
        """Initialize database connection."""
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")

        # SQLite doesn't support pool options
        if Config.DATABASE_URL.startswith("sqlite"):
            self.engine = create_engine(
                Config.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
            logger.info("DatabaseService initialized with SQLite")
        else:
            self.engine = create_engine(
                Config.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=Config.DB_POOL_SIZE,
                max_overflow=Config.DB_MAX_OVERFLOW,
                pool_timeout=Config.DB_POOL_TIMEOUT
            )
            logger.info(f"DatabaseService initialized (pool_size={Config.DB_POOL_SIZE})")

        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
    
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

    # =========================================================================
    # API Calls and Tweet Storage Operations
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
        session = self.get_session()
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
        session = self.get_session()
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

    def save_tweets(self, api_call_id: str, tweets_data: List[Dict[str, Any]]) -> int:
        """
        Save multiple tweets to database.
        Returns count of tweets saved.
        """
        session = self.get_session()
        saved_count = 0
        try:
            for tweet_data in tweets_data:
                tweet = Tweet(
                    api_call_id=api_call_id,
                    tweet_id=tweet_data.get('tweet_id', ''),
                    author_id=tweet_data.get('author_id'),
                    author_username=tweet_data.get('author_username'),
                    author_name=tweet_data.get('author_name'),
                    author_verified=tweet_data.get('author_verified', False),
                    author_followers_count=tweet_data.get('author_followers_count', 0),
                    content=tweet_data.get('content', ''),
                    content_cleaned=tweet_data.get('content_cleaned'),
                    tweet_created_at=tweet_data.get('tweet_created_at'),
                    language=tweet_data.get('language'),
                    source=tweet_data.get('source'),
                    retweet_count=tweet_data.get('retweet_count', 0),
                    like_count=tweet_data.get('like_count', 0),
                    reply_count=tweet_data.get('reply_count', 0),
                    quote_count=tweet_data.get('quote_count', 0),
                    impression_count=tweet_data.get('impression_count', 0),
                    is_retweet=tweet_data.get('is_retweet', False),
                    is_reply=tweet_data.get('is_reply', False),
                    is_quote=tweet_data.get('is_quote', False),
                    replied_to_tweet_id=tweet_data.get('replied_to_tweet_id'),
                    quoted_tweet_id=tweet_data.get('quoted_tweet_id'),
                    hashtags=tweet_data.get('hashtags', []),
                    mentions=tweet_data.get('mentions', []),
                    urls=tweet_data.get('urls', []),
                    geo_country=tweet_data.get('geo_country'),
                    geo_city=tweet_data.get('geo_city'),
                    geo_coordinates=tweet_data.get('geo_coordinates'),
                    sentiment_positive=tweet_data.get('sentiment_positive', 0.0),
                    sentiment_negative=tweet_data.get('sentiment_negative', 0.0),
                    sentiment_neutral=tweet_data.get('sentiment_neutral', 0.0),
                    sentiment_label=tweet_data.get('sentiment_label'),
                    sentiment_confidence=tweet_data.get('sentiment_confidence', 0.0),
                    pnd_topic=tweet_data.get('pnd_topic'),
                    pnd_confidence=tweet_data.get('pnd_confidence', 0.0),
                    pnd_secondary_topic=tweet_data.get('pnd_secondary_topic'),
                    is_potential_bot=tweet_data.get('is_potential_bot', False),
                    bot_score=tweet_data.get('bot_score', 0.0)
                )
                session.add(tweet)
                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} tweets for API call {api_call_id}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving tweets: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def save_analysis_snapshot(
        self,
        api_call_id: str,
        snapshot_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save analysis snapshot (aggregated metrics)."""
        session = self.get_session()
        try:
            snapshot = AnalysisSnapshot(
                api_call_id=api_call_id,
                icce=snapshot_data.get('icce', 0.0),
                sov=snapshot_data.get('sov', 0.0),
                sna=snapshot_data.get('sna', 0.0),
                momentum=snapshot_data.get('momentum', 0.0),
                sentiment_positive=snapshot_data.get('sentiment_positive', 0.0),
                sentiment_negative=snapshot_data.get('sentiment_negative', 0.0),
                sentiment_neutral=snapshot_data.get('sentiment_neutral', 0.0),
                executive_summary=snapshot_data.get('executive_summary'),
                key_findings=snapshot_data.get('key_findings', []),
                key_stats=snapshot_data.get('key_stats', []),
                recommendations=snapshot_data.get('recommendations', []),
                trending_topics=snapshot_data.get('trending_topics', []),
                geo_distribution=snapshot_data.get('geo_distribution', []),
                opportunity=snapshot_data.get('opportunity'),
                risk_level=snapshot_data.get('risk_level'),
                risk_description=snapshot_data.get('risk_description')
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            logger.info(f"Analysis snapshot saved: {snapshot.id}")
            return snapshot.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving analysis snapshot: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def save_pnd_metrics(
        self,
        api_call_id: str,
        pnd_metrics: List[Dict[str, Any]]
    ) -> int:
        """Save PND axis metrics. Returns count saved."""
        session = self.get_session()
        saved_count = 0
        try:
            for metric_data in pnd_metrics:
                metric = PndAxisMetric(
                    api_call_id=api_call_id,
                    pnd_axis=metric_data.get('pnd_axis', ''),
                    pnd_axis_display=metric_data.get('pnd_axis_display'),
                    icce=metric_data.get('icce', 0.0),
                    sov=metric_data.get('sov', 0.0),
                    sna=metric_data.get('sna', 0.0),
                    tweet_count=metric_data.get('tweet_count', 0),
                    trend=metric_data.get('trend'),
                    trend_change=metric_data.get('trend_change', 0.0),
                    sentiment_positive=metric_data.get('sentiment_positive', 0.0),
                    sentiment_negative=metric_data.get('sentiment_negative', 0.0),
                    sentiment_neutral=metric_data.get('sentiment_neutral', 0.0),
                    key_insights=metric_data.get('key_insights', []),
                    sample_tweets=metric_data.get('sample_tweets', [])
                )
                session.add(metric)
                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} PND metrics for API call {api_call_id}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving PND metrics: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def save_forecast_snapshot(
        self,
        api_call_id: str,
        forecast_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save forecast snapshot."""
        session = self.get_session()
        try:
            forecast = ForecastSnapshot(
                api_call_id=api_call_id,
                historical_dates=forecast_data.get('historical_dates', []),
                icce_values=forecast_data.get('icce_values', []),
                icce_smooth=forecast_data.get('icce_smooth', []),
                momentum_values=forecast_data.get('momentum_values', []),
                forecast_dates=forecast_data.get('forecast_dates', []),
                icce_pred=forecast_data.get('icce_pred', []),
                pred_low=forecast_data.get('pred_low', []),
                pred_high=forecast_data.get('pred_high', []),
                model_type=forecast_data.get('model_type', 'holt_winters'),
                model_confidence=forecast_data.get('model_confidence', 0.0),
                days_back=forecast_data.get('days_back', 30),
                forecast_days=forecast_data.get('forecast_days', 14),
                icce_current=forecast_data.get('icce_current', 0.0),
                icce_predicted_end=forecast_data.get('icce_predicted_end', 0.0),
                icce_change_predicted=forecast_data.get('icce_change_predicted', 0.0)
            )
            session.add(forecast)
            session.commit()
            session.refresh(forecast)
            logger.info(f"Forecast snapshot saved: {forecast.id}")
            return forecast.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving forecast snapshot: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def save_campaign_strategy(
        self,
        api_call_id: str,
        strategy_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save campaign strategy."""
        session = self.get_session()
        try:
            strategy = CampaignStrategy(
                api_call_id=api_call_id,
                executive_summary=strategy_data.get('executive_summary'),
                data_analysis=strategy_data.get('data_analysis'),
                strategic_plan=strategy_data.get('strategic_plan'),
                general_analysis=strategy_data.get('general_analysis'),
                speech=strategy_data.get('speech'),
                speech_title=strategy_data.get('speech_title'),
                speech_duration_minutes=strategy_data.get('speech_duration_minutes', 5),
                game_main_move=strategy_data.get('game_main_move'),
                game_alternatives=strategy_data.get('game_alternatives', []),
                game_rival_signal=strategy_data.get('game_rival_signal'),
                game_trigger=strategy_data.get('game_trigger'),
                game_payoff=strategy_data.get('game_payoff'),
                game_confidence=strategy_data.get('game_confidence'),
                rival_name=strategy_data.get('rival_name'),
                rival_comparison=strategy_data.get('rival_comparison'),
                gap_analysis=strategy_data.get('gap_analysis'),
                comparison_context=strategy_data.get('comparison_context'),
                ejes_scores=strategy_data.get('ejes_scores'),
                drivers=strategy_data.get('drivers', []),
                risks=strategy_data.get('risks', []),
                recommendations=strategy_data.get('recommendations', []),
                action_plan=strategy_data.get('action_plan', []),
                chart_suggestion=strategy_data.get('chart_suggestion')
            )
            session.add(strategy)
            session.commit()
            session.refresh(strategy)
            logger.info(f"Campaign strategy saved: {strategy.id}")
            return strategy.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving campaign strategy: {e}", exc_info=True)
            return None
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
        session = self.get_session()
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
        session = self.get_session()
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

    def get_tweets_by_api_call(
        self,
        api_call_id: str,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tweets for a specific API call."""
        session = self.get_session()
        try:
            tweets = (
                session.query(Tweet)
                .filter(Tweet.api_call_id == api_call_id)
                .order_by(Tweet.tweet_created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [
                {
                    'tweet_id': t.tweet_id,
                    'author_username': t.author_username,
                    'author_name': t.author_name,
                    'content': t.content,
                    'tweet_created_at': t.tweet_created_at.isoformat() if t.tweet_created_at else None,
                    'retweet_count': t.retweet_count,
                    'like_count': t.like_count,
                    'reply_count': t.reply_count,
                    'sentiment_label': t.sentiment_label,
                    'pnd_topic': t.pnd_topic
                }
                for t in tweets
            ]
        except Exception as e:
            logger.error(f"Error getting tweets: {e}", exc_info=True)
            return []
        finally:
            session.close()

