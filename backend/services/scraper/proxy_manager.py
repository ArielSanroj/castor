"""
Proxy management for distributed scraping.
Supports intelligent rotation with health checks and performance scoring.
"""
import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

from .config import get_scraper_config

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """Information about a proxy server."""
    address: str  # format: protocol://user:pass@host:port or host:port
    protocol: str = "http"
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    fail_count: int = 0
    success_count: int = 0
    avg_response_time_ms: float = 0
    last_used: Optional[datetime] = None


class ProxyManager:
    """
    Manages a pool of proxies with intelligent rotation.

    Features:
    - Automatic health checks
    - Round-robin with failure penalties
    - Support for residential and datacenter proxies
    """

    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies: Dict[str, ProxyInfo] = {}
        self.current_index = 0
        self._lock = asyncio.Lock()

        if proxy_list:
            for proxy in proxy_list:
                self.add_proxy(proxy)

    def add_proxy(self, address: str):
        """Add a proxy to the pool."""
        # Normalize format
        if "://" not in address:
            address = f"http://{address}"

        protocol = address.split("://")[0]

        self.proxies[address] = ProxyInfo(
            address=address,
            protocol=protocol
        )
        logger.info("Proxy added", extra={"address": self._mask_proxy(address)})

    def _mask_proxy(self, address: str) -> str:
        """Mask proxy credentials for logging."""
        if "@" in address:
            parts = address.split("@")
            return f"***@{parts[-1]}"
        return address

    async def get_proxy(self) -> Optional[str]:
        """
        Get next available proxy using intelligent rotation.
        Prioritizes proxies with better history.
        """
        async with self._lock:
            if not self.proxies:
                return None

            healthy_proxies = [
                (addr, info) for addr, info in self.proxies.items()
                if info.is_healthy and info.fail_count < 5
            ]

            if not healthy_proxies:
                # Reset all proxies if none healthy
                logger.warning("All proxies marked unhealthy, resetting...")
                for info in self.proxies.values():
                    info.is_healthy = True
                    info.fail_count = 0
                healthy_proxies = list(self.proxies.items())

            # Sort by score (fewer failures, more successes)
            def proxy_score(item):
                addr, info = item
                score = info.success_count - (info.fail_count * 3)
                # Penalize recently used
                if info.last_used:
                    seconds_since_use = (datetime.now() - info.last_used).total_seconds()
                    if seconds_since_use < 2:
                        score -= 10
                return score

            healthy_proxies.sort(key=proxy_score, reverse=True)

            # Select from top proxies with some randomness
            top_count = min(5, len(healthy_proxies))
            selected_addr, selected_info = random.choice(healthy_proxies[:top_count])

            selected_info.last_used = datetime.now()

            return selected_addr

    async def report_success(self, proxy_address: str, response_time_ms: float = 0):
        """Report successful proxy use."""
        async with self._lock:
            if proxy_address in self.proxies:
                info = self.proxies[proxy_address]
                info.success_count += 1
                info.is_healthy = True

                # Update average response time
                if info.avg_response_time_ms == 0:
                    info.avg_response_time_ms = response_time_ms
                else:
                    info.avg_response_time_ms = (info.avg_response_time_ms + response_time_ms) / 2

    async def report_failure(self, proxy_address: str, error: Optional[str] = None):
        """Report proxy failure."""
        async with self._lock:
            if proxy_address in self.proxies:
                info = self.proxies[proxy_address]
                info.fail_count += 1

                # Mark unhealthy after multiple failures
                if info.fail_count >= 3:
                    info.is_healthy = False
                    logger.warning(
                        "Proxy marked unhealthy",
                        extra={
                            "proxy": self._mask_proxy(proxy_address),
                            "fail_count": info.fail_count,
                            "error": error
                        }
                    )

    async def health_check(self, proxy_address: str) -> bool:
        """Check if a proxy is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy_address,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        elapsed = (datetime.now() - start_time).total_seconds() * 1000
                        await self.report_success(proxy_address, elapsed)
                        return True

            await self.report_failure(proxy_address, "Bad status code")
            return False

        except Exception as e:
            await self.report_failure(proxy_address, str(e))
            return False

    async def check_all_proxies(self) -> int:
        """Check health of all proxies."""
        logger.info("Starting proxy health check...")

        tasks = [self.health_check(addr) for addr in self.proxies.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy = sum(1 for r in results if r is True)
        logger.info(f"Health check complete: {healthy}/{len(self.proxies)} proxies healthy")

        return healthy

    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        total = len(self.proxies)
        healthy = sum(1 for p in self.proxies.values() if p.is_healthy)

        return {
            "total": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "proxies": [
                {
                    "address": self._mask_proxy(addr),
                    "healthy": info.is_healthy,
                    "success": info.success_count,
                    "fail": info.fail_count,
                    "avg_response_ms": round(info.avg_response_time_ms, 2)
                }
                for addr, info in self.proxies.items()
            ]
        }

    @classmethod
    def from_file(cls, filepath: str) -> "ProxyManager":
        """Load proxies from a file (one per line)."""
        proxies = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {filepath}")

        return cls(proxy_list=proxies)


# Global singleton
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> Optional[ProxyManager]:
    """Get the global proxy manager instance."""
    global _proxy_manager

    config = get_scraper_config()

    if _proxy_manager is None and config.use_proxies:
        if config.proxy_list_file:
            _proxy_manager = ProxyManager.from_file(config.proxy_list_file)
        else:
            _proxy_manager = ProxyManager()

    return _proxy_manager
