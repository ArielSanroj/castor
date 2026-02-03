#!/usr/bin/env python3
"""
DESCARGA RESPETUOSA - CONGRESO 2022
- Respeta límites del servidor con rate limiting adaptativo
- Backoff exponencial ante errores
- Delays aleatorios para comportamiento natural
- Límites configurables por hora/día
- Pausas automáticas para evitar sobrecarga
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import re
import requests
from datetime import datetime, timedelta
import argparse
import random
from collections import deque

class RateLimiter:
    """Control de velocidad adaptativo"""

    def __init__(self, max_per_minute=10, max_per_hour=300, max_per_day=5000):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day

        # Historial de requests
        self.requests_minute = deque()
        self.requests_hour = deque()
        self.requests_day = deque()

        # Estado adaptativo
        self.base_delay = 2.0  # segundos base entre requests
        self.current_delay = self.base_delay
        self.max_delay = 60.0  # máximo 1 minuto
        self.consecutive_errors = 0

    def _cleanup_old_requests(self):
        """Limpia requests antiguos de los historiales"""
        now = datetime.now()

        # Limpiar último minuto
        while self.requests_minute and (now - self.requests_minute[0]) > timedelta(minutes=1):
            self.requests_minute.popleft()

        # Limpiar última hora
        while self.requests_hour and (now - self.requests_hour[0]) > timedelta(hours=1):
            self.requests_hour.popleft()

        # Limpiar último día
        while self.requests_day and (now - self.requests_day[0]) > timedelta(days=1):
            self.requests_day.popleft()

    def can_request(self):
        """Verifica si podemos hacer un request"""
        self._cleanup_old_requests()

        if len(self.requests_minute) >= self.max_per_minute:
            return False, "Límite por minuto alcanzado"
        if len(self.requests_hour) >= self.max_per_hour:
            return False, "Límite por hora alcanzado"
        if len(self.requests_day) >= self.max_per_day:
            return False, "Límite diario alcanzado"

        return True, None

    def wait_if_needed(self):
        """Espera si es necesario para respetar límites"""
        can, reason = self.can_request()

        if not can:
            if "minuto" in reason:
                wait_time = 60 - (datetime.now() - self.requests_minute[0]).seconds + 5
                print(f"  [Rate Limit] {reason}. Esperando {wait_time}s...")
                time.sleep(wait_time)
            elif "hora" in reason:
                wait_time = min(300, 3600 - (datetime.now() - self.requests_hour[0]).seconds + 60)
                print(f"  [Rate Limit] {reason}. Esperando {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  [Rate Limit] {reason}. Pausando 1 hora...")
                time.sleep(3600)

    def register_request(self):
        """Registra un request exitoso"""
        now = datetime.now()
        self.requests_minute.append(now)
        self.requests_hour.append(now)
        self.requests_day.append(now)
        self.consecutive_errors = 0

        # Reducir delay gradualmente si todo va bien
        if self.current_delay > self.base_delay:
            self.current_delay = max(self.base_delay, self.current_delay * 0.95)

    def register_error(self):
        """Registra un error - aplica backoff exponencial"""
        self.consecutive_errors += 1
        # Backoff exponencial: 2^n segundos, máximo max_delay
        self.current_delay = min(self.max_delay, self.base_delay * (2 ** self.consecutive_errors))
        print(f"  [Backoff] Error #{self.consecutive_errors}. Nuevo delay: {self.current_delay:.1f}s")

    def get_delay(self):
        """Retorna delay con jitter aleatorio (±30%)"""
        jitter = random.uniform(0.7, 1.3)
        return self.current_delay * jitter

    def get_stats(self):
        """Estadísticas actuales"""
        self._cleanup_old_requests()
        return {
            'ultimo_minuto': len(self.requests_minute),
            'ultima_hora': len(self.requests_hour),
            'ultimo_dia': len(self.requests_day),
            'delay_actual': f"{self.current_delay:.1f}s",
            'errores_consecutivos': self.consecutive_errors
        }


class DescargaRespetuosa:
    def __init__(self, remote_debug_port=None, remote_debug_address="127.0.0.1",
                 max_per_minute=8, max_per_hour=200, max_per_day=3000):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.driver = None
        self.session = requests.Session()
        self.remote_debug_port = remote_debug_port
        self.remote_debug_address = remote_debug_address

        # Rate limiter configurable
        self.rate_limiter = RateLimiter(
            max_per_minute=max_per_minute,
            max_per_hour=max_per_hour,
            max_per_day=max_per_day
        )

        # Estadísticas
        self.pdfs_descargados = 0
        self.puestos_procesados = 0
        self.errores = 0
        self.captchas_resueltos = 0
        self.inicio_sesion = datetime.now()

        # Progreso
        self.procesados = set()
        self.cargar_progreso()

        # Cargar puestos
        print("[*] Cargando puestos...")
        with open('lista_puestos_congreso_2022.json', 'r') as f:
            self.puestos = json.load(f)
        print(f"[OK] {len(self.puestos)} puestos cargados")

        # Carpeta de descargas
        os.makedirs('pdfs_congreso_2022', exist_ok=True)

    def cargar_progreso(self):
        if os.path.exists('progreso_descarga.json'):
            with open('progreso_descarga.json', 'r') as f:
                data = json.load(f)
                self.procesados = set(data.get('procesados', []))
                self.pdfs_descargados = data.get('pdfs', 0)
            print(f"[OK] Progreso cargado: {len(self.procesados)} puestos, {self.pdfs_descargados} PDFs")

    def guardar_progreso(self):
        with open('progreso_descarga.json', 'w') as f:
            json.dump({
                'procesados': list(self.procesados),
                'pdfs': self.pdfs_descargados,
                'fecha': datetime.now().isoformat(),
                'stats': self.rate_limiter.get_stats()
            }, f, indent=2)

    def iniciar_chrome(self):
        print("[*] Iniciando Chrome...")
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1400,900')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        prefs = {
            'download.default_directory': os.path.abspath('pdfs_congreso_2022'),
            'download.prompt_for_download': False,
        }
        options.add_experimental_option('prefs', prefs)

        if self.remote_debug_port:
            addr = f"{self.remote_debug_address}:{self.remote_debug_port}"
            options.add_experimental_option("debuggerAddress", addr)
            print(f"[*] Conectando a Chrome remoto en {addr}...")
            self.driver = webdriver.Chrome(options=options)
            print("[OK] Conectado a Chrome remoto")
        else:
            self.driver = webdriver.Chrome(options=options)
            print("[OK] Chrome iniciado")
        return True

    def sincronizar_cookies(self):
        """Copia cookies de Selenium a requests"""
        self.session.cookies.clear()
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'])

    def hay_captcha(self):
        """Detecta si hay CAPTCHA pendiente"""
        try:
            html = self.driver.page_source.lower()
            if 'captcha' in html:
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

    def esperar_captcha(self, timeout=300):
        """Espera que el usuario resuelva CAPTCHA"""
        print("\n" + "!"*55)
        print("  ⚠️  CAPTCHA DETECTADO")
        print("  Resuélvelo manualmente en el navegador...")
        print(f"  (Esperando máximo {timeout}s)")
        print("!"*55)

        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                if resp.get_attribute('value'):
                    print("[OK] CAPTCHA resuelto!")
                    self.captchas_resueltos += 1
                    self.sincronizar_cookies()
                    # Pausa adicional post-captcha
                    time.sleep(random.uniform(3, 5))
                    return True
            except:
                pass

            try:
                html = self.driver.page_source
                if 'descargarE14' in html:
                    print("[OK] Resultados detectados!")
                    self.sincronizar_cookies()
                    return True
            except:
                pass

            time.sleep(2)

        print("[!] Timeout esperando CAPTCHA")
        return False

    def seleccionar(self, select_id, valor, espera_base=1.5):
        """Selecciona valor en dropdown con espera variable"""
        try:
            elem = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            time.sleep(random.uniform(0.3, 0.7))  # Jitter antes
            Select(elem).select_by_value(valor)
            # Espera con jitter
            time.sleep(espera_base * random.uniform(0.8, 1.4))
            return True
        except Exception as e:
            return False

    def consultar(self):
        """Clic en consultar con delay"""
        try:
            # Pausa antes de clic (simula lectura humana)
            time.sleep(random.uniform(0.5, 1.5))
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(random.uniform(2.5, 4.0))
            return True
        except:
            return False

    def extraer_y_descargar(self, info_puesto):
        """Extrae tokens y descarga PDFs respetando límites"""
        html = self.driver.page_source
        tokens = re.findall(r"descargarE14\(['\"]([^'\"]+)['\"]\)", html)

        if not tokens:
            return 0

        descargados = 0

        # Crear estructura de carpetas
        corp = re.sub(r'[^\w]', '_', info_puesto['corporacion'])[:10]
        depto = re.sub(r'[^\w]', '_', info_puesto['departamento'])[:20]
        muni = re.sub(r'[^\w]', '_', info_puesto['municipio'])[:20]
        puesto = re.sub(r'[^\w]', '_', info_puesto['puesto'])[:25]

        carpeta = f"pdfs_congreso_2022/{corp}/{depto}"
        os.makedirs(carpeta, exist_ok=True)

        for i, token in enumerate(tokens):
            archivo = f"{carpeta}/{muni}_{puesto}_M{i+1:03d}.pdf"

            if os.path.exists(archivo):
                descargados += 1
                continue

            # Verificar rate limit antes de cada descarga
            self.rate_limiter.wait_if_needed()

            try:
                # Delay adaptativo entre descargas
                delay = self.rate_limiter.get_delay()
                time.sleep(delay)

                # Descargar PDF
                r = self.session.post(
                    f"{self.base_url}/descargae14",
                    data={'token': token},
                    timeout=30
                )

                if r.content[:4] == b'%PDF':
                    with open(archivo, 'wb') as f:
                        f.write(r.content)
                    descargados += 1
                    self.rate_limiter.register_request()
                else:
                    # Posible CAPTCHA o error
                    if 'captcha' in r.text.lower():
                        self.rate_limiter.register_error()
                        self.driver.refresh()
                        time.sleep(3)
                        if self.esperar_captcha(timeout=300):
                            self.sincronizar_cookies()
                            # Reintentar con delay mayor
                            time.sleep(self.rate_limiter.get_delay() * 2)
                            r = self.session.post(
                                f"{self.base_url}/descargae14",
                                data={'token': token},
                                timeout=30
                            )
                            if r.content[:4] == b'%PDF':
                                with open(archivo, 'wb') as f:
                                    f.write(r.content)
                                descargados += 1
                                self.rate_limiter.register_request()
                    else:
                        self.rate_limiter.register_error()

            except requests.exceptions.Timeout:
                print(f"  [Timeout] Mesa {i+1}")
                self.rate_limiter.register_error()
            except Exception as e:
                self.errores += 1
                self.rate_limiter.register_error()

        return descargados

    def procesar_puesto(self, p):
        """Procesa un puesto completo"""
        key = f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"

        if key in self.procesados:
            return 0

        # Verificar rate limit antes de procesar
        self.rate_limiter.wait_if_needed()

        try:
            # Seleccionar con pausas variables
            if not self.seleccionar('selectCorp', p['corporacion_cod'], 2):
                return 0
            if not self.seleccionar('selectDepto', p['departamento_cod'], 2):
                return 0
            if not self.seleccionar('selectMpio', p['municipio_cod'], 1.5):
                return 0
            if not self.seleccionar('selectZona', p['zona_cod'], 1.5):
                return 0
            if not self.seleccionar('selectPto', p['puesto_cod'], 1):
                return 0

            # Consultar
            self.consultar()

            # Verificar CAPTCHA
            if self.hay_captcha():
                if not self.esperar_captcha(timeout=300):
                    self.rate_limiter.register_error()
                    return 0
                self.consultar()
                time.sleep(random.uniform(2, 3))

            # Sincronizar cookies
            self.sincronizar_cookies()

            # Extraer y descargar
            n = self.extraer_y_descargar(p)

            self.procesados.add(key)
            self.puestos_procesados += 1
            self.pdfs_descargados += n

            return n

        except Exception as e:
            self.errores += 1
            self.rate_limiter.register_error()
            return 0

    def mostrar_estadisticas(self):
        """Muestra estadísticas actuales"""
        elapsed = datetime.now() - self.inicio_sesion
        stats = self.rate_limiter.get_stats()

        print(f"\n{'─'*55}")
        print(f"  📊 ESTADÍSTICAS")
        print(f"  Tiempo: {str(elapsed).split('.')[0]}")
        print(f"  Puestos: {self.puestos_procesados} | PDFs: {self.pdfs_descargados}")
        print(f"  CAPTCHAs: {self.captchas_resueltos} | Errores: {self.errores}")
        print(f"  Rate: {stats['ultimo_minuto']}/min, {stats['ultima_hora']}/hora")
        print(f"  Delay actual: {stats['delay_actual']}")
        print(f"{'─'*55}\n")

    def ejecutar(self):
        """Ejecuta la descarga respetando límites"""
        if not self.iniciar_chrome():
            return

        try:
            print(f"[*] Navegando a {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(random.uniform(3, 5))

            # Configuración inicial
            print("\n" + "="*55)
            print("  CONFIGURACIÓN INICIAL")
            print("="*55)

            primer_puesto = self.puestos[0]
            time.sleep(random.uniform(2, 3))

            self.seleccionar('selectCorp', primer_puesto['corporacion_cod'], 2)
            self.seleccionar('selectDepto', primer_puesto['departamento_cod'], 2)
            self.seleccionar('selectMpio', primer_puesto['municipio_cod'], 1.5)
            self.seleccionar('selectZona', primer_puesto['zona_cod'], 1.5)
            self.seleccionar('selectPto', primer_puesto['puesto_cod'], 1)

            print("  Consultando...")
            self.consultar()

            if self.hay_captcha():
                print("\n  >>> RESUELVE EL CAPTCHA INICIAL <<<")
                self.esperar_captcha(timeout=600)
            else:
                print("[OK] Sin CAPTCHA inicial")

            print("="*55)

            self.sincronizar_cookies()
            print("[OK] Sesión sincronizada")

            # Filtrar pendientes
            pendientes = [p for p in self.puestos
                         if f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"
                         not in self.procesados]

            print(f"\n[*] Puestos pendientes: {len(pendientes)}")
            print(f"[*] PDFs descargados: {self.pdfs_descargados}")
            print(f"[*] Rate limits: {self.rate_limiter.max_per_minute}/min, "
                  f"{self.rate_limiter.max_per_hour}/hora, "
                  f"{self.rate_limiter.max_per_day}/día")
            print("\n[*] Iniciando descarga... (Ctrl+C para pausar)\n")

            ultimo_depto = ""

            for i, p in enumerate(pendientes):
                # Mostrar progreso cada departamento
                if p['departamento'] != ultimo_depto:
                    print(f"\n>>> {p['corporacion'][:8]} | {p['departamento'][:30]}")
                    ultimo_depto = p['departamento']
                    self.guardar_progreso()

                    # Mostrar stats cada 10 departamentos
                    if self.puestos_procesados > 0 and self.puestos_procesados % 100 == 0:
                        self.mostrar_estadisticas()

                n = self.procesar_puesto(p)

                if n > 0:
                    print(f"  ✓ {p['puesto'][:35]}: {n} PDFs")

                # Delay entre puestos con jitter
                time.sleep(self.rate_limiter.get_delay())

                # Guardar cada 30 puestos
                if self.puestos_procesados % 30 == 0:
                    self.guardar_progreso()

                # Pausa larga cada 500 puestos (descanso servidor)
                if self.puestos_procesados > 0 and self.puestos_procesados % 500 == 0:
                    pausa = random.uniform(60, 120)
                    print(f"\n  [Pausa programada] Descansando {pausa:.0f}s...")
                    time.sleep(pausa)

            self.guardar_progreso()

        except KeyboardInterrupt:
            print("\n\n[!] Pausado por usuario")
            self.guardar_progreso()
            print(f"[OK] Progreso guardado")

        finally:
            self.mostrar_estadisticas()
            print(f"\n{'='*55}")
            print(f"  RESUMEN FINAL")
            print(f"  Puestos procesados: {self.puestos_procesados}")
            print(f"  PDFs descargados: {self.pdfs_descargados}")
            print(f"  CAPTCHAs resueltos: {self.captchas_resueltos}")
            print(f"  Errores: {self.errores}")
            print(f"{'='*55}")

            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga respetuosa de E14")
    parser.add_argument("--remote-debugging-port", type=int, default=None,
                       help="Puerto de Chrome remoto")
    parser.add_argument("--remote-debugging-address", type=str, default="127.0.0.1",
                       help="Dirección de Chrome remoto")
    parser.add_argument("--max-per-minute", type=int, default=8,
                       help="Máximo requests por minuto (default: 8)")
    parser.add_argument("--max-per-hour", type=int, default=200,
                       help="Máximo requests por hora (default: 200)")
    parser.add_argument("--max-per-day", type=int, default=3000,
                       help="Máximo requests por día (default: 3000)")
    args = parser.parse_args()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║  DESCARGA RESPETUOSA - E14 CONGRESO 2022                  ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  ✓ Rate limiting adaptativo                               ║
    ║  ✓ Backoff exponencial ante errores                       ║
    ║  ✓ Delays aleatorios (comportamiento natural)             ║
    ║  ✓ Pausas programadas cada 500 puestos                    ║
    ║  ✓ Guarda progreso automáticamente                        ║
    ║  ✓ Continúa donde quedaste (Ctrl+C para pausar)           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    descargador = DescargaRespetuosa(
        remote_debug_port=args.remote_debugging_port,
        remote_debug_address=args.remote_debugging_address,
        max_per_minute=args.max_per_minute,
        max_per_hour=args.max_per_hour,
        max_per_day=args.max_per_day
    )
    descargador.ejecutar()
