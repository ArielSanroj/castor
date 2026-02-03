#!/usr/bin/env python3
"""
DESCARGA DIRECTA - CONGRESO 2022
- Más lento para evitar CAPTCHAs frecuentes
- Descarga PDFs inmediatamente con la sesión activa
- Pausa cuando detecta CAPTCHA
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
from datetime import datetime
import argparse

class DescargaDirecta:
    def __init__(self, remote_debug_port=None, remote_debug_address="127.0.0.1"):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.driver = None
        self.session = requests.Session()
        self.remote_debug_port = remote_debug_port
        self.remote_debug_address = remote_debug_address

        # Estadísticas
        self.pdfs_descargados = 0
        self.puestos_procesados = 0
        self.errores = 0

        # Progreso
        self.procesados = set()
        self.cargar_progreso()

        # Cargar puestos
        print("[*] Cargando puestos...")
        with open('lista_puestos_congreso_2022.json', 'r') as f:
            self.puestos = json.load(f)
        print(f"[OK] {len(self.puestos)} puestos")

        # Carpeta de descargas
        os.makedirs('pdfs_congreso_2022', exist_ok=True)

    def cargar_progreso(self):
        if os.path.exists('progreso_descarga.json'):
            with open('progreso_descarga.json', 'r') as f:
                data = json.load(f)
                self.procesados = set(data.get('procesados', []))
                self.pdfs_descargados = data.get('pdfs', 0)
            print(f"[OK] Progreso: {len(self.procesados)} puestos, {self.pdfs_descargados} PDFs")

    def guardar_progreso(self):
        with open('progreso_descarga.json', 'w') as f:
            json.dump({
                'procesados': list(self.procesados),
                'pdfs': self.pdfs_descargados,
                'fecha': datetime.now().isoformat()
            }, f)

    def iniciar_chrome(self):
        print("[*] Iniciando Chrome...")
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1400,900')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        # Carpeta de descargas del navegador
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
            print("[OK] Chrome remoto listo")
        else:
            self.driver = webdriver.Chrome(options=options)
            print("[OK] Chrome listo")
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
                # Verificar si ya está resuelto
                try:
                    resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                    if resp.get_attribute('value'):
                        return False  # Ya resuelto
                except:
                    pass
                return True
        except:
            pass
        return False

    def esperar_captcha(self, timeout=300):
        """Espera automáticamente que el usuario resuelva CAPTCHA (polling)"""
        print("\n" + "!"*50)
        print("  CAPTCHA DETECTADO")
        print("  Resuelvelo en el navegador...")
        print(f"  (Esperando máximo {timeout}s)")
        print("!"*50)

        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                # Verificar si CAPTCHA fue resuelto
                resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                if resp.get_attribute('value'):
                    print("[OK] CAPTCHA resuelto!")
                    self.sincronizar_cookies()
                    return True
            except:
                pass

            # Verificar si ya hay resultados (mesas visibles)
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
        self.sincronizar_cookies()
        return False

    def seleccionar(self, select_id, valor, espera=1.5):
        """Selecciona valor en dropdown con espera"""
        try:
            elem = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            # Esperar a que tenga opciones
            time.sleep(0.5)
            Select(elem).select_by_value(valor)
            time.sleep(espera)
            return True
        except Exception as e:
            return False

    def consultar(self):
        """Clic en consultar"""
        try:
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(3)  # Esperar más
            return True
        except:
            return False

    def extraer_y_descargar(self, info_puesto):
        """Extrae tokens de mesas y descarga PDFs inmediatamente"""
        html = self.driver.page_source

        # Buscar tokens
        tokens = re.findall(r"descargarE14\(['\"]([^'\"]+)['\"]\)", html)

        if not tokens:
            return 0

        descargados = 0

        # Crear carpeta para este puesto
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

            try:
                # Descargar usando sesión con cookies
                r = self.session.post(
                    f"{self.base_url}/descargae14",
                    data={'token': token},
                    timeout=30
                )

                if r.content[:4] == b'%PDF':
                    with open(archivo, 'wb') as f:
                        f.write(r.content)
                    descargados += 1
                else:
                    # Puede ser CAPTCHA
                    if 'captcha' in r.text.lower():
                        # Recargar página para mostrar CAPTCHA en navegador
                        self.driver.refresh()
                        time.sleep(2)
                        if self.esperar_captcha(timeout=300):
                            # Reintentar
                            self.sincronizar_cookies()
                            r = self.session.post(
                                f"{self.base_url}/descargae14",
                                data={'token': token},
                                timeout=30
                            )
                            if r.content[:4] == b'%PDF':
                                with open(archivo, 'wb') as f:
                                    f.write(r.content)
                                descargados += 1

            except Exception as e:
                self.errores += 1

            time.sleep(0.3)  # Pausa entre descargas

        return descargados

    def procesar_puesto(self, p):
        """Procesa un puesto completo"""
        key = f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"

        if key in self.procesados:
            return 0

        try:
            # Seleccionar con pausas largas
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
                if self.esperar_captcha(timeout=300):
                    self.consultar()
                    time.sleep(2)

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
            return 0

    def ejecutar(self):
        """Ejecuta la descarga completa"""
        if not self.iniciar_chrome():
            return

        try:
            # Ir al sitio
            print(f"[*] Navegando a {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)

            # Configuración inicial automática
            print("\n" + "="*55)
            print("  CONFIGURACION INICIAL (AUTOMATICA)")
            print("="*55)
            print("  Seleccionando primer puesto para activar sesión...")

            # Seleccionar primer puesto disponible para obtener sesión
            primer_puesto = self.puestos[0]
            time.sleep(2)

            self.seleccionar('selectCorp', primer_puesto['corporacion_cod'], 2)
            self.seleccionar('selectDepto', primer_puesto['departamento_cod'], 2)
            self.seleccionar('selectMpio', primer_puesto['municipio_cod'], 1.5)
            self.seleccionar('selectZona', primer_puesto['zona_cod'], 1.5)
            self.seleccionar('selectPto', primer_puesto['puesto_cod'], 1)

            print("  Consultando...")
            self.consultar()

            # Esperar CAPTCHA inicial
            if self.hay_captcha():
                print("\n  >>> RESUELVE EL CAPTCHA EN EL NAVEGADOR <<<")
                self.esperar_captcha(timeout=600)
            else:
                print("[OK] Sin CAPTCHA inicial")

            print("="*55)

            # Sincronizar sesión
            self.sincronizar_cookies()
            print("[OK] Sesion sincronizada")

            # Filtrar puestos pendientes
            pendientes = [p for p in self.puestos
                         if f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"
                         not in self.procesados]

            print(f"\n[*] Puestos pendientes: {len(pendientes)}")
            print(f"[*] PDFs ya descargados: {self.pdfs_descargados}")
            print("\n[*] Iniciando... (Ctrl+C para pausar)\n")

            ultimo_depto = ""

            for i, p in enumerate(pendientes):
                # Mostrar progreso cada cambio de departamento
                if p['departamento'] != ultimo_depto:
                    print(f"\n>>> {p['corporacion'][:8]} | {p['departamento'][:30]}")
                    print(f"    Puestos: {self.puestos_procesados} | PDFs: {self.pdfs_descargados}")
                    ultimo_depto = p['departamento']
                    self.guardar_progreso()

                n = self.procesar_puesto(p)

                if n > 0:
                    print(f"  {p['puesto'][:35]}: {n} PDFs")

                # Pausa entre puestos (evitar CAPTCHA)
                time.sleep(1.5)

                # Guardar cada 50 puestos
                if self.puestos_procesados % 50 == 0:
                    self.guardar_progreso()

            self.guardar_progreso()

        except KeyboardInterrupt:
            print("\n\n[!] Pausado por usuario")
            self.guardar_progreso()
            print(f"[OK] Progreso guardado: {self.pdfs_descargados} PDFs")

        finally:
            print(f"\n{'='*55}")
            print(f"  RESUMEN")
            print(f"  Puestos procesados: {self.puestos_procesados}")
            print(f"  PDFs descargados: {self.pdfs_descargados}")
            print(f"  Errores: {self.errores}")
            print(f"{'='*55}")

            self.driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--remote-debugging-port",
        type=int,
        default=None,
        help="Conecta a un Chrome ya abierto con --remote-debugging-port",
    )
    parser.add_argument(
        "--remote-debugging-address",
        type=str,
        default="127.0.0.1",
        help="Direccion de Chrome remoto (por defecto 127.0.0.1)",
    )
    args = parser.parse_args()

    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║  DESCARGA DIRECTA - CONGRESO 2022 (NO INTERACTIVO)    ║
    ║  SENADO + CAMARA (~210,000 PDFs)                      ║
    ╠═══════════════════════════════════════════════════════╣
    ║  - Modo automático (sin input manual)                 ║
    ║  - Detecta CAPTCHA y espera que lo resuelvas          ║
    ║  - Guarda progreso (puedes pausar con Ctrl+C)         ║
    ║  - Continua donde quedaste                            ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    descargador = DescargaDirecta(
        remote_debug_port=args.remote_debugging_port,
        remote_debug_address=args.remote_debugging_address,
    )
    descargador.ejecutar()
