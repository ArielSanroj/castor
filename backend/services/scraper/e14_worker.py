"""
E-14 Worker - Extracts electoral data using Playwright browser automation.
"""
import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    async_playwright = None  # Optional dependency

from .config import get_scraper_config
from .task_queue import TaskQueue, ScrapingTask
from .captcha_solver import CaptchaSolver

logger = logging.getLogger(__name__)


class E14Worker:
    """Worker that extracts E-14 electoral data."""

    # User agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]

    def __init__(
        self,
        worker_id: str,
        queue: TaskQueue,
        pool,  # asyncpg.Pool
        shutdown_event: asyncio.Event,
        proxy: Optional[str] = None
    ):
        self.worker_id = worker_id
        self.queue = queue
        self.pool = pool
        self.shutdown_event = shutdown_event
        self.proxy = proxy

        self.config = get_scraper_config()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.captcha_solver = CaptchaSolver() if self.config.captcha_api_key else None

        self.tasks_completed = 0
        self.tasks_failed = 0

    async def initialize_browser(self):
        """Initialize browser with anti-detection configuration."""
        if async_playwright is None:
            raise ImportError("playwright is required for E14Worker")

        playwright = await async_playwright().start()

        # Anti-detection browser args
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized',
        ]

        launch_options = {
            'headless': True,
            'args': browser_args,
        }

        if self.proxy:
            launch_options['proxy'] = {'server': self.proxy}

        self.browser = await playwright.chromium.launch(**launch_options)

        # Realistic browser context
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.USER_AGENTS),
            locale='es-CO',
            timezone_id='America/Bogota',
            geolocation={'latitude': 4.7110, 'longitude': -74.0721},  # Bogota
            permissions=['geolocation'],
        )

        # Anti-detection scripts
        await self.context.add_init_script("""
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Fake plugins
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});

            // Language settings
            Object.defineProperty(navigator, 'languages', {get: () => ['es-CO', 'es', 'en']});

            // Chrome runtime
            window.chrome = {runtime: {}};
        """)

        self.page = await self.context.new_page()
        logger.info(f"Browser initialized for worker {self.worker_id}")

    async def close_browser(self):
        """Close browser safely."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def warm_up_session(self):
        """Warm up session with human-like behavior to improve reCAPTCHA v3 score."""
        logger.info(f"Warming up session for {self.worker_id}")

        try:
            await self.page.goto(self.config.base_url, wait_until='networkidle')
            await self._random_delay(2, 4)

            # Simulate human behavior
            await self._simulate_human_behavior()

            await self.page.click('body')
            await self._random_delay(1, 2)

            logger.info(f"Session warmed up for {self.worker_id}")

        except Exception as e:
            logger.warning(f"Error warming up session: {e}")

    async def _simulate_human_behavior(self):
        """Simulate human mouse movements and scrolling."""
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await self.page.mouse.move(x, y)
            await self._random_delay(0.1, 0.3)

        # Random scroll
        await self.page.evaluate(f"window.scrollTo(0, {random.randint(100, 500)})")
        await self._random_delay(0.5, 1)

    async def _random_delay(self, min_sec: float, max_sec: float):
        """Random delay to simulate human behavior."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def process_task(self, task: ScrapingTask) -> Dict[str, Any]:
        """
        Process a single scraping task.
        Navigates to the E-14 page and extracts data.
        """
        logger.info(
            f"Processing task {task.id}",
            extra={
                "departamento": task.departamento_nombre,
                "municipio": task.municipio_nombre
            }
        )

        try:
            # Navigate to E-14 page with filters
            await self._navigate_to_e14(task)

            # Handle CAPTCHA if present
            captcha_solved = await self._handle_captcha_if_needed()
            if not captcha_solved:
                raise Exception("Could not solve CAPTCHA")

            await self._random_delay(1, 2)

            # Extract E-14 data
            e14_data = await self._extract_e14_data(task)

            # Download image if configured
            if self.config.save_images:
                e14_data['imagen_path'] = await self._download_e14_image(task)

            return e14_data

        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            raise

    async def _navigate_to_e14(self, task: ScrapingTask):
        """Navigate to the specific E-14 page."""
        await self.page.goto(self.config.base_url, wait_until='networkidle')
        await self._random_delay(1, 2)

        # Map corporacion to select value
        corp_value = 'SEN_1' if task.corporacion == 'senado' else 'CAM_1'

        # Select corporacion
        await self.page.wait_for_selector('#selectCorp', timeout=15000)
        await self.page.select_option('#selectCorp', corp_value)
        await self._random_delay(0.8, 1.2)

        # Select department
        await self.page.wait_for_selector('#selectDepto', timeout=10000)
        await self.page.select_option('#selectDepto', task.departamento_id)
        await self._random_delay(1, 1.5)

        # Select municipality
        await self.page.wait_for_selector('#selectMpio', timeout=10000)
        await self.page.select_option('#selectMpio', task.municipio_id)
        await self._random_delay(1, 1.5)

        # Select zone if present
        if task.zona_id:
            await self.page.wait_for_selector('#selectZona', timeout=10000)
            await self.page.select_option('#selectZona', task.zona_id)
            await self._random_delay(0.8, 1.2)

        # Select station if present
        if task.puesto_id:
            await self.page.wait_for_selector('#selectPto', timeout=10000)
            await self.page.select_option('#selectPto', task.puesto_id)
            await self._random_delay(0.8, 1.2)

        # Click submit
        submit_button = await self.page.query_selector(
            '#btnConsultar, button[type="submit"], .btn-consultar'
        )
        if submit_button:
            await submit_button.click()
            await self.page.wait_for_load_state('networkidle')

    async def _handle_captcha_if_needed(self) -> bool:
        """Detect and solve CAPTCHA if present."""
        # Check for visible reCAPTCHA v2
        recaptcha_frame = await self.page.query_selector('iframe[src*="recaptcha"]')

        if not recaptcha_frame:
            # Check for invisible v3
            recaptcha_v3 = await self.page.evaluate("""
                () => typeof grecaptcha !== 'undefined' && grecaptcha.execute !== undefined
            """)

            if recaptcha_v3:
                logger.debug("reCAPTCHA v3 detected, executing automatically")
                try:
                    await self.page.evaluate("""
                        async () => {
                            return new Promise((resolve) => {
                                grecaptcha.ready(() => {
                                    grecaptcha.execute().then(resolve);
                                });
                            });
                        }
                    """)
                    return True
                except Exception as e:
                    logger.warning(f"Error executing reCAPTCHA v3: {e}")

            return True  # No CAPTCHA

        # CAPTCHA v2 visible - use external solver
        if self.captcha_solver:
            logger.info("CAPTCHA v2 detected, solving...")
            try:
                sitekey = await self.page.evaluate("""
                    () => {
                        const elem = document.querySelector('[data-sitekey]');
                        return elem ? elem.getAttribute('data-sitekey') : null;
                    }
                """)

                if sitekey:
                    token = await self.captcha_solver.solve_recaptcha_v2(
                        sitekey=sitekey,
                        page_url=self.page.url
                    )

                    # Inject token
                    await self.page.evaluate(f"""
                        document.querySelector('[name="g-recaptcha-response"]').value = '{token}';
                    """)

                    logger.info("CAPTCHA solved successfully")
                    return True

            except Exception as e:
                logger.error(f"Error solving CAPTCHA: {e}")
                return False

        logger.warning("CAPTCHA detected but no solver configured")
        return False

    async def _extract_e14_data(self, task: ScrapingTask) -> Dict[str, Any]:
        """Extract E-14 data from the page."""
        data = {
            'task_id': task.id,
            'departamento': task.departamento_nombre,
            'municipio': task.municipio_nombre,
            'zona': task.zona_nombre,
            'puesto': task.puesto_nombre,
            'corporacion': task.corporacion,
            'extracted_at': datetime.now().isoformat(),
            'votos': {},
            'totales': {}
        }

        try:
            # Wait for results table
            await self.page.wait_for_selector(
                '.tabla-resultados, .e14-data, table',
                timeout=15000
            )

            # Extract table data
            rows = await self.page.query_selector_all('table tr, .resultado-row')

            for row in rows:
                cells = await row.query_selector_all('td, .cell')
                if len(cells) >= 2:
                    partido = await cells[0].inner_text()
                    votos_text = await cells[1].inner_text()
                    try:
                        votos = int(votos_text.replace(',', '').strip())
                        data['votos'][partido.strip()] = votos
                    except ValueError:
                        pass

            # Extract totals
            totales_element = await self.page.query_selector('.total-votos, .totales')
            if totales_element:
                data['totales']['total'] = await totales_element.inner_text()

            # Extract E-14 image URL
            img_element = await self.page.query_selector('img.e14-image, .acta-imagen img')
            if img_element:
                data['imagen_url'] = await img_element.get_attribute('src')

        except Exception as e:
            logger.warning(f"Error extracting E-14 data: {e}")
            data['raw_html'] = await self.page.content()

        return data

    async def _download_e14_image(self, task: ScrapingTask) -> Optional[str]:
        """Download E-14 image if available."""
        try:
            img_element = await self.page.query_selector(
                'img.e14-image, .acta-imagen img, img[src*="e14"]'
            )
            if not img_element:
                return None

            img_url = await img_element.get_attribute('src')
            if not img_url:
                return None

            # Create output directory
            output_dir = f"{self.config.output_dir}/{task.departamento_id}/{task.municipio_id}"
            os.makedirs(output_dir, exist_ok=True)

            filename = f"e14_{task.corporacion}_{task.puesto_id or 'unknown'}.png"
            filepath = f"{output_dir}/{filename}"

            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(img_url) as response:
                    if response.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await response.read())
                        return filepath

        except Exception as e:
            logger.warning(f"Error downloading E-14 image: {e}")

        return None

    async def save_result(self, task: ScrapingTask, data: Dict[str, Any]):
        """Save extraction result to database."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO e14_scraper_result
                (task_id, mesa_numero, total_votos, votos_por_partido, imagen_url, imagen_path, raw_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                task.id,
                data.get('mesa_numero'),
                data.get('totales', {}).get('total'),
                json.dumps(data.get('votos', {})),
                data.get('imagen_url'),
                data.get('imagen_path'),
                json.dumps(data)
            )

    async def run(self):
        """Main worker loop."""
        try:
            await self.initialize_browser()
            await self.warm_up_session()

            # Register worker
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scraper_worker_session (worker_id, proxy_address, is_active)
                    VALUES ($1, $2, TRUE)
                    ON CONFLICT (worker_id) DO UPDATE
                    SET is_active = TRUE, started_at = NOW()
                """, self.worker_id, self.proxy)

            logger.info(f"Worker {self.worker_id} started")

            while not self.shutdown_event.is_set():
                # Get next task
                task = await self.queue.claim_task(self.worker_id)

                if not task:
                    await asyncio.sleep(2)
                    continue

                try:
                    result = await self.process_task(task)
                    await self.save_result(task, result)

                    await self.queue.complete_task(
                        task_id=task.id,
                        worker_id=self.worker_id,
                        e14_data=result,
                        e14_url=result.get('imagen_url')
                    )

                    self.tasks_completed += 1

                    # Rate limiting
                    delay = 60 / self.config.requests_per_minute_per_worker
                    await asyncio.sleep(delay)

                except Exception as e:
                    self.tasks_failed += 1
                    await self.queue.fail_task(
                        task_id=task.id,
                        worker_id=self.worker_id,
                        error=str(e),
                        should_retry=True,
                        max_retries=self.config.max_retries
                    )
                    await asyncio.sleep(5)

                # Update worker activity
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE scraper_worker_session
                        SET last_activity = NOW(),
                            tasks_completed = $2,
                            tasks_failed = $3
                        WHERE worker_id = $1
                    """, self.worker_id, self.tasks_completed, self.tasks_failed)

        except Exception as e:
            logger.exception(f"Fatal error in worker {self.worker_id}: {e}")

        finally:
            await self.close_browser()

            # Mark worker as inactive
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE scraper_worker_session SET is_active = FALSE WHERE worker_id = $1
                """, self.worker_id)

            logger.info(
                f"Worker {self.worker_id} finished",
                extra={"completed": self.tasks_completed, "failed": self.tasks_failed}
            )
