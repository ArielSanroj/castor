#!/usr/bin/env python3
"""
DESCARGA OPTIMIZADA E-14 - CONGRESO 2022
Estrategias para minimizar CAPTCHAs:

1. BATCH POR MUNICIPIO - Procesa TODO un municipio antes de cambiar
   (El CAPTCHA se activa al cambiar zona/municipio, no al cambiar puesto)

2. SESIONES PARALELAS - Múltiples navegadores con sesiones calientes

3. PERSISTENCIA DE SESIÓN - Reutiliza cookies mientras sean válidas

4. DESCARGA DIRECTA - Una vez tienes tokens, descarga sin navegador

5. CAPTCHA SOLVER (opcional) - Integración con 2Captcha/Anti-Captcha
"""

import asyncio
import aiohttp
import json
import os
import re
import time
import random
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import argparse
import requests

# ============================================================
# CONFIGURACIÓN
# ============================================================
class Config:
    # Límites de velocidad
    MAX_CONCURRENT_DOWNLOADS = 20  # Descargas simultáneas de PDF
    DELAY_BETWEEN_PUESTOS = 0.5   # Segundos entre puestos (mismo municipio)
    DELAY_BETWEEN_MUNICIPIOS = 2  # Segundos al cambiar municipio

    # CAPTCHA Solver (2Captcha)
    CAPTCHA_API_KEY = None  # Poner tu key aquí o en variable de entorno
    CAPTCHA_SITE_KEY = "6LePIBcUAAAAAIYOdExWpG-STXLA0nnLRmXQlz_4"  # reCAPTCHA site key

    # Rutas
    OUTPUT_DIR = "pdfs_congreso_2022"
    PROGRESS_FILE = "progreso_optimizado.json"
    TOKENS_CACHE = "tokens_cache.json"


