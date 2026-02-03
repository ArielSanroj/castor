#!/usr/bin/env python3
"""
E-14 Scraper - Versión API Directa (Sin CAPTCHA)
================================================
Descarga masiva de formularios E-14 usando la API interna de la Registraduría.

Uso:
    python scraper_api.py                    # Ejecutar scraping completo
    python scraper_api.py --test             # Probar con 10 puestos
    python scraper_api.py --workers 50       # Usar 50 workers paralelos
    python scraper_api.py --output ./e14s    # Directorio de salida personalizado
"""

import asyncio
import aiohttp
import json
import re
import os
import sys
import time
import argparse
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

BASE_URL = "https://e14_congreso_2022.registraduria.gov.co"
DEFAULT_WORKERS = 30
DEFAULT_OUTPUT = "./output_e14"
REQUESTS_PER_SECOND = 50  # Rate limit global


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

@dataclass
class Puesto:
    """Representa un puesto de votación"""
    corp: str           # SEN o CAM
    corp_cod: str       # 1 o 2
    depto_cod: str
    depto_nombre: str
    mpio_cod: str
    mpio_nombre: str
    zona_cod: str
    zona_nombre: str
    puesto_cod: str
    puesto_nombre: str


@dataclass
class Mesa:
    """Representa una mesa de votación"""
    numero: str
    token: str
    puesto: Puesto


@dataclass
class Stats:
    """Estadísticas del scraping"""
    total_puestos: int = 0
    puestos_procesados: int = 0
    mesas_encontradas: int = 0
    pdfs_descargados: int = 0
    errores: int = 0
    inicio: float = 0

    @property
    def velocidad(self) -> float:
        elapsed = time.time() - self.inicio
        if elapsed > 0:
            return self.pdfs_descargados / elapsed
        return 0

    @property
    def progreso(self) -> float:
        if self.total_puestos > 0:
            return (self.puestos_procesados / self.total_puestos) * 100
        return 0


# ============================================================================
# CLIENTE API
# ============================================================================

class RegistraduriaAPI:
    """Cliente para la API de la Registraduría"""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.token: Optional[str] = None
        self.token_expires: float = 0

    async def get_token(self) -> str:
        """Obtiene o renueva el token JWT"""
        # Renovar si expira en menos de 5 minutos
        if self.token and time.time() < self.token_expires - 300:
            return self.token

        async with self.session.get(f"{BASE_URL}/auth/csrf") as resp:
            data = await resp.json()
            self.token = data['token']
            # Token dura 24 horas, pero renovamos cada 12
            self.token_expires = time.time() + 43200
            return self.token

    async def consultar_e14(self, puesto: Puesto) -> List[Mesa]:
        """Consulta las mesas de un puesto y retorna lista de tokens"""
        token = await self.get_token()

        data = {
            'corp': puesto.corp,
            'depto': puesto.depto_cod,
            'mpio': puesto.mpio_cod,
            'zona': puesto.zona_cod,
            'com': '',
            'pto': puesto.puesto_cod,
            'token': token,
            'g-recaptcha-response': ''  # ¡No necesario!
        }

        async with self.session.post(f"{BASE_URL}/consultarE14", data=data) as resp:
            html = await resp.text()

            # Extraer tokens de mesas
            matches = re.findall(r"descargarE14\('([^']+)'\).*?Mesa\s+(\d+)", html, re.DOTALL)

            mesas = []
            for token_mesa, numero in matches:
                mesas.append(Mesa(
                    numero=numero,
                    token=token_mesa,
                    puesto=puesto
                ))

            return mesas

    async def descargar_e14(self, mesa: Mesa) -> Optional[bytes]:
        """Descarga el PDF de un E-14"""
        token = await self.get_token()

        data = {
            'srcDescargaE14': mesa.token,
            'token': token
        }

        headers = {
            'Referer': f"{BASE_URL}/"
        }

        async with self.session.post(
            f"{BASE_URL}/descargae14",
            data=data,
            headers=headers
        ) as resp:
            if resp.status == 200:
                content = await resp.read()
                # Verificar que es PDF
                if content[:4] == b'%PDF':
                    return content
            return None


# ============================================================================
# SCRAPER PRINCIPAL
# ============================================================================

