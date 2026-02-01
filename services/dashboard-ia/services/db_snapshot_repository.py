"""
Snapshot repository for database operations.
Handles analysis snapshots, PND metrics, forecasts, and campaign strategies.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from models.database import AnalysisSnapshot, PndAxisMetric, ForecastSnapshot, CampaignStrategy

logger = logging.getLogger(__name__)


class SnapshotRepository:
    """Repository for snapshot database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    def save_analysis_snapshot(
        self,
        api_call_id: str,
        snapshot_data: Dict[str, Any]
    ) -> Optional[str]:
        """Save analysis snapshot (aggregated metrics)."""
        session = self._db.get_session()
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
        session = self._db.get_session()
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
        session = self._db.get_session()
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
        session = self._db.get_session()
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
