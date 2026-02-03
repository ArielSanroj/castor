#!/usr/bin/env python3
"""
DESCARGA CON SELENIUM PURO
- Usa Selenium para TODO (navegar + descargar)
- No usa requests (evita problemas de sesión)
- Hace click directo en botones de descarga
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
import sys
from datetime import datetime

class DescargaSeleniumPuro:
    def __init__(self):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.driver = None

        # Carpeta de descargas
        self.carpeta_descargas = os.path.abspath('pdfs_congreso_2022')
        os.makedirs(self.carpeta_descargas, exist_ok=True)

        # Estadísticas
        self.pdfs_descargados = 0
        self.puestos_procesados = 0

        # Progreso
        self.procesados = set()
        self.cargar_progreso()

        # Cargar puestos
        print("[*] Cargando puestos...")
        with open('lista_puestos_congreso_2022.json', 'r') as f:
            self.puestos = json.load(f)
        print(f"[OK] {len(self.puestos)} puestos")

    def cargar_progreso(self):
        if os.path.exists('progreso_selenium.json'):
            with open('progreso_selenium.json', 'r') as f:
                data = json.load(f)
                self.procesados = set(data.get('procesados', []))
                self.pdfs_descargados = data.get('pdfs', 0)
            print(f"[OK] Progreso: {len(self.procesados)} puestos, {self.pdfs_descargados} PDFs")

    def guardar_progreso(self):
        with open('progreso_selenium.json', 'w') as f:
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

        # Configurar carpeta de descargas
        prefs = {
            'download.default_directory': self.carpeta_descargas,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugins.always_open_pdf_externally': True,  # No abrir PDF en Chrome
            'safebrowsing.enabled': True
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        self.driver = webdriver.Chrome(options=options)
        print("[OK] Chrome listo")
        print(f"[OK] Descargas irán a: {self.carpeta_descargas}")
        return True

    def seleccionar(self, select_id, valor, espera=1.5):
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            time.sleep(0.3)
            Select(elem).select_by_value(valor)
            time.sleep(espera)
            return True
        except:
            return False

    def consultar(self):
        try:
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(3)
            return True
        except:
            return False

    def hay_captcha_pendiente(self):
        """Verifica si hay CAPTCHA sin resolver"""
        try:
            html = self.driver.page_source
            if 'g-recaptcha' in html:
                # Ver si ya está resuelto
                try:
                    resp = self.driver.find_element(By.ID, 'g-recaptcha-response')
                    if resp.get_attribute('value'):
                        return False
                except:
                    pass

                # Ver si hay mesas visibles (significa que pasó)
                if 'descargarE14' in html:
                    return False

                return True
        except:
            pass
        return False

    def esperar_captcha(self, timeout=300):
        """Espera que el usuario resuelva CAPTCHA"""
        print("\n" + "!"*50)
        print("  CAPTCHA - Resuélvelo en Chrome")
        print("!"*50, flush=True)

        inicio = time.time()
        while time.time() - inicio < timeout:
            # Verificar si hay mesas visibles
            if 'descargarE14' in self.driver.page_source:
                print("[OK] CAPTCHA resuelto!", flush=True)
                return True
            time.sleep(2)

        print("[!] Timeout CAPTCHA", flush=True)
        return False

    def contar_archivos_descarga(self):
        """Cuenta archivos en carpeta de descargas"""
        return len([f for f in os.listdir(self.carpeta_descargas)
                   if f.endswith('.pdf') and not f.endswith('.crdownload')])

    def descargar_mesas_puesto(self):
        """
        Hace click en cada botón de mesa para descargar
        Retorna cantidad de PDFs descargados
        """
        descargados = 0

        try:
            # Encontrar todos los botones de descarga
            botones = self.driver.find_elements(By.XPATH,
                "//button[contains(@onclick, 'descargarE14')] | //a[contains(@onclick, 'descargarE14')]"
            )

            if not botones:
                # Intentar otro selector
                botones = self.driver.find_elements(By.XPATH,
                    "//*[contains(@onclick, 'descargar')]"
                )

            print(f"    Mesas encontradas: {len(botones)}", flush=True)

            archivos_antes = self.contar_archivos_descarga()

            for i, btn in enumerate(botones):
                try:
                    # Scroll al botón
                    self.driver.execute_script("arguments[0].scrollIntoView();", btn)
                    time.sleep(0.3)

                    # Click para descargar
                    btn.click()
                    time.sleep(1)  # Esperar que inicie descarga

                except Exception as e:
                    continue

            # Esperar que terminen las descargas
            time.sleep(2)

            archivos_despues = self.contar_archivos_descarga()
            descargados = archivos_despues - archivos_antes

        except Exception as e:
            print(f"    Error: {e}", flush=True)

        return descargados

    def procesar_puesto(self, p):
        """Procesa un puesto: navega y descarga mesas"""
        key = f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"

        if key in self.procesados:
            return 0

        try:
            # Seleccionar valores
            self.seleccionar('selectCorp', p['corporacion_cod'], 1.5)
            self.seleccionar('selectDepto', p['departamento_cod'], 1.5)
            self.seleccionar('selectMpio', p['municipio_cod'], 1)
            self.seleccionar('selectZona', p['zona_cod'], 1)
            self.seleccionar('selectPto', p['puesto_cod'], 0.8)

            # Consultar
            self.consultar()

            # Si hay CAPTCHA, esperar
            if self.hay_captcha_pendiente():
                if not self.esperar_captcha():
                    return 0

            # Descargar mesas
            n = self.descargar_mesas_puesto()

            self.procesados.add(key)
            self.puestos_procesados += 1
            self.pdfs_descargados += n

            return n

        except Exception as e:
            return 0

    def ejecutar(self):
        """Ejecuta descarga completa"""
        if not self.iniciar_chrome():
            return

        try:
            # Navegar al sitio
            print(f"[*] Navegando a {self.base_url}", flush=True)
            self.driver.get(self.base_url)
            time.sleep(3)

            # Configuración inicial
            print("\n" + "="*55)
            print("  CONFIGURACIÓN INICIAL")
            print("="*55)
            print("  Seleccionando primer puesto...", flush=True)

            p = self.puestos[0]
            self.seleccionar('selectCorp', p['corporacion_cod'], 2)
            self.seleccionar('selectDepto', p['departamento_cod'], 2)
            self.seleccionar('selectMpio', p['municipio_cod'], 1.5)
            self.seleccionar('selectZona', p['zona_cod'], 1.5)
            self.seleccionar('selectPto', p['puesto_cod'], 1)

            print("  Consultando...", flush=True)
            self.consultar()

            # CAPTCHA inicial
            if self.hay_captcha_pendiente():
                print("\n  >>> RESUELVE EL CAPTCHA EN CHROME <<<", flush=True)
                self.esperar_captcha(600)

            print("="*55, flush=True)

            # Procesar puestos
            pendientes = [p for p in self.puestos
                         if f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"
                         not in self.procesados]

            print(f"\n[*] Puestos pendientes: {len(pendientes)}", flush=True)
            print(f"[*] PDFs descargados: {self.pdfs_descargados}", flush=True)
            print("\n[*] Iniciando... (Ctrl+C para pausar)\n", flush=True)

            ultimo_depto = ""

            for i, p in enumerate(pendientes):
                if p['departamento'] != ultimo_depto:
                    print(f"\n>>> {p['corporacion'][:8]} | {p['departamento'][:30]}", flush=True)
                    ultimo_depto = p['departamento']
                    self.guardar_progreso()

                n = self.procesar_puesto(p)

                if n > 0:
                    print(f"  {p['puesto'][:35]}: {n} PDFs", flush=True)
                else:
                    sys.stdout.write('.')
                    sys.stdout.flush()

                time.sleep(1)

            self.guardar_progreso()

        except KeyboardInterrupt:
            print("\n\n[!] Pausado", flush=True)
            self.guardar_progreso()

        finally:
            print(f"\n{'='*55}")
            print(f"  Puestos: {self.puestos_procesados}")
            print(f"  PDFs: {self.pdfs_descargados}")
            print(f"  Carpeta: {self.carpeta_descargas}")
            print(f"{'='*55}")

            self.driver.quit()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║  DESCARGA SELENIUM PURO - CONGRESO 2022               ║
    ║  Hace click directo en botones de descarga            ║
    ╚═══════════════════════════════════════════════════════╝
    """, flush=True)

    d = DescargaSeleniumPuro()
    d.ejecutar()
