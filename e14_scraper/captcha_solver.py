"""
Módulo para resolver CAPTCHAs usando servicios externos
"""
import asyncio
import aiohttp
from typing import Optional
import structlog

from config import settings

logger = structlog.get_logger()


class CaptchaSolver:
    """
    Resuelve CAPTCHAs usando servicios externos como 2Captcha.
    Soporta reCAPTCHA v2, v3 y hCaptcha.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.captcha_api_key
        self.base_url = "https://2captcha.com"
        self.log = logger.bind(component="captcha_solver")

        if not self.api_key:
            self.log.warning("No hay API key de CAPTCHA configurada")

    async def solve_recaptcha_v2(
        self,
        sitekey: str,
        page_url: str,
        invisible: bool = False
    ) -> Optional[str]:
        """
        Resuelve reCAPTCHA v2.

        Args:
            sitekey: La clave del sitio (data-sitekey del elemento reCAPTCHA)
            page_url: URL de la página donde está el CAPTCHA
            invisible: True si es reCAPTCHA invisible

        Returns:
            Token de respuesta del CAPTCHA o None si falla
        """
        if not self.api_key:
            raise ValueError("API key de CAPTCHA no configurada")

        self.log.info("Resolviendo reCAPTCHA v2", sitekey=sitekey[:20] + "...")

        async with aiohttp.ClientSession() as session:
            # Paso 1: Enviar el CAPTCHA para resolver
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
                    self.log.error("Error enviando CAPTCHA", error=result.get('request'))
                    return None

                captcha_id = result['request']
                self.log.info("CAPTCHA enviado", captcha_id=captcha_id)

            # Paso 2: Esperar y obtener el resultado
            result_url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }

            # Intentar obtener resultado con reintentos
            max_attempts = 30  # Máximo 2.5 minutos de espera
            for attempt in range(max_attempts):
                await asyncio.sleep(5)  # Esperar 5 segundos entre intentos

                async with session.get(result_url, params=params) as response:
                    result = await response.json()

                    if result.get('status') == 1:
                        token = result['request']
                        self.log.info("CAPTCHA resuelto exitosamente")
                        return token

                    if result.get('request') == 'CAPCHA_NOT_READY':
                        self.log.debug(f"CAPTCHA no listo, intento {attempt + 1}/{max_attempts}")
                        continue

                    # Error permanente
                    self.log.error("Error obteniendo resultado", error=result.get('request'))
                    return None

            self.log.error("Timeout esperando resolución de CAPTCHA")
            return None

    async def solve_recaptcha_v3(
        self,
        sitekey: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.7
    ) -> Optional[str]:
        """
        Resuelve reCAPTCHA v3.

        Args:
            sitekey: La clave del sitio
            page_url: URL de la página
            action: Acción del reCAPTCHA (ej: "submit", "login")
            min_score: Score mínimo requerido (0.1-0.9)

        Returns:
            Token de respuesta o None si falla
        """
        if not self.api_key:
            raise ValueError("API key de CAPTCHA no configurada")

        self.log.info("Resolviendo reCAPTCHA v3", action=action, min_score=min_score)

        async with aiohttp.ClientSession() as session:
            # Enviar solicitud
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
                    self.log.error("Error enviando reCAPTCHA v3", error=result.get('request'))
                    return None

                captcha_id = result['request']

            # Obtener resultado
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
                        self.log.error("Error en reCAPTCHA v3", error=result.get('request'))
                        return None

            return None

    async def solve_hcaptcha(
        self,
        sitekey: str,
        page_url: str
    ) -> Optional[str]:
        """
        Resuelve hCaptcha.

        Args:
            sitekey: La clave del sitio
            page_url: URL de la página

        Returns:
            Token de respuesta o None si falla
        """
        if not self.api_key:
            raise ValueError("API key de CAPTCHA no configurada")

        self.log.info("Resolviendo hCaptcha")

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
        """Obtiene el balance disponible en la cuenta de 2Captcha"""
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
        """Reporta un CAPTCHA mal resuelto para reembolso"""
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
            self.log.info("CAPTCHA reportado como malo", captcha_id=captcha_id)