# ============================================================
# CAPTCHA SOLVER (2Captcha)
# ============================================================
class CaptchaSolver:
    """Resuelve reCAPTCHA v2/v3 usando 2Captcha API"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"

    def solve_recaptcha_v2(self, site_url, site_key):
        """Resuelve reCAPTCHA v2 y retorna el token"""
        if not self.api_key:
            return None

        try:
            # Enviar CAPTCHA
            resp = requests.post(f"{self.base_url}/in.php", data={
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': site_url,
                'json': 1
            }, timeout=30)

            result = resp.json()
            if result.get('status') != 1:
                print(f"  [2Captcha] Error enviando: {result}")
                return None

            task_id = result['request']
            print(f"  [2Captcha] Task ID: {task_id}")

            # Esperar resultado (polling)
            for _ in range(60):  # Máximo 2 minutos
                time.sleep(2)
                resp = requests.get(f"{self.base_url}/res.php", params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': task_id,
                    'json': 1
                }, timeout=30)

                result = resp.json()
                if result.get('status') == 1:
                    print(f"  [2Captcha] ✓ Resuelto!")
                    return result['request']
                elif result.get('request') != 'CAPCHA_NOT_READY':
                    print(f"  [2Captcha] Error: {result}")
                    return None

            print("  [2Captcha] Timeout")
            return None

        except Exception as e:
            print(f"  [2Captcha] Error: {e}")
            return None


# ============================================================
# ORGANIZADOR DE TRABAJO
# ============================================================
class WorkOrganizer:
    """Organiza puestos por municipio para minimizar cambios"""

    def __init__(self, puestos):
        self.puestos = puestos
        self.by_municipio = defaultdict(list)
        self._organize()

    def _organize(self):
        """Agrupa puestos por departamento+municipio+corporación"""
        for p in self.puestos:
            key = (p['corporacion_cod'], p['departamento_cod'], p['municipio_cod'])
            self.by_municipio[key].append(p)

    def get_work_batches(self):
        """Retorna batches organizados por municipio"""
        batches = []
        for key, puestos in self.by_municipio.items():
            corp_cod, depto_cod, muni_cod = key
            batches.append({
                'corporacion_cod': corp_cod,
                'departamento_cod': depto_cod,
                'municipio_cod': muni_cod,
                'corporacion': puestos[0]['corporacion'],
                'departamento': puestos[0]['departamento'],
                'municipio': puestos[0]['municipio'],
                'puestos': puestos
            })
        return batches

    def stats(self):
        """Estadísticas de trabajo"""
        total_puestos = sum(len(p) for p in self.by_municipio.values())
        return {
            'municipios': len(self.by_municipio),
            'puestos': total_puestos,
            'promedio_por_municipio': total_puestos / len(self.by_municipio)
        }


# ============================================================
# DOWNLOADER ASÍNCRONO
# ============================================================
class AsyncDownloader:
    """Descarga PDFs de forma asíncrona usando tokens"""

    def __init__(self, base_url, max_concurrent=20):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.semaphore = None
        self.session = None
        self.downloaded = 0
        self.errors = 0
        self.lock = asyncio.Lock()

    async def init_session(self, cookies):
        """Inicializa sesión aiohttp con cookies"""
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # Convertir cookies de Selenium a aiohttp
        jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(
            cookie_jar=jar,
            timeout=aiohttp.ClientTimeout(total=60)
        )

        # Agregar cookies
        for cookie in cookies:
            self.session.cookie_jar.update_cookies(
                {cookie['name']: cookie['value']},
                response_url=self.base_url
            )

    async def download_pdf(self, token, filepath):
        """Descarga un PDF por su token"""
        if os.path.exists(filepath):
            return True

        async with self.semaphore:
            try:
                async with self.session.post(
                    f"{self.base_url}/descargae14",
                    data={'token': token}
                ) as resp:
                    content = await resp.read()

                    if content[:4] == b'%PDF':
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        async with self.lock:
                            self.downloaded += 1
                        return True
                    else:
                        async with self.lock:
                            self.errors += 1
                        return False

            except Exception as e:
                async with self.lock:
                    self.errors += 1
                return False

    async def download_batch(self, tokens_with_paths):
        """Descarga un batch de PDFs en paralelo"""
        tasks = [
            self.download_pdf(token, path)
            for token, path in tokens_with_paths
        ]
        return await asyncio.gather(*tasks)

    async def close(self):
        if self.session:
            await self.session.close()


# ============================================================
# EXTRACTOR DE TOKENS
# ============================================================
class TokenExtractor:
    """Extrae tokens de mesas usando Selenium"""

    def __init__(self, base_url, captcha_solver=None):
        self.base_url = base_url
        self.driver = None
        self.captcha_solver = captcha_solver
        self.captchas_resueltos = 0

    def iniciar_chrome(self, headless=False, remote_port=None):
        """Inicia Chrome con configuración anti-detección"""
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1400,900')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        if headless:
            options.add_argument('--headless=new')

        if remote_port:
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{remote_port}")
            self.driver = webdriver.Chrome(options=options)
        else:
            self.driver = webdriver.Chrome(options=options)

            # Ocultar webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                '''
            })

        return self.driver

    def get_cookies(self):
        """Obtiene cookies actuales"""
        return self.driver.get_cookies()

    def navegar_inicial(self):
        """Navegación inicial para obtener sesión"""
        self.driver.get(self.base_url)
        time.sleep(random.uniform(2, 3))

    def seleccionar(self, select_id, valor, espera=1.0):
        """Selecciona valor en dropdown"""
        try:
            elem = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            time.sleep(random.uniform(0.2, 0.5))
            Select(elem).select_by_value(valor)
            time.sleep(espera * random.uniform(0.8, 1.2))
            return True
        except Exception as e:
            return False

    def consultar(self):
        """Click en botón consultar"""
        try:
            time.sleep(random.uniform(0.3, 0.7))
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(random.uniform(2, 3))
            return True
        except:
            return False

    def hay_captcha(self):
        """Detecta si hay CAPTCHA pendiente"""
        try:
            html = self.driver.page_source.lower()
            if 'captcha' in html or 'recaptcha' in html:
                # Verificar si ya está resuelto
                try:
                    resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                    if resp.get_attribute('value'):
                        return False
                except:
                    pass
                return True
        except:
            pass
        return False

    def resolver_captcha(self, timeout=300):
        """Resuelve CAPTCHA (manual o automático)"""

        # Intentar resolver automáticamente si hay API key
        if self.captcha_solver and self.captcha_solver.api_key:
            print("  [CAPTCHA] Intentando resolución automática...")
            token = self.captcha_solver.solve_recaptcha_v2(
                self.base_url,
                Config.CAPTCHA_SITE_KEY
            )

            if token:
                # Inyectar token
                self.driver.execute_script(f'''
                    document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                    if (typeof captchaCallback === 'function') captchaCallback('{token}');
                ''')
                self.captchas_resueltos += 1
                time.sleep(1)
                return True

        # Resolución manual
        print("\n" + "!"*55)
        print("  ⚠️  CAPTCHA DETECTADO - Resuélvelo manualmente")
        print(f"  (Esperando máximo {timeout}s)")
        print("!"*55)

        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                if resp.get_attribute('value'):
                    print("  [CAPTCHA] ✓ Resuelto manualmente!")
                    self.captchas_resueltos += 1
                    time.sleep(random.uniform(1, 2))
                    return True
            except:
                pass

            # También verificar si aparecen resultados
            if 'descargarE14' in self.driver.page_source:
                print("  [CAPTCHA] ✓ Resultados detectados!")
                return True

            time.sleep(2)

        return False

    def extraer_tokens(self):
        """Extrae todos los tokens de mesas de la página actual"""
        html = self.driver.page_source
        tokens = re.findall(r"descargarE14\(['\"]([^'\"]+)['\"]\)", html)
        return tokens

    def procesar_municipio(self, batch):
        """Procesa todos los puestos de un municipio"""
        tokens_municipio = []

        # Navegar al municipio (esto puede activar CAPTCHA)
        print(f"\n  → {batch['corporacion'][:6]} | {batch['departamento'][:25]} | {batch['municipio'][:20]}")

        if not self.seleccionar('selectCorp', batch['corporacion_cod'], 1.5):
            return []
        if not self.seleccionar('selectDepto', batch['departamento_cod'], 1.5):
            return []
        if not self.seleccionar('selectMpio', batch['municipio_cod'], 1):
            return []

        # Procesar cada puesto del municipio (sin cambiar municipio = sin CAPTCHA)
        for p in batch['puestos']:
            # Solo cambiar zona y puesto
            if not self.seleccionar('selectZona', p['zona_cod'], 0.5):
                continue
            if not self.seleccionar('selectPto', p['puesto_cod'], 0.3):
                continue

            # Consultar
            self.consultar()

            # Verificar CAPTCHA
            if self.hay_captcha():
                if not self.resolver_captcha():
                    print("  [!] CAPTCHA no resuelto, saltando...")
                    continue
                self.consultar()
                time.sleep(1)

            # Extraer tokens
            tokens = self.extraer_tokens()

            if tokens:
                # Generar rutas para PDFs
                corp = re.sub(r'[^\w]', '_', p['corporacion'])[:10]
                depto = re.sub(r'[^\w]', '_', p['departamento'])[:25]
                muni = re.sub(r'[^\w]', '_', p['municipio'])[:25]
                puesto_name = re.sub(r'[^\w]', '_', p['puesto'])[:30]

                for i, token in enumerate(tokens):
                    filepath = f"{Config.OUTPUT_DIR}/{corp}/{depto}/{muni}_{puesto_name}_M{i+1:03d}.pdf"
                    tokens_municipio.append({
                        'token': token,
                        'path': filepath,
                        'puesto': p
                    })

                print(f"    ✓ {p['puesto'][:35]}: {len(tokens)} mesas")

            # Pequeña pausa entre puestos (mismo municipio)
            time.sleep(Config.DELAY_BETWEEN_PUESTOS * random.uniform(0.7, 1.3))

        return tokens_municipio

    def cerrar(self):
        if self.driver:
            self.driver.quit()


# ============================================================
# ORQUESTADOR PRINCIPAL
# ============================================================
class E14Downloader:
    """Orquestador principal de descarga"""

    def __init__(self, captcha_api_key=None, remote_port=None, headless=False):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.remote_port = remote_port
        self.headless = headless

        # Componentes
        self.captcha_solver = CaptchaSolver(captcha_api_key) if captcha_api_key else None
        self.extractor = TokenExtractor(self.base_url, self.captcha_solver)
        self.downloader = AsyncDownloader(self.base_url, Config.MAX_CONCURRENT_DOWNLOADS)

        # Estado
        self.municipios_procesados = set()
        self.tokens_extraidos = 0
        self.pdfs_descargados = 0
        self.inicio = None

        # Cargar progreso
        self.cargar_progreso()

    def cargar_progreso(self):
        """Carga progreso previo"""
        if os.path.exists(Config.PROGRESS_FILE):
            with open(Config.PROGRESS_FILE, 'r') as f:
                data = json.load(f)
                self.municipios_procesados = set(data.get('municipios', []))
                self.pdfs_descargados = data.get('pdfs', 0)
            print(f"[OK] Progreso: {len(self.municipios_procesados)} municipios, {self.pdfs_descargados} PDFs")

    def guardar_progreso(self):
        """Guarda progreso"""
        with open(Config.PROGRESS_FILE, 'w') as f:
            json.dump({
                'municipios': list(self.municipios_procesados),
                'pdfs': self.pdfs_descargados,
                'tokens': self.tokens_extraidos,
                'fecha': datetime.now().isoformat()
            }, f, indent=2)

    def mostrar_stats(self):
        """Muestra estadísticas"""
        elapsed = datetime.now() - self.inicio
        rate = self.pdfs_descargados / max(elapsed.total_seconds(), 1)

        print(f"\n{'─'*60}")
        print(f"  📊 ESTADÍSTICAS")
        print(f"  Tiempo: {str(elapsed).split('.')[0]}")
        print(f"  Municipios: {len(self.municipios_procesados)}")
        print(f"  Tokens extraídos: {self.tokens_extraidos}")
        print(f"  PDFs descargados: {self.pdfs_descargados}")
        print(f"  Velocidad: {rate:.1f} PDFs/seg")
        print(f"  CAPTCHAs: {self.extractor.captchas_resueltos}")
        print(f"{'─'*60}\n")

    async def ejecutar(self):
        """Ejecuta la descarga completa"""
        self.inicio = datetime.now()

        # Cargar puestos
        print("[*] Cargando puestos...")
        with open('lista_puestos_congreso_2022.json', 'r') as f:
            puestos = json.load(f)

        # Organizar por municipio
        organizer = WorkOrganizer(puestos)
        batches = organizer.get_work_batches()
        stats = organizer.stats()

        print(f"[OK] {stats['puestos']} puestos en {stats['municipios']} municipios")
        print(f"    Promedio: {stats['promedio_por_municipio']:.1f} puestos/municipio")

        # Filtrar municipios ya procesados
        batches = [b for b in batches
                   if f"{b['corporacion_cod']}|{b['departamento_cod']}|{b['municipio_cod']}"
                   not in self.municipios_procesados]

        print(f"[*] Municipios pendientes: {len(batches)}")

        # Iniciar Chrome
        print("[*] Iniciando Chrome...")
        self.extractor.iniciar_chrome(
            headless=self.headless,
            remote_port=self.remote_port
        )

        # Navegación inicial
        print("[*] Navegando al sitio...")
        self.extractor.navegar_inicial()

        # CAPTCHA inicial
        if self.extractor.hay_captcha():
            print("\n>>> RESUELVE EL CAPTCHA INICIAL <<<")
            if not self.extractor.resolver_captcha(timeout=600):
                print("[!] No se pudo resolver CAPTCHA inicial")
                return

        # Iniciar sesión de descarga
        cookies = self.extractor.get_cookies()
        await self.downloader.init_session(cookies)

        print("\n[*] Iniciando extracción y descarga...")
        print("    (Ctrl+C para pausar)\n")

        try:
            for i, batch in enumerate(batches):
                key = f"{batch['corporacion_cod']}|{batch['departamento_cod']}|{batch['municipio_cod']}"

                # Extraer tokens del municipio
                tokens_data = self.extractor.procesar_municipio(batch)

                if tokens_data:
                    self.tokens_extraidos += len(tokens_data)

                    # Descargar PDFs en paralelo
                    tokens_with_paths = [(t['token'], t['path']) for t in tokens_data]
                    await self.downloader.download_batch(tokens_with_paths)

                    self.pdfs_descargados = self.downloader.downloaded

                # Marcar municipio como procesado
                self.municipios_procesados.add(key)

                # Actualizar cookies periódicamente
                if i % 10 == 0:
                    cookies = self.extractor.get_cookies()
                    await self.downloader.close()
                    await self.downloader.init_session(cookies)

                # Guardar progreso
                if i % 5 == 0:
                    self.guardar_progreso()

                # Stats cada 50 municipios
                if i % 50 == 0 and i > 0:
                    self.mostrar_stats()

                # Pausa entre municipios
                time.sleep(Config.DELAY_BETWEEN_MUNICIPIOS * random.uniform(0.8, 1.2))

        except KeyboardInterrupt:
            print("\n[!] Pausado por usuario")

        finally:
            self.guardar_progreso()
            await self.downloader.close()
            self.extractor.cerrar()
            self.mostrar_stats()


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Descarga optimizada de E-14")
    parser.add_argument("--remote-port", type=int, help="Puerto de Chrome remoto")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana")
    parser.add_argument("--captcha-key", type=str, help="API key de 2Captcha")
    parser.add_argument("--max-concurrent", type=int, default=20, help="Descargas paralelas")
    args = parser.parse_args()

    if args.captcha_key:
        Config.CAPTCHA_API_KEY = args.captcha_key
    elif os.environ.get('CAPTCHA_API_KEY'):
        Config.CAPTCHA_API_KEY = os.environ.get('CAPTCHA_API_KEY')

    if args.max_concurrent:
        Config.MAX_CONCURRENT_DOWNLOADS = args.max_concurrent

    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  E-14 DOWNLOADER OPTIMIZADO                                ║
    ╠════════════════════════════════════════════════════════════╣
    ║  Estrategias:                                              ║
    ║  ✓ Batch por municipio (minimiza CAPTCHAs)                 ║
    ║  ✓ Descarga paralela de PDFs (hasta 20 simultáneas)        ║
    ║  ✓ Persistencia de sesión                                  ║
    ║  ✓ Resolución automática de CAPTCHA (si hay API key)       ║
    ║  ✓ Progreso guardado automáticamente                       ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    downloader = E14Downloader(
        captcha_api_key=Config.CAPTCHA_API_KEY,
        remote_port=args.remote_port,
        headless=args.headless
    )

    asyncio.run(downloader.ejecutar())


if __name__ == "__main__":
    main()
