"""
Twitter Rate Limit Tracker for Free Tier.
Tracks daily/monthly usage to avoid exceeding 100 posts/month limit.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TwitterRateTracker:
    """
    Tracks Twitter API usage for Free tier (100 posts/month).
    Stores usage data in a JSON file.
    """
    
    def __init__(self, storage_path: str = "/tmp/twitter_usage.json"):
        self.storage_path = Path(storage_path)
        self.monthly_limit = 100
        self.daily_limit = 3  # ~100/30 days
        
    def _load_usage(self) -> Dict[str, Any]:
        """Load usage data from file."""
        if not self.storage_path.exists():
            return {
                "daily": {},
                "monthly_total": 0,
                "month_start": datetime.utcnow().replace(day=1).isoformat()
            }
        
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")
            return {
                "daily": {},
                "monthly_total": 0,
                "month_start": datetime.utcnow().replace(day=1).isoformat()
            }
    
    def _save_usage(self, data: Dict[str, Any]):
        """Save usage data to file."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage data: {e}")
    
    def _get_today_key(self) -> str:
        """Get today's date key."""
        return datetime.utcnow().strftime("%Y-%m-%d")
    
    def _reset_if_new_month(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reset counters if it's a new month."""
        month_start = datetime.fromisoformat(data["month_start"])
        now = datetime.utcnow()
        
        if now.month != month_start.month or now.year != month_start.year:
            logger.info("New month detected, resetting Twitter usage counters")
            return {
                "daily": {},
                "monthly_total": 0,
                "month_start": now.replace(day=1).isoformat()
            }
        return data
    
    def can_make_request(self, tweet_count: int) -> tuple[bool, str]:
        """
        Check if we can make a request for the given number of tweets.
        
        Returns:
            (allowed, reason) - True if allowed, False with reason if not
        """
        data = self._load_usage()
        data = self._reset_if_new_month(data)
        
        today_key = self._get_today_key()
        today_usage = data["daily"].get(today_key, 0)
        monthly_usage = data["monthly_total"]
        
        # Check monthly limit
        if monthly_usage + tweet_count > self.monthly_limit:
            remaining = self.monthly_limit - monthly_usage
            return False, f"Monthly limit reached ({monthly_usage}/{self.monthly_limit}). Only {remaining} tweets remaining this month."
        
        # Check daily limit
        if today_usage + tweet_count > self.daily_limit:
            remaining = self.daily_limit - today_usage
            return False, f"Daily limit reached ({today_usage}/{self.daily_limit}). Only {remaining} tweets remaining today. Try again tomorrow."
        
        return True, "OK"
    
    def record_usage(self, tweet_count: int):
        """Record that we used N tweets."""
        data = self._load_usage()
        data = self._reset_if_new_month(data)
        
        today_key = self._get_today_key()
        data["daily"][today_key] = data["daily"].get(today_key, 0) + tweet_count
        data["monthly_total"] += tweet_count
        
        self._save_usage(data)
        
        logger.info(f"Twitter usage recorded: {tweet_count} tweets. Daily: {data['daily'][today_key]}/{self.daily_limit}, Monthly: {data['monthly_total']}/{self.monthly_limit}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        data = self._load_usage()
        data = self._reset_if_new_month(data)
        
        today_key = self._get_today_key()
        today_usage = data["daily"].get(today_key, 0)
        monthly_usage = data["monthly_total"]
        
        return {
            "today": {
                "used": today_usage,
                "limit": self.daily_limit,
                "remaining": self.daily_limit - today_usage,
                "percentage": (today_usage / self.daily_limit * 100) if self.daily_limit > 0 else 0
            },
            "month": {
                "used": monthly_usage,
                "limit": self.monthly_limit,
                "remaining": self.monthly_limit - monthly_usage,
                "percentage": (monthly_usage / self.monthly_limit * 100) if self.monthly_limit > 0 else 0
            },
            "month_start": data["month_start"]
        }


# Global instance
_tracker = TwitterRateTracker()


def can_make_twitter_request(tweet_count: int) -> tuple[bool, str]:
    """Check if a Twitter request can be made."""
    return _tracker.can_make_request(tweet_count)


def record_twitter_usage(tweet_count: int):
    """Record Twitter API usage."""
    _tracker.record_usage(tweet_count)


def get_twitter_usage_stats() -> Dict[str, Any]:
    """Get Twitter usage statistics."""
    return _tracker.get_usage_stats()
