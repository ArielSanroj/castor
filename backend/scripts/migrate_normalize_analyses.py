#!/usr/bin/env python3
"""
Migration script: Normalize analyses data from JSON to relational tables.

This script:
1. Creates new normalized tables (analysis_topics, analysis_recommendations, etc.)
2. Migrates existing analysis_data JSON to normalized structure
3. Updates user_metrics with aggregated data

Run with: python scripts/migrate_normalize_analyses.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import Config
from models.database import (
    Base, Analysis, AnalysisTopic, AnalysisRecommendation,
    AnalysisSpeech, UserMetrics, User
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_analyses(session):
    """Migrate analysis_data JSON to normalized tables."""
    analyses = session.query(Analysis).all()
    logger.info(f"Found {len(analyses)} analyses to migrate")

    migrated = 0
    for analysis in analyses:
        try:
            data = analysis.analysis_data or {}

            # 1. Update normalized sentiment fields on Analysis
            sentiment = data.get('sentiment_overview', {})
            if sentiment:
                analysis.sentiment_positive = sentiment.get('positive', 0.0)
                analysis.sentiment_negative = sentiment.get('negative', 0.0)
                analysis.sentiment_neutral = sentiment.get('neutral', 0.0)

            metadata = data.get('metadata', {})
            analysis.tweets_analyzed = metadata.get('tweets_analyzed', 0)
            analysis.trending_topic = metadata.get('trending_topic') or data.get('trending_topic')

            # 2. Migrate topics
            topics = data.get('topics', data.get('topic_analyses', []))
            for topic_data in topics:
                if isinstance(topic_data, dict):
                    topic_sentiment = topic_data.get('sentiment', {})
                    topic = AnalysisTopic(
                        analysis_id=analysis.id,
                        topic_name=topic_data.get('topic', 'General'),
                        sentiment_positive=topic_sentiment.get('positive', 0.0),
                        sentiment_negative=topic_sentiment.get('negative', 0.0),
                        sentiment_neutral=topic_sentiment.get('neutral', 0.0),
                        tweet_count=topic_data.get('tweet_count', 0),
                        key_insights=topic_data.get('key_insights', []),
                        sample_tweets=topic_data.get('sample_tweets', [])
                    )
                    session.add(topic)

            # 3. Migrate recommendations
            exec_summary = data.get('executive_summary', {})

            # Key findings as 'finding' type
            for finding in exec_summary.get('key_findings', []):
                rec = AnalysisRecommendation(
                    analysis_id=analysis.id,
                    recommendation_type='finding',
                    priority='media',
                    content=finding
                )
                session.add(rec)

            # Recommendations as 'recommendation' type
            for rec_text in exec_summary.get('recommendations', []):
                rec = AnalysisRecommendation(
                    analysis_id=analysis.id,
                    recommendation_type='recommendation',
                    priority='alta',
                    content=rec_text
                )
                session.add(rec)

            # Strategic actions
            plan = data.get('strategic_plan', {})
            for action in plan.get('actions', []):
                if isinstance(action, dict):
                    rec = AnalysisRecommendation(
                        analysis_id=analysis.id,
                        recommendation_type='action',
                        priority=action.get('priority', 'media'),
                        content=action.get('action', str(action)),
                        topic_related=action.get('topic')
                    )
                    session.add(rec)

            # 4. Migrate speech
            speech_data = data.get('speech', {})
            if speech_data and speech_data.get('content'):
                speech = AnalysisSpeech(
                    analysis_id=analysis.id,
                    title=speech_data.get('title', f'Discurso para {analysis.location}'),
                    content=speech_data.get('content', ''),
                    key_points=speech_data.get('key_points', []),
                    duration_minutes=speech_data.get('duration_minutes', 7)
                )
                session.add(speech)

            migrated += 1

        except Exception as e:
            logger.error(f"Error migrating analysis {analysis.id}: {e}")

    session.commit()
    logger.info(f"Migrated {migrated} analyses")
    return migrated


def update_user_metrics(session):
    """Calculate and update user metrics."""
    users = session.query(User).all()
    logger.info(f"Updating metrics for {len(users)} users")

    for user in users:
        try:
            analyses = session.query(Analysis).filter(Analysis.user_id == user.id).all()

            if not analyses:
                continue

            # Calculate aggregates
            total = len(analyses)
            avg_pos = sum(a.sentiment_positive or 0 for a in analyses) / total if total else 0
            avg_neg = sum(a.sentiment_negative or 0 for a in analyses) / total if total else 0

            # Most common location
            locations = [a.location for a in analyses if a.location]
            most_location = max(set(locations), key=locations.count) if locations else None

            # Most common topic
            topics = session.query(AnalysisTopic).join(Analysis).filter(Analysis.user_id == user.id).all()
            topic_names = [t.topic_name for t in topics]
            most_topic = max(set(topic_names), key=topic_names.count) if topic_names else None

            # Last analysis
            last_analysis = max(analyses, key=lambda a: a.created_at or datetime.min.replace(tzinfo=timezone.utc))

            # Upsert metrics
            metrics = session.query(UserMetrics).filter(UserMetrics.user_id == user.id).first()
            if not metrics:
                metrics = UserMetrics(user_id=user.id)
                session.add(metrics)

            metrics.total_analyses = total
            metrics.total_topics_analyzed = len(topics)
            metrics.avg_sentiment_positive = avg_pos
            metrics.avg_sentiment_negative = avg_neg
            metrics.most_analyzed_location = most_location
            metrics.most_analyzed_topic = most_topic
            metrics.last_analysis_at = last_analysis.created_at

        except Exception as e:
            logger.error(f"Error updating metrics for user {user.id}: {e}")

    session.commit()
    logger.info("User metrics updated")


def main():
    """Run migration."""
    logger.info("Starting database normalization migration...")

    # Create engine
    engine = create_engine(Config.DATABASE_URL)

    # Create new tables
    logger.info("Creating new tables...")
    Base.metadata.create_all(bind=engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Run migrations
        migrate_analyses(session)
        update_user_metrics(session)

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