class E14Scraper:
    """Scraper principal que coordina la descarga masiva"""

    def __init__(
        self,
        output_dir: str = DEFAULT_OUTPUT,
        max_workers: int = DEFAULT_WORKERS,
        test_mode: bool = False
    ):
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.test_mode = test_mode
        self.stats = Stats()
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.rate_limiter: Optional[asyncio.Semaphore] = None

    async def run(self, puestos: List[Puesto]):
        """Ejecuta el scraping completo"""
        self.stats.total_puestos = len(puestos)
        self.stats.inicio = time.time()

        # Crear directorio de salida
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Semáforos para control de concurrencia
        self.semaphore = asyncio.Semaphore(self.max_workers)

        # Crear sesión HTTP con connection pool grande
        # SSL verificación deshabilitada (certificado del gobierno tiene issues)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(
            limit=self.max_workers * 2,
            limit_per_host=self.max_workers * 2,
            ssl=ssl_context
        )

        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            api = RegistraduriaAPI(session)

            # Obtener token inicial
            await api.get_token()
            print(f"✅ Token JWT obtenido")

            # Crear tareas para todos los puestos
            tasks = [
                self.procesar_puesto(api, puesto)
                for puesto in puestos
            ]

            # Ejecutar con barra de progreso
            print(f"\n🚀 Iniciando scraping de {len(puestos)} puestos con {self.max_workers} workers...\n")

            # Tarea de monitoreo
            monitor_task = asyncio.create_task(self.mostrar_progreso())

            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

            # Mostrar resumen final
            self.mostrar_resumen()

    async def procesar_puesto(self, api: RegistraduriaAPI, puesto: Puesto):
        """Procesa un puesto: consulta mesas y descarga PDFs"""
        async with self.semaphore:
            try:
                # Consultar mesas del puesto
                mesas = await api.consultar_e14(puesto)
                self.stats.mesas_encontradas += len(mesas)

                # Descargar cada mesa
                for mesa in mesas:
                    await self.descargar_mesa(api, mesa)

                self.stats.puestos_procesados += 1

            except Exception as e:
                self.stats.errores += 1
                # Log error silencioso para no interrumpir el progreso

    async def descargar_mesa(self, api: RegistraduriaAPI, mesa: Mesa):
        """Descarga el PDF de una mesa"""
        try:
            pdf_content = await api.descargar_e14(mesa)

            if pdf_content:
                # Crear estructura de directorios
                dir_path = self.output_dir / mesa.puesto.corp / mesa.puesto.depto_nombre / mesa.puesto.mpio_nombre
                dir_path.mkdir(parents=True, exist_ok=True)

                # Nombre del archivo
                filename = f"{mesa.puesto.zona_cod}_{mesa.puesto.puesto_cod}_mesa{mesa.numero}.pdf"
                filepath = dir_path / filename

                # Guardar PDF
                with open(filepath, 'wb') as f:
                    f.write(pdf_content)

                self.stats.pdfs_descargados += 1

        except Exception as e:
            self.stats.errores += 1

    async def mostrar_progreso(self):
        """Muestra el progreso en tiempo real"""
        while True:
            await asyncio.sleep(2)

            elapsed = time.time() - self.stats.inicio

            # Calcular ETA
            if self.stats.puestos_procesados > 0:
                rate = self.stats.puestos_procesados / elapsed
                remaining = self.stats.total_puestos - self.stats.puestos_procesados
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                eta_str = "calculando..."

            # Barra de progreso
            progress = self.stats.progreso
            bar_width = 30
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Limpiar línea y mostrar progreso
            sys.stdout.write(f"\r[{bar}] {progress:.1f}% | "
                           f"Puestos: {self.stats.puestos_procesados}/{self.stats.total_puestos} | "
                           f"PDFs: {self.stats.pdfs_descargados} | "
                           f"Vel: {self.stats.velocidad:.1f}/s | "
                           f"ETA: {eta_str}    ")
            sys.stdout.flush()

    def mostrar_resumen(self):
        """Muestra el resumen final"""
        elapsed = time.time() - self.stats.inicio

        print("\n\n" + "=" * 60)
        print("📊 RESUMEN FINAL")
        print("=" * 60)
        print(f"   Puestos procesados: {self.stats.puestos_procesados:,}")
        print(f"   Mesas encontradas:  {self.stats.mesas_encontradas:,}")
        print(f"   PDFs descargados:   {self.stats.pdfs_descargados:,}")
        print(f"   Errores:            {self.stats.errores:,}")
        print(f"   Tiempo total:       {elapsed/60:.1f} minutos")
        print(f"   Velocidad promedio: {self.stats.velocidad:.1f} PDFs/segundo")
        print(f"   Directorio salida:  {self.output_dir.absolute()}")
        print("=" * 60)


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def cargar_puestos(filepath: str) -> List[Puesto]:
    """Carga la lista de puestos desde el archivo JSON existente"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    puestos = []
    for item in data:
        # Determinar corp y cod
        corp = item['corporacion'][:3].upper()  # SEN o CAM
        corp_cod = '1' if corp == 'SEN' else '2'

        puestos.append(Puesto(
            corp=corp,
            corp_cod=corp_cod,
            depto_cod=item['departamento_cod'],
            depto_nombre=limpiar_nombre(item['departamento']),
            mpio_cod=item['municipio_cod'],
            mpio_nombre=limpiar_nombre(item['municipio']),
            zona_cod=item['zona_cod'],
            zona_nombre=item['zona'],
            puesto_cod=item['puesto_cod'],
            puesto_nombre=item['puesto']
        ))

    return puestos


def limpiar_nombre(nombre: str) -> str:
    """Limpia el nombre para usar como directorio"""
    # Remover códigos y porcentajes
    nombre = re.sub(r'^\d+\s*-\s*', '', nombre)
    nombre = re.sub(r'\s*\([^)]*%[^)]*\)', '', nombre)
    # Caracteres seguros para directorios
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    return nombre.strip()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description='E-14 Scraper - Descarga masiva de formularios electorales'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Modo prueba: solo procesa 10 puestos'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        help=f'Número de workers paralelos (default: {DEFAULT_WORKERS})'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=DEFAULT_OUTPUT,
        help=f'Directorio de salida (default: {DEFAULT_OUTPUT})'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='/Users/arielsanroj/actas_e14_masivo/lista_puestos_congreso_2022.json',
        help='Archivo JSON con lista de puestos'
    )

    args = parser.parse_args()

    # Banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           E-14 SCRAPER - API DIRECTA (SIN CAPTCHA)            ║
║                   Registraduría Nacional                       ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    # Cargar puestos
    print(f"📂 Cargando puestos desde {args.data}...")
    puestos = cargar_puestos(args.data)
    print(f"   Encontrados {len(puestos):,} puestos")

    # Modo test
    if args.test:
        puestos = puestos[:10]
        print(f"   🧪 Modo test: usando solo {len(puestos)} puestos")

    # Crear y ejecutar scraper
    scraper = E14Scraper(
        output_dir=args.output,
        max_workers=args.workers,
        test_mode=args.test
    )

    await scraper.run(puestos)


if __name__ == "__main__":
    asyncio.run(main())
