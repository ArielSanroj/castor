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
        alpha: float = 0.5
    ) -> List[ICCEValue]:
        """
        Calculate Índice Compuesto de Conversación Electoral (ICCE) according to theoretical model.
        
        Model:
        - ISN (Índice de Sentimiento Neto) = P - N  (range: [-1, 1])
        - ISN' (normalized) = (ISN + 1) / 2  (range: [0, 1])
        - ICR (Índice de Conversación Relativa) = V_c / V_total  (range: [0, 1])
        - ICCE = α * ISN' + (1-α) * ICR  (default α=0.5)
        
        Args:
            location: Location filter
            candidate_name: Optional candidate name filter
            politician: Optional Twitter handle filter
            days_back: Number of days to look back
            alpha: Weight for ISN' in ICCE calculation (default 0.5)
        
        Returns:
            List of ICCE values per day with ISN, ICR, and ICCE
        """
        try:
            # Get historical tweets
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Group tweets by day for candidate
            daily_candidate_data = defaultdict(lambda: {
                'tweets': [],
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_count': 0,
                'sentiment_sum': 0.0
            })
            
            # Group tweets by day for TOTAL conversation (all candidates)
            daily_total_data = defaultdict(lambda: {'total_count': 0})
            
            # Fetch tweets for candidate
            candidate_tweets = self.twitter_service.search_by_pnd_topic(
                topic=None,
                location=location,
                candidate_name=candidate_name,
                politician=politician,
                max_results=min(days_back * 10, 300),
            )
            
            # Fetch tweets for TOTAL conversation (without candidate filter)
            total_tweets = self.twitter_service.search_by_pnd_topic(
                topic=None,
                location=location,
                candidate_name=None,
                politician=None,
                max_results=min(days_back * 20, 500),  # More tweets for total
            )
            
            # Process candidate tweets
            for tweet in candidate_tweets:
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
                
                # Count by sentiment
                if sentiment.positive > sentiment.negative:
                    daily_candidate_data[day_key]['positive_count'] += 1
                elif sentiment.negative > sentiment.positive:
                    daily_candidate_data[day_key]['negative_count'] += 1
                else:
                    daily_candidate_data[day_key]['neutral_count'] += 1
                
                # Calculate net sentiment
                net_sentiment = sentiment.positive - sentiment.negative  # -1 to 1
                
                daily_candidate_data[day_key]['tweets'].append(tweet)
                daily_candidate_data[day_key]['total_count'] += 1
                daily_candidate_data[day_key]['sentiment_sum'] += net_sentiment
            
            # Process total tweets (for ICR calculation)
            for tweet in total_tweets:
                tweet_date = tweet.get('created_at', datetime.utcnow())
                if isinstance(tweet_date, str):
                    try:
                        tweet_date = datetime.fromisoformat(tweet_date.replace('Z', '+00:00'))
                    except:
                        tweet_date = datetime.utcnow()
                
                day_key = tweet_date.date()
                daily_total_data[day_key]['total_count'] += 1
            
            # Calculate ICCE for each day according to theoretical model
            icce_values = []
            
            for day in sorted(set(list(daily_candidate_data.keys()) + list(daily_total_data.keys()))):
                candidate_data = daily_candidate_data.get(day, {
                    'total_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0,
                    'sentiment_sum': 0.0
                })
                total_data = daily_total_data.get(day, {'total_count': 1})  # Avoid division by zero
                
                V_c = candidate_data['total_count']
                V_total = max(total_data['total_count'], V_c)  # Ensure V_total >= V_c
                
                # Calculate ISN (Índice de Sentimiento Neto)
                if V_c > 0:
                    P_c = candidate_data['positive_count'] / V_c
                    N_c = candidate_data['negative_count'] / V_c
                    ISN = P_c - N_c  # Range: [-1, 1]
                else:
                    ISN = 0.0
                
                # Normalize ISN to [0, 1]
                ISN_normalized = (ISN + 1) / 2  # Range: [0, 1]
                
                # Calculate ICR (Índice de Conversación Relativa)
                ICR = V_c / V_total if V_total > 0 else 0.0  # Range: [0, 1]
                
                # Calculate ICCE according to theoretical model
                # ICCE = α * ISN' + (1-α) * ICR
                ICCE = alpha * ISN_normalized + (1 - alpha) * ICR
                
                # Convert to 0-100 scale for compatibility
                ICCE_scaled = ICCE * 100
                
                # Average sentiment score for metadata
                avg_sentiment = candidate_data['sentiment_sum'] / V_c if V_c > 0 else 0.0
                
                icce_values.append(ICCEValue(
                    date=datetime.combine(day, datetime.min.time()),
                    value=ICCE_scaled,  # Store as 0-100 for compatibility
                    volume=V_c,
                    sentiment_score=ISN,  # Store raw ISN [-1, 1]
                    conversation_share=ICR  # Store ICR [0, 1]
                ))
            
            # Fill missing days with interpolated values
            if icce_values:
                filled_values = self._fill_missing_days(icce_values, start_date, end_date)
                return filled_values
            
            return []
            
        except Exception as e:
            logger.error(f"Error calculating ICCE: {e}", exc_info=True)
            return []

    def calculate_ema_smooth(
        self,
        icce_values: List[ICCEValue],
        lambda_param: float = 0.3
    ) -> List[float]:
        """
        Calculate Exponential Moving Average (EMA) smoothing for ICCE values.
        
        EMA formula: S_t = λ * ICCE_t + (1-λ) * S_{t-1}
        
        Args:
            icce_values: Historical ICCE values
            lambda_param: Smoothing parameter (default 0.3)
            
        Returns:
            List of smoothed ICCE values
        """
        if not icce_values:
            return []
        
        smoothed = []
        values = [v.value / 100.0 for v in icce_values]  # Convert to [0,1] scale
        
        # Initialize first value
        smoothed.append(values[0])
        
        # Calculate EMA for remaining values
        for i in range(1, len(values)):
            ema_value = lambda_param * values[i] + (1 - lambda_param) * smoothed[i-1]
            smoothed.append(ema_value)
        
        return smoothed

    def calculate_momentum(
        self,
        icce_values: List[ICCEValue],
        lambda_param: float = 0.3
    ) -> List[MomentumValue]:
        """
        Calculate Momentum Electoral de Conversación (MEC) using EMA smoothing.
        
        Model:
        - EMA smoothing: S_t = λ * ICCE_t + (1-λ) * S_{t-1}
        - Momentum: MEC_t = S_t - S_{t-1}
        
        Args:
            icce_values: Historical ICCE values
            lambda_param: EMA smoothing parameter (default 0.3)
            
        Returns:
            List of momentum values
        """
        if len(icce_values) < 2:
            return []
        
        # Calculate EMA smoothed values
        smoothed_values = self.calculate_ema_smooth(icce_values, lambda_param)
        
        momentum_values = []
        
        # Calculate momentum as difference of EMA
        for i in range(1, len(icce_values)):
            momentum = smoothed_values[i] - smoothed_values[i-1]
            
            # Also calculate raw change for reference
            current_value = icce_values[i].value / 100.0  # Convert to [0,1]
            previous_value = icce_values[i-1].value / 100.0
            change = current_value - previous_value
            
            # Determine trend based on momentum
            if momentum > 0.01:  # Threshold for "up"
                trend = "up"
            elif momentum < -0.01:  # Threshold for "down"
                trend = "stable"
            else:
                trend = "stable"
            
            momentum_values.append(MomentumValue(
                date=icce_values[i].date,
                momentum=momentum,  # Keep in [0,1] scale for consistency
                change=change,
                trend=trend
            ))
        
        return momentum_values

    def forecast_icce(
        self,
        icce_values: List[ICCEValue],
        forecast_days: int = 14,
        model_type: str = "holt_winters",
        use_smoothed: bool = True,
        lambda_param: float = 0.3
    ) -> List[ForecastPoint]:
        """
        Forecast ICCE values using time series models.
        
        By default, forecasts on EMA-smoothed values for better trend detection.
        
        Args:
            icce_values: Historical ICCE values
            forecast_days: Number of days to forecast
            model_type: 'holt_winters', 'prophet', or 'simple_trend'
            use_smoothed: If True, forecast on EMA-smoothed values (default True)
            lambda_param: EMA smoothing parameter if use_smoothed=True
            
        Returns:
            List of forecast points with confidence intervals
        """
        if len(icce_values) < 7:
            return []
        
        try:
            # Use smoothed values for forecasting (better trend detection)
            if use_smoothed:
                smoothed_values = self.calculate_ema_smooth(icce_values, lambda_param)
                # Convert back to 0-100 scale for forecasting
                values = [v * 100.0 for v in smoothed_values]
            else:
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

