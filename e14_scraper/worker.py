"""
Worker de scraping - Ejecuta las tareas de extracción de E-14
"""
import asyncio
import random
import json
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import asyncpg

from config import settings
from models import ScrapingTask
from orchestrator import TaskQueue
from captcha_solver import CaptchaSolver

logger = structlog.get_logger()


class E14Worker:
    """Worker que extrae datos de formularios E-14"""

    def __init__(
        self,
        worker_id: str,
        queue: TaskQueue,
        pool: asyncpg.Pool,
        shutdown_event: asyncio.Event,
        proxy: Optional[str] = None
    ):
        self.worker_id = worker_id
        self.queue = queue
        self.pool = pool
        self.shutdown_event = shutdown_event
        self.proxy = proxy

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.captcha_solver = CaptchaSolver() if settings.captcha_api_key else None

        self.tasks_completed = 0
        self.tasks_failed = 0

        self.log = logger.bind(worker_id=worker_id)

    async def initialize_browser(self):
        """Inicializa el navegador con configuración anti-detección"""
        playwright = await async_playwright().start()

        # Configuración del navegador para evitar detección
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
            'headless': True,  # Cambiar a False para debug
            'args': browser_args,
        }

        # Configurar proxy si está disponible
        if self.proxy:
            launch_options['proxy'] = {'server': self.proxy}

        self.browser = await playwright.chromium.launch(**launch_options)

        # Crear contexto con configuración realista
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self._get_random_user_agent(),
            locale='es-CO',
            timezone_id='America/Bogota',
            geolocation={'latitude': 4.7110, 'longitude': -74.0721},  # Bogotá
            permissions=['geolocation'],
        )

        # Inyectar scripts anti-detección
        await self.context.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Ocultar plugins vacíos
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});

            // Ocultar languages
            Object.defineProperty(navigator, 'languages', {get: () => ['es-CO', 'es', 'en']});

            // Chrome runtime
            window.chrome = {runtime: {}};
        """)

        self.page = await self.context.new_page()
        self.log.info("Navegador inicializado")

    async def close_browser(self):
        """Cierra el navegador de forma segura"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def warm_up_session(self):
        """
        'Calienta' la sesión navegando normalmente para mejorar el score de reCAPTCHA v3.
        Esto simula comportamiento humano antes de hacer scraping masivo.
        """
        self.log.info("Calentando sesión...")

        try:
            # Navegar a la página principal
            await self.page.goto(settings.base_url, wait_until='networkidle')
            await self._random_delay(2, 4)

            # Simular movimientos de mouse
            await self._simulate_human_behavior()

            # Hacer clic en algunos elementos de navegación
            await self.page.click('body')  # Click genérico
            await self._random_delay(1, 2)

            self.log.info("Sesión calentada correctamente")

        except Exception as e:
            self.log.warning("Error calentando sesión", error=str(e))

    async def _simulate_human_behavior(self):
        """Simula comportamiento humano en la página"""
        # Movimientos de mouse aleatorios
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await self.page.mouse.move(x, y)
            await self._random_delay(0.1, 0.3)

        # Scroll aleatorio
        await self.page.evaluate(f"window.scrollTo(0, {random.randint(100, 500)})")
        await self._random_delay(0.5, 1)

    async def _random_delay(self, min_sec: float, max_sec: float):
        """Delay aleatorio para simular comportamiento humano"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    def _get_random_user_agent(self) -> str:
        """Retorna un User-Agent aleatorio realista"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
        return random.choice(user_agents)

    async def process_task(self, task: ScrapingTask) -> Dict[str, Any]:
        """
        Procesa una tarea de scraping individual.
        Navega a la página del puesto de votación y extrae los datos del E-14.
        """
        self.log.info(
            "Procesando tarea",
            task_id=task.id,
            departamento=task.departamento_nombre,
            municipio=task.municipio_nombre
        )

        try:
            # Navegar a la página con los filtros correctos
            await self._navigate_to_e14(task)

            # Manejar CAPTCHA si aparece
            captcha_solved = await self._handle_captcha_if_needed()

            if not captcha_solved:
                raise Exception("No se pudo resolver el CAPTCHA")

            # Esperar a que cargue el E-14
            await self._random_delay(1, 2)

            # Extraer datos del E-14
            e14_data = await self._extract_e14_data(task)

            # Descargar imagen si está configurado
            if settings.save_images:
                e14_data['imagen_path'] = await self._download_e14_image(task)

            return e14_data

        except Exception as e:
            self.log.error("Error procesando tarea", task_id=task.id, error=str(e))
            raise

    async def _navigate_to_e14(self, task: ScrapingTask):
        """Navega a la página del E-14 específico"""
        # Ir a la página principal
        await self.page.goto(settings.base_url, wait_until='networkidle')
        await self._random_delay(1, 2)

        # Mapear corporación al valor del select
        corp_value = 'SEN_1' if task.corporacion == 'senado' else 'CAM_1'

        # Seleccionar corporación
        await self.page.wait_for_selector('#selectCorp', timeout=15000)
        await self.page.select_option('#selectCorp', corp_value)
        await self._random_delay(0.8, 1.2)

        # Seleccionar departamento
        await self.page.wait_for_selector('#selectDepto', timeout=10000)
        await self.page.select_option('#selectDepto', task.departamento_id)
        await self._random_delay(1, 1.5)

        # Seleccionar municipio
        await self.page.wait_for_selector('#selectMpio', timeout=10000)
        await self.page.select_option('#selectMpio', task.municipio_id)
        await self._random_delay(1, 1.5)

        # Seleccionar zona si existe
        if task.zona_id:
            await self.page.wait_for_selector('#selectZona', timeout=10000)
            await self.page.select_option('#selectZona', task.zona_id)
            await self._random_delay(0.8, 1.2)

        # Seleccionar puesto si existe
        if task.puesto_id:
            await self.page.wait_for_selector('#selectPto', timeout=10000)
            await self.page.select_option('#selectPto', task.puesto_id)
            await self._random_delay(0.8, 1.2)

        # Hacer clic en consultar
        submit_button = await self.page.query_selector('#btnConsultar, button[type="submit"], .btn-consultar')
        if submit_button:
            await submit_button.click()
            await self.page.wait_for_load_state('networkidle')

    async def _wait_and_select(self, field_name: str, value: str):
        """Espera a que un select esté disponible y selecciona el valor"""
        selector = f"#{field_name}"
        try:
            await self.page.wait_for_selector(selector, timeout=10000)
            await self.page.select_option(selector, value)
        except Exception as e:
            self.log.warning(f"No se pudo seleccionar {field_name}", error=str(e))

    async def _handle_captcha_if_needed(self) -> bool:
        """Detecta y resuelve CAPTCHA si es necesario"""
        # Verificar si hay un reCAPTCHA visible
        recaptcha_frame = await self.page.query_selector('iframe[src*="recaptcha"]')

        if not recaptcha_frame:
            # No hay CAPTCHA visible, verificar si es v3 (invisible)
            recaptcha_v3 = await self.page.evaluate("""
                () => typeof grecaptcha !== 'undefined' && grecaptcha.execute !== undefined
            """)

            if recaptcha_v3:
                # reCAPTCHA v3 se ejecuta automáticamente, solo esperamos
                self.log.debug("reCAPTCHA v3 detectado, ejecutando automáticamente")
                try:
                    # Ejecutar reCAPTCHA v3
                    token = await self.page.evaluate("""
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
                    self.log.warning("Error ejecutando reCAPTCHA v3", error=str(e))

            return True  # No hay CAPTCHA

        # Hay CAPTCHA v2 visible - usar solver externo
        if self.captcha_solver:
            self.log.info("CAPTCHA v2 detectado, resolviendo...")
            try:
                # Obtener sitekey del CAPTCHA
                sitekey = await self.page.evaluate("""
                    () => {
                        const elem = document.querySelector('[data-sitekey]');
                        return elem ? elem.getAttribute('data-sitekey') : null;
                    }
                """)

                if sitekey:
                    # Resolver con servicio externo
                    token = await self.captcha_solver.solve_recaptcha_v2(
                        sitekey=sitekey,
                        page_url=self.page.url
                    )

                    # Inyectar el token
                    await self.page.evaluate(f"""
                        document.querySelector('[name="g-recaptcha-response"]').value = '{token}';
                    """)

                    self.log.info("CAPTCHA resuelto exitosamente")
                    return True

            except Exception as e:
                self.log.error("Error resolviendo CAPTCHA", error=str(e))
                return False

        self.log.warning("CAPTCHA detectado pero no hay solver configurado")
        return False

    async def _extract_e14_data(self, task: ScrapingTask) -> Dict[str, Any]:
        """Extrae los datos del formulario E-14 de la página"""
        # Esta función debe adaptarse a la estructura real del E-14
        # Por ahora, extraemos datos genéricos

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
            # Esperar a que cargue la tabla de resultados
            await self.page.wait_for_selector('.tabla-resultados, .e14-data, table', timeout=15000)

            # Extraer datos de la tabla (adaptar selectores según página real)
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

            # Extraer totales
            totales_element = await self.page.query_selector('.total-votos, .totales')
            if totales_element:
                data['totales']['total'] = await totales_element.inner_text()

            # Extraer URL de imagen del E-14
            img_element = await self.page.query_selector('img.e14-image, .acta-imagen img')
            if img_element:
                data['imagen_url'] = await img_element.get_attribute('src')

        except Exception as e:
            self.log.warning("Error extrayendo datos E-14", error=str(e))
            # Guardar HTML para debug
            data['raw_html'] = await self.page.content()

        return data

    async def _download_e14_image(self, task: ScrapingTask) -> Optional[str]:
        """Descarga la imagen del E-14 si está disponible"""
        import os
        import aiohttp

        try:
            img_element = await self.page.query_selector('img.e14-image, .acta-imagen img, img[src*="e14"]')
            if not img_element:
                return None

            img_url = await img_element.get_attribute('src')
            if not img_url:
                return None

            # Crear directorio de salida
            output_dir = f"{settings.output_dir}/{task.departamento_id}/{task.municipio_id}"
            os.makedirs(output_dir, exist_ok=True)

            # Nombre del archivo
            filename = f"e14_{task.corporacion}_{task.puesto_id or 'unknown'}.png"
            filepath = f"{output_dir}/{filename}"

            # Descargar imagen
            async with aiohttp.ClientSession() as session:
                async with session.get(img_url) as response:
                    if response.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await response.read())
                        return filepath

        except Exception as e:
            self.log.warning("Error descargando imagen E-14", error=str(e))

        return None

    async def save_result(self, task: ScrapingTask, data: Dict[str, Any]):
        """Guarda el resultado en la base de datos"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO e14_results
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
        """Loop principal del worker"""
        try:
            await self.initialize_browser()
            await self.warm_up_session()

            # Registrar worker en la DB
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO worker_sessions (worker_id, proxy_address, is_active)
                    VALUES ($1, $2, TRUE)
                    ON CONFLICT (worker_id) DO UPDATE
                    SET is_active = TRUE, started_at = NOW()
                """, self.worker_id, self.proxy)

            self.log.info("Worker iniciado")

            while not self.shutdown_event.is_set():
                # Obtener siguiente tarea
                task = await self.queue.claim_task(self.worker_id)

                if not task:
                    # No hay tareas disponibles, esperar un poco
                    await asyncio.sleep(2)
                    continue

                try:
                    # Procesar tarea
                    result = await self.process_task(task)

                    # Guardar resultado
                    await self.save_result(task, result)

                    # Marcar como completada
                    await self.queue.complete_task(
                        task_id=task.id,
                        worker_id=self.worker_id,
                        e14_data=result,
                        e14_url=result.get('imagen_url')
                    )

                    self.tasks_completed += 1

                    # Rate limiting - esperar entre requests
                    delay = 60 / settings.requests_per_minute_per_worker
                    await asyncio.sleep(delay)

                except Exception as e:
                    self.tasks_failed += 1
                    await self.queue.fail_task(
                        task_id=task.id,
                        worker_id=self.worker_id,
                        error=str(e),
                        should_retry=True
                    )
                    # Esperar más tiempo después de un error
                    await asyncio.sleep(5)

                # Actualizar actividad del worker
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE worker_sessions
                        SET last_activity = NOW(),
                            tasks_completed = $2,
                            tasks_failed = $3
                        WHERE worker_id = $1
                    """, self.worker_id, self.tasks_completed, self.tasks_failed)

        except Exception as e:
            self.log.exception("Error fatal en worker", error=str(e))

        finally:
            # Limpiar
            await self.close_browser()

            # Marcar worker como inactivo
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE worker_sessions SET is_active = FALSE WHERE worker_id = $1
                """, self.worker_id)

            self.log.info(
                "Worker finalizado",
                completed=self.tasks_completed,
                failed=self.tasks_failed
            )
