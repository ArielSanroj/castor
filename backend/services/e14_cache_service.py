"""
E-14 Cache Service using Redis.

Caches aggregated E-14 data to reduce database/file system load.
Provides easy cache invalidation and TTL management.
"""
import json
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

import redis

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHE_TTL = int(os.environ.get('E14_CACHE_TTL', 3600))  # 1 hour default

# Cache keys
CACHE_PREFIX = 'e14:'
PARTY_SUMMARY_KEY = f'{CACHE_PREFIX}party_summary'
TOTALS_KEY = f'{CACHE_PREFIX}totals'
FORMS_KEY = f'{CACHE_PREFIX}forms'
METADATA_KEY = f'{CACHE_PREFIX}metadata'


class E14CacheService:
    """Redis-based cache for E-14 electoral data."""

    def __init__(self, redis_url: str = REDIS_URL, ttl: int = CACHE_TTL):
        """
        Initialize cache service.

        Args:
            redis_url: Redis connection URL
            ttl: Cache TTL in seconds (default 1 hour)
        """
        self.ttl = ttl
        self._redis: Optional[redis.Redis] = None
        self._redis_url = redis_url

    @property
    def redis(self) -> redis.Redis:
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise
        return self._redis

    def is_available(self) -> bool:
        """Check if Redis is available."""
        try:
            self.redis.ping()
            return True
        except Exception:
            return False

    # ========================================
    # CACHE OPERATIONS
    # ========================================

    def get_party_summary(self) -> Optional[list]:
        """Get cached party summary."""
        try:
            data = self.redis.get(PARTY_SUMMARY_KEY)
            if data:
                logger.debug("Cache HIT: party_summary")
                return json.loads(data)
            logger.debug("Cache MISS: party_summary")
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set_party_summary(self, summary: list) -> bool:
        """Cache party summary."""
        try:
            self.redis.setex(
                PARTY_SUMMARY_KEY,
                self.ttl,
                json.dumps(summary, ensure_ascii=False)
            )
            logger.info(f"Cached party_summary ({len(summary)} parties, TTL={self.ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def get_totals(self) -> Optional[Dict[str, Any]]:
        """Get cached totals."""
        try:
            data = self.redis.get(TOTALS_KEY)
            if data:
                logger.debug("Cache HIT: totals")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set_totals(self, totals: Dict[str, Any]) -> bool:
        """Cache totals."""
        try:
            self.redis.setex(
                TOTALS_KEY,
                self.ttl,
                json.dumps(totals, ensure_ascii=False)
            )
            logger.info(f"Cached totals (TTL={self.ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def get_forms(self, limit: int = 50) -> Optional[list]:
        """Get cached forms (limited)."""
        try:
            data = self.redis.get(f"{FORMS_KEY}:{limit}")
            if data:
                logger.debug(f"Cache HIT: forms (limit={limit})")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set_forms(self, forms: list, limit: int = 50) -> bool:
        """Cache forms."""
        try:
            self.redis.setex(
                f"{FORMS_KEY}:{limit}",
                self.ttl,
                json.dumps(forms, ensure_ascii=False)
            )
            logger.info(f"Cached forms ({len(forms)} forms, limit={limit}, TTL={self.ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def get_full_response(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get full cached API response."""
        try:
            data = self.redis.get(f"{CACHE_PREFIX}response:{limit}")
            if data:
                logger.debug(f"Cache HIT: full_response (limit={limit})")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set_full_response(self, response: Dict[str, Any], limit: int = 50) -> bool:
        """Cache full API response."""
        try:
            # Add cache metadata
            response['_cache'] = {
                'cached_at': datetime.utcnow().isoformat(),
                'ttl_seconds': self.ttl,
                'source': 'redis'
            }
            self.redis.setex(
                f"{CACHE_PREFIX}response:{limit}",
                self.ttl,
                json.dumps(response, ensure_ascii=False)
            )
            logger.info(f"Cached full_response (limit={limit}, TTL={self.ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    # ========================================
    # CACHE MANAGEMENT
    # ========================================

    def clear_all(self) -> int:
        """
        Clear all E-14 cache entries.

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis.keys(f"{CACHE_PREFIX}*")
            if keys:
                count = self.redis.delete(*keys)
                logger.info(f"Cleared {count} E-14 cache keys")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def clear_forms(self) -> int:
        """Clear only forms cache (keeps summaries)."""
        try:
            keys = self.redis.keys(f"{FORMS_KEY}:*") + self.redis.keys(f"{CACHE_PREFIX}response:*")
            if keys:
                count = self.redis.delete(*keys)
                logger.info(f"Cleared {count} form cache keys")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            keys = self.redis.keys(f"{CACHE_PREFIX}*")
            info = {
                'available': True,
                'total_keys': len(keys),
                'keys': [],
                'ttl_default': self.ttl
            }

            for key in keys:
                ttl = self.redis.ttl(key)
                size = len(self.redis.get(key) or '')
                info['keys'].append({
                    'key': key,
                    'ttl_remaining': ttl,
                    'size_bytes': size
                })

            return info
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            return {'available': False, 'error': str(e)}

    def warm_cache_from_db(self) -> bool:
        """
        Warm cache from PostgreSQL database.

        Loads aggregated data from e14_party_totals view.
        """
        try:
            import psycopg2

            conn = psycopg2.connect(
                dbname='castor_elecciones',
                host='localhost',
                port=5432
            )

            with conn.cursor() as cur:
                # Get party summary
                cur.execute("""
                    SELECT party_name, total_votes, mesas_count, avg_confidence
                    FROM e14_party_totals
                    ORDER BY total_votes DESC
                    LIMIT 30
                """)
                party_summary = [
                    {
                        'party_name': row[0],
                        'total_votes': row[1],
                        'mesas_count': row[2],
                        'avg_confidence': float(row[3]) if row[3] else 0.5
                    }
                    for row in cur.fetchall()
                ]

                # Get totals
                cur.execute("""
                    SELECT
                        COUNT(*) as total_forms,
                        SUM(total_votos) as total_votes,
                        AVG(confidence) as avg_confidence
                    FROM e14_forms
                """)
                row = cur.fetchone()
                totals = {
                    'total_forms': row[0],
                    'total_votes': row[1],
                    'avg_confidence': float(row[2]) if row[2] else 0.5
                }

            conn.close()

            # Cache the data
            self.set_party_summary(party_summary)
            self.set_totals(totals)

            logger.info("Cache warmed from PostgreSQL")
            return True

        except Exception as e:
            logger.error(f"Cache warm error: {e}")
            return False


# Singleton instance
_cache_service: Optional[E14CacheService] = None


def get_e14_cache_service() -> E14CacheService:
    """Get singleton cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = E14CacheService()
    return _cache_service
