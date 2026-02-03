"""
CAPTCHA solving module using external services (2Captcha).
Supports reCAPTCHA v2, v3 and hCaptcha.
"""
import asyncio
import logging
from typing import Optional

import aiohttp

from .config import get_scraper_config

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """
    Solve CAPTCHAs using 2Captcha service.
    Supports reCAPTCHA v2, v3 and hCaptcha.

    Cost: ~$0.50 per 1000 CAPTCHAs
    """

    def __init__(self, api_key: Optional[str] = None):
        config = get_scraper_config()
        self.api_key = api_key or config.captcha_api_key
        self.base_url = "https://2captcha.com"

        if not self.api_key:
            logger.warning("No CAPTCHA API key configured")

    async def solve_recaptcha_v2(
        self,
        sitekey: str,
        page_url: str,
        invisible: bool = False
    ) -> Optional[str]:
        """
        Solve reCAPTCHA v2.

        Args:
            sitekey: The site key (data-sitekey attribute)
            page_url: URL of the page with CAPTCHA
            invisible: True for invisible reCAPTCHA

        Returns:
            CAPTCHA response token or None if failed
        """
        if not self.api_key:
            raise ValueError("CAPTCHA API key not configured")

        logger.info("Solving reCAPTCHA v2", extra={"sitekey": sitekey[:20]})

        async with aiohttp.ClientSession() as session:
            # Step 1: Submit CAPTCHA for solving
            submit_url = f"{self.base_url}/in.php"
            params = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': sitekey,
                'pageurl': page_url,
                'json': 1
            }

            if invisible:
                params['invisible'] = 1

            async with session.get(submit_url, params=params) as response:
                result = await response.json()

                if result.get('status') != 1:
                    logger.error("Error submitting CAPTCHA", extra={"error": result.get('request')})
                    return None

                captcha_id = result['request']
                logger.info("CAPTCHA submitted", extra={"captcha_id": captcha_id})

            # Step 2: Poll for result
            result_url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }

            max_attempts = 30  # Max 2.5 minutes wait
            for attempt in range(max_attempts):
                await asyncio.sleep(5)

                async with session.get(result_url, params=params) as response:
                    result = await response.json()

                    if result.get('status') == 1:
                        token = result['request']
                        logger.info("CAPTCHA solved successfully")
                        return token

                    if result.get('request') == 'CAPCHA_NOT_READY':
                        logger.debug(f"CAPTCHA not ready, attempt {attempt + 1}/{max_attempts}")
                        continue

                    logger.error("Error getting result", extra={"error": result.get('request')})
                    return None

            logger.error("CAPTCHA solving timeout")
            return None

    async def solve_recaptcha_v3(
        self,
        sitekey: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.7
    ) -> Optional[str]:
        """
        Solve reCAPTCHA v3.

        Args:
            sitekey: The site key
            page_url: URL of the page
            action: reCAPTCHA action (e.g. "submit", "login")
            min_score: Minimum required score (0.1-0.9)

        Returns:
            CAPTCHA response token or None if failed
        """
        if not self.api_key:
            raise ValueError("CAPTCHA API key not configured")

        logger.info("Solving reCAPTCHA v3", extra={"action": action, "min_score": min_score})

        async with aiohttp.ClientSession() as session:
            submit_url = f"{self.base_url}/in.php"
            params = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': sitekey,
                'pageurl': page_url,
                'version': 'v3',
                'action': action,
                'min_score': min_score,
                'json': 1
            }

            async with session.get(submit_url, params=params) as response:
                result = await response.json()

                if result.get('status') != 1:
                    logger.error("Error submitting reCAPTCHA v3", extra={"error": result.get('request')})
                    return None

                captcha_id = result['request']

            # Poll for result
            result_url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }

            for attempt in range(30):
                await asyncio.sleep(5)

                async with session.get(result_url, params=params) as response:
                    result = await response.json()

                    if result.get('status') == 1:
                        return result['request']

                    if result.get('request') != 'CAPCHA_NOT_READY':
                        logger.error("Error in reCAPTCHA v3", extra={"error": result.get('request')})
                        return None

            return None

    async def solve_hcaptcha(
        self,
        sitekey: str,
        page_url: str
    ) -> Optional[str]:
        """
        Solve hCaptcha.

        Args:
            sitekey: The site key
            page_url: URL of the page

        Returns:
            CAPTCHA response token or None if failed
        """
        if not self.api_key:
            raise ValueError("CAPTCHA API key not configured")

        logger.info("Solving hCaptcha")

        async with aiohttp.ClientSession() as session:
            submit_url = f"{self.base_url}/in.php"
            params = {
                'key': self.api_key,
                'method': 'hcaptcha',
                'sitekey': sitekey,
                'pageurl': page_url,
                'json': 1
            }

            async with session.get(submit_url, params=params) as response:
                result = await response.json()

                if result.get('status') != 1:
                    return None

                captcha_id = result['request']

            result_url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }

            for _ in range(30):
                await asyncio.sleep(5)

                async with session.get(result_url, params=params) as response:
                    result = await response.json()

                    if result.get('status') == 1:
                        return result['request']

                    if result.get('request') != 'CAPCHA_NOT_READY':
                        return None

            return None

    async def get_balance(self) -> float:
        """Get available balance in 2Captcha account."""
        if not self.api_key:
            return 0.0

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'getbalance',
                'json': 1
            }

            async with session.get(url, params=params) as response:
                result = await response.json()

                if result.get('status') == 1:
                    return float(result['request'])

                return 0.0

    async def report_bad(self, captcha_id: str):
        """Report a badly solved CAPTCHA for refund."""
        if not self.api_key:
            return

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'reportbad',
                'id': captcha_id,
                'json': 1
            }
            await session.get(url, params=params)
            logger.info("CAPTCHA reported as bad", extra={"captcha_id": captcha_id})


# Synchronous wrapper for use in non-async contexts
def get_captcha_balance_sync() -> float:
    """Synchronously get CAPTCHA balance (for testing)."""
    import asyncio
    solver = CaptchaSolver()
    return asyncio.run(solver.get_balance())
