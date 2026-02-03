"""
Gestor de proxies para distribución de carga
"""
import asyncio
import random
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiohttp
import structlog

from config import settings

logger = structlog.get_logger()


@dataclass
class ProxyInfo:
    """Información de un proxy"""
    address: str  # formato: protocol://user:pass@host:port o host:port
    protocol: str = "http"
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    fail_count: int = 0
    success_count: int = 0
    avg_response_time_ms: float = 0
    last_used: Optional[datetime] = None


class ProxyManager:
    """
    Gestiona un pool de proxies con rotación inteligente.
    Características:
    - Health checks automáticos
    - Rotación round-robin con penalización por fallos
    - Soporte para proxies residenciales y datacenter
    """

    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies: Dict[str, ProxyInfo] = {}
        self.current_index = 0
        self.log = logger.bind(component="proxy_manager")
        self._lock = asyncio.Lock()

        if proxy_list:
            for proxy in proxy_list:
                self.add_proxy(proxy)

    def add_proxy(self, address: str):
        """Añade un proxy al pool"""
        # Normalizar formato
        if "://" not in address:
            address = f"http://{address}"

        protocol = address.split("://")[0]

        self.proxies[address] = ProxyInfo(
            address=address,
            protocol=protocol
        )
        self.log.info("Proxy añadido", address=self._mask_proxy(address))

    def _mask_proxy(self, address: str) -> str:
        """Enmascara credenciales del proxy para logging"""
        if "@" in address:
            # Tiene credenciales
            parts = address.split("@")
            return f"***@{parts[-1]}"
        return address

    async def get_proxy(self) -> Optional[str]:
        """
        Obtiene el siguiente proxy disponible usando rotación inteligente.
        Prioriza proxies con mejor historial.
        """
        async with self._lock:
            if not self.proxies:
                return None

            healthy_proxies = [
                (addr, info) for addr, info in self.proxies.items()
                if info.is_healthy and info.fail_count < 5
            ]

            if not healthy_proxies:
                # Reset de todos los proxies si ninguno está saludable
                self.log.warning("Todos los proxies marcados como no saludables, reiniciando...")
                for info in self.proxies.values():
                    info.is_healthy = True
                    info.fail_count = 0
                healthy_proxies = list(self.proxies.items())

            # Ordenar por score (menos fallos, más éxitos)
            def proxy_score(item):
                addr, info = item
                score = info.success_count - (info.fail_count * 3)
                # Penalizar si se usó recientemente
                if info.last_used:
                    seconds_since_use = (datetime.now() - info.last_used).total_seconds()
                    if seconds_since_use < 2:
                        score -= 10
                return score

            healthy_proxies.sort(key=proxy_score, reverse=True)

            # Seleccionar el mejor proxy (con algo de aleatoriedad)
            top_count = min(5, len(healthy_proxies))
            selected_addr, selected_info = random.choice(healthy_proxies[:top_count])

            selected_info.last_used = datetime.now()

            return selected_addr

    async def report_success(self, proxy_address: str, response_time_ms: float = 0):
        """Reporta un uso exitoso del proxy"""
        async with self._lock:
            if proxy_address in self.proxies:
                info = self.proxies[proxy_address]
                info.success_count += 1
                info.is_healthy = True

                # Actualizar tiempo de respuesta promedio
                if info.avg_response_time_ms == 0:
                    info.avg_response_time_ms = response_time_ms
                else:
                    info.avg_response_time_ms = (info.avg_response_time_ms + response_time_ms) / 2

    async def report_failure(self, proxy_address: str, error: Optional[str] = None):
        """Reporta un fallo del proxy"""
        async with self._lock:
            if proxy_address in self.proxies:
                info = self.proxies[proxy_address]
                info.fail_count += 1

                # Marcar como no saludable después de varios fallos
                if info.fail_count >= 3:
                    info.is_healthy = False
                    self.log.warning(
                        "Proxy marcado como no saludable",
                        proxy=self._mask_proxy(proxy_address),
                        fail_count=info.fail_count,
                        error=error
                    )

    async def health_check(self, proxy_address: str) -> bool:
        """Verifica la salud de un proxy"""
        try:
            async with aiohttp.ClientSession() as session:
                proxy_url = proxy_address

                start_time = datetime.now()
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy_url,
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

    async def check_all_proxies(self):
        """Verifica la salud de todos los proxies"""
        self.log.info("Iniciando health check de proxies...")

        tasks = [self.health_check(addr) for addr in self.proxies.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy = sum(1 for r in results if r is True)
        self.log.info(f"Health check completado: {healthy}/{len(self.proxies)} proxies saludables")

        return healthy

    def get_stats(self) -> Dict:
        """Obtiene estadísticas del pool de proxies"""
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
        """Carga proxies desde un archivo (uno por línea)"""
        proxies = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
        except FileNotFoundError:
            logger.warning(f"Archivo de proxies no encontrado: {filepath}")

        return cls(proxy_list=proxies)


# Singleton para uso global
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> Optional[ProxyManager]:
    """Obtiene el gestor de proxies global"""
    global _proxy_manager

    if _proxy_manager is None and settings.use_proxies:
        if settings.proxy_list_file:
            _proxy_manager = ProxyManager.from_file(settings.proxy_list_file)
        else:
            _proxy_manager = ProxyManager()

    return _proxy_manager


# Ejemplo de archivo de proxies (proxies.txt):
"""
# Proxies residenciales (más caros pero mejor para evitar bloqueos)
http://user:pass@residential-proxy.com:8080

# Proxies datacenter (más baratos pero pueden ser detectados)
http://user:pass@dc-proxy.com:8080

# Proxies SOCKS5
socks5://user:pass@socks-proxy.com:1080

# Proxies sin autenticación
http://123.456.789.012:8080
"""
