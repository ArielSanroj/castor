"""
Forecast Service - Implements ICCE, MEC, and time series forecasting models.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from collections import defaultdict

from app.schemas.forecast import (
    ICCEValue,
    MomentumValue,
    ForecastPoint,
    ScenarioSimulation,
)

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Service for electoral conversation forecasting.
    Implements ICCE, Momentum, and time series projections.
    """

    def __init__(self, twitter_service, sentiment_service, db_service=None):
        self.twitter_service = twitter_service
        self.sentiment_service = sentiment_service
        self.db_service = db_service

    def calculate_icce(
        self,
        location: str,
        candidate_name: Optional[str] = None,
        politician: Optional[str] = None,
        days_back: int = 30,
    ) -> List[ICCEValue]:
        """
        Calculate Índice Compuesto de Conversación Electoral (ICCE) for historical period.
        
        ICCE = (Volume_Normalized * 0.4) + (Sentiment_Score * 0.4) + (Conversation_Share * 0.2)
        
        Returns:
            List of ICCE values per day
        """
        try:
            # Get historical tweets
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Group tweets by day
            daily_data = defaultdict(lambda: {
                'tweets': [],
                'total_volume': 0,
                'sentiment_sum': 0.0,
                'count': 0
            })
            
            # Fetch tweets (simplified - in production would fetch historical data)
            tweets = self.twitter_service.search_by_pnd_topic(
                topic=None,
                location=location,
                candidate_name=candidate_name,
                politician=politician,
                max_results=min(days_back * 10, 300),  # Limit for performance
            )
            
            # Process tweets and group by day
            for tweet in tweets:
                tweet_date = tweet.get('created_at', datetime.utcnow())
                if isinstance(tweet_date, str):
                    try:
                        tweet_date = datetime.fromisoformat(tweet_date.replace('Z', '+00:00'))
                    except:
                        tweet_date = datetime.utcnow()
                
                day_key = tweet_date.date()
                text = tweet.get('text', '')
                
                # Analyze sentiment
                sentiment = self.sentiment_service.analyze_sentiment(text)
                net_sentiment = sentiment.positive - sentiment.negative  # -1 to 1
                
                daily_data[day_key]['tweets'].append(tweet)
                daily_data[day_key]['count'] += 1
                daily_data[day_key]['sentiment_sum'] += net_sentiment
            
            # Calculate ICCE for each day
            icce_values = []
            max_volume = max((d['count'] for d in daily_data.values()), default=1)
            
            for day, data in sorted(daily_data.items()):
                volume_normalized = (data['count'] / max_volume) * 100 if max_volume > 0 else 0
                avg_sentiment = data['sentiment_sum'] / data['count'] if data['count'] > 0 else 0
                sentiment_score = (avg_sentiment + 1) * 50  # Convert -1,1 to 0,100
                
                # Conversation share (simplified - would compare with total conversation)
                conversation_share = min(data['count'] / 10.0, 1.0) * 100  # Normalized
                
                # Calculate ICCE
                icce = (
                    volume_normalized * 0.4 +
                    sentiment_score * 0.4 +
                    conversation_share * 0.2
                )
                
                icce_values.append(ICCEValue(
                    date=datetime.combine(day, datetime.min.time()),
                    value=icce,
                    volume=data['count'],
                    sentiment_score=avg_sentiment,
                    conversation_share=conversation_share / 100.0
                ))
            
            # Fill missing days with interpolated values
            if icce_values:
                filled_values = self._fill_missing_days(icce_values, start_date, end_date)
                return filled_values
            
            return []
            
        except Exception as e:
            logger.error(f"Error calculating ICCE: {e}", exc_info=True)
            return []

    def calculate_momentum(
        self,
        icce_values: List[ICCEValue],
        window: int = 7
    ) -> List[MomentumValue]:
        """
        Calculate Momentum Electoral de Conversación (MEC) from ICCE values.
        
        Momentum = Moving average difference + rate of change
        
        Args:
            icce_values: Historical ICCE values
            window: Moving average window in days
            
        Returns:
            List of momentum values
        """
        if len(icce_values) < window + 1:
            return []
        
        momentum_values = []
        
        for i in range(window, len(icce_values)):
            # Calculate moving averages
            recent_avg = np.mean([v.value for v in icce_values[i-window:i]])
            previous_avg = np.mean([v.value for v in icce_values[i-window-1:i-1]]) if i > window else recent_avg
            
            # Momentum = change in moving average
            momentum = recent_avg - previous_avg
            
            # Rate of change
            current_value = icce_values[i].value
            previous_value = icce_values[i-1].value if i > 0 else current_value
            change = current_value - previous_value
            
            # Determine trend
            if momentum > 2:
                trend = "up"
            elif momentum < -2:
                trend = "down"
            else:
                trend = "stable"
            
            momentum_values.append(MomentumValue(
                date=icce_values[i].date,
                momentum=momentum,
                change=change,
                trend=trend
            ))
        
        return momentum_values

    def forecast_icce(
        self,
        icce_values: List[ICCEValue],
        forecast_days: int = 14,
        model_type: str = "holt_winters"
    ) -> List[ForecastPoint]:
        """
        Forecast ICCE values using time series models.
        
        Args:
            icce_values: Historical ICCE values
            forecast_days: Number of days to forecast
            model_type: 'holt_winters', 'prophet', or 'arima'
            
        Returns:
            List of forecast points with confidence intervals
        """
        if len(icce_values) < 7:
            return []
        
        try:
            # Extract time series
            values = [v.value for v in icce_values]
            dates = [v.date for v in icce_values]
            
            if model_type == "holt_winters":
                return self._holt_winters_forecast(values, dates, forecast_days)
            elif model_type == "simple_trend":
                return self._simple_trend_forecast(values, dates, forecast_days)
            else:
                # Default to simple trend
                return self._simple_trend_forecast(values, dates, forecast_days)
                
        except Exception as e:
            logger.error(f"Error forecasting ICCE: {e}", exc_info=True)
            return []

    def simulate_scenario(
        self,
        baseline_icce: float,
        scenario_type: str,
        sentiment_shift: float = 0.0
    ) -> ScenarioSimulation:
        """
        Simulate impact of a scenario on ICCE.
        
        Args:
            baseline_icce: Current ICCE value
            scenario_type: Type of scenario
            sentiment_shift: Expected sentiment change (-1 to 1)
            
        Returns:
            Scenario simulation result
        """
        # Impact multipliers by scenario type
        multipliers = {
            "announcement": 0.15,
            "debate": 0.25,
            "crisis": -0.30,
            "positive_news": 0.20,
        }
        
        multiplier = multipliers.get(scenario_type, 0.10)
        
        # Calculate impact
        sentiment_impact = sentiment_shift * 40  # Convert sentiment to ICCE points
        scenario_impact = baseline_icce * multiplier
        
        total_impact = sentiment_impact + scenario_impact
        simulated_icce = max(0, min(100, baseline_icce + total_impact))
        
        return ScenarioSimulation(
            scenario_name=scenario_type,
            baseline_icce=baseline_icce,
            simulated_icce=simulated_icce,
            impact=total_impact,
            impact_percentage=(total_impact / baseline_icce * 100) if baseline_icce > 0 else 0
        )

    def _fill_missing_days(
        self,
        icce_values: List[ICCEValue],
        start_date: datetime,
        end_date: datetime
    ) -> List[ICCEValue]:
        """Fill missing days with interpolated values."""
        if not icce_values:
            return []
        
        # Create date range
        current_date = start_date.date()
        end_date_only = end_date.date()
        filled = []
        value_dict = {v.date.date(): v for v in icce_values}
        
        while current_date <= end_date_only:
            if current_date in value_dict:
                filled.append(value_dict[current_date])
            else:
                # Interpolate from nearest values
                nearest = self._find_nearest_value(current_date, icce_values)
                if nearest:
                    filled.append(ICCEValue(
                        date=datetime.combine(current_date, datetime.min.time()),
                        value=nearest.value * 0.8,  # Slight decay for missing days
                        volume=max(0, nearest.volume - 1),
                        sentiment_score=nearest.sentiment_score,
                        conversation_share=nearest.conversation_share * 0.9
                    ))
            current_date += timedelta(days=1)
        
        return filled

    def _find_nearest_value(self, target_date, icce_values: List[ICCEValue]) -> Optional[ICCEValue]:
        """Find nearest ICCE value to target date."""
        if not icce_values:
            return None
        
        target = target_date
        nearest = None
        min_diff = float('inf')
        
        for value in icce_values:
            diff = abs((value.date.date() - target).days)
            if diff < min_diff:
                min_diff = diff
                nearest = value
        
        return nearest

    def _holt_winters_forecast(
        self,
        values: List[float],
        dates: List[datetime],
        forecast_days: int
    ) -> List[ForecastPoint]:
        """Simple Holt-Winters-like forecast."""
        if len(values) < 3:
            return []
        
        # Calculate trend
        recent_values = values[-7:] if len(values) >= 7 else values
        trend = np.mean(np.diff(recent_values)) if len(recent_values) > 1 else 0
        
        # Calculate level (recent average)
        level = np.mean(recent_values)
        
        # Generate forecast
        forecast_points = []
        last_date = dates[-1]
        
        for i in range(1, forecast_days + 1):
            forecast_date = last_date + timedelta(days=i)
            projected = level + (trend * i)
            
            # Confidence interval (wider as we go further)
            std_dev = np.std(recent_values) if len(recent_values) > 1 else 5.0
            margin = std_dev * (1 + i * 0.1)  # Increasing uncertainty
            
            forecast_points.append(ForecastPoint(
                date=forecast_date,
                projected_value=max(0, min(100, projected)),
                lower_bound=max(0, min(100, projected - margin)),
                upper_bound=max(0, min(100, projected + margin)),
                confidence=max(0.5, 1.0 - (i * 0.02))  # Decreasing confidence
            ))
        
        return forecast_points

    def _simple_trend_forecast(
        self,
        values: List[float],
        dates: List[datetime],
        forecast_days: int
    ) -> List[ForecastPoint]:
        """Simple linear trend forecast."""
        if len(values) < 2:
            return []
        
        # Linear regression on recent values
        recent_n = min(14, len(values))
        recent_values = values[-recent_n:]
        recent_indices = list(range(len(recent_values)))
        
        # Simple linear fit
        x_mean = np.mean(recent_indices)
        y_mean = np.mean(recent_values)
        
        numerator = sum((recent_indices[i] - x_mean) * (recent_values[i] - y_mean) for i in range(len(recent_values)))
        denominator = sum((i - x_mean) ** 2 for i in recent_indices)
        
        slope = numerator / denominator if denominator > 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Generate forecast
        forecast_points = []
        last_date = dates[-1]
        last_value = values[-1]
        
        for i in range(1, forecast_days + 1):
            forecast_date = last_date + timedelta(days=i)
            projected = intercept + slope * (recent_n + i - 1)
            
            # Confidence interval
            std_dev = np.std(recent_values) if len(recent_values) > 1 else 5.0
            margin = std_dev * (1 + i * 0.15)
            
            forecast_points.append(ForecastPoint(
                date=forecast_date,
                projected_value=max(0, min(100, projected)),
                lower_bound=max(0, min(100, projected - margin)),
                upper_bound=max(0, min(100, projected + margin)),
                confidence=max(0.4, 1.0 - (i * 0.03))
            ))
        
        return forecast_points

