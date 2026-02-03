#!/usr/bin/env python3
"""
SELENIUM EXTRACTOR - CONGRESO 2022
Extrae tokens de mesas y descarga PDFs
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import json
import os
import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pickle

class SeleniumCongreso2022:
    def __init__(self):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.driver = None
        self.tokens_extraidos = []
        self.session = requests.Session()

        # Cargar puestos
        self.puestos = []
        if os.path.exists('lista_puestos_congreso_2022.json'):
            with open('lista_puestos_congreso_2022.json', 'r') as f:
                self.puestos = json.load(f)

        # Progreso
        self.procesados = set()
        self.cargar_progreso()

    def cargar_progreso(self):
        if os.path.exists('progreso_tokens.json'):
            with open('progreso_tokens.json', 'r') as f:
                data = json.load(f)
                self.tokens_extraidos = data.get('tokens', [])
                self.procesados = set(data.get('procesados', []))
            print(f"[OK] Progreso cargado: {len(self.tokens_extraidos)} tokens, {len(self.procesados)} puestos procesados")

    def guardar_progreso(self):
        with open('progreso_tokens.json', 'w') as f:
            json.dump({
                'tokens': self.tokens_extraidos,
                'procesados': list(self.procesados),
                'fecha': datetime.now().isoformat()
            }, f)

        # También guardar tokens por separado
        with open('tokens_mesas_congreso.json', 'w') as f:
            json.dump(self.tokens_extraidos, f, indent=2)

    def iniciar_navegador(self):
        """Inicia Chrome"""
        print("[*] Iniciando navegador...")

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1400,900')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            print("[OK] Navegador iniciado")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo iniciar Chrome: {e}")
            print("\nInstala ChromeDriver:")
            print("  brew install --cask chromedriver")
            print("  xattr -d com.apple.quarantine /usr/local/bin/chromedriver")
            return False

    def navegar_sitio(self):
        """Navega al sitio"""
        self.driver.get(self.base_url)
        time.sleep(3)
        print(f"[OK] Navegando a {self.base_url}")

    def esperar_captcha(self):
        """Espera que el usuario resuelva el CAPTCHA"""
        print("\n" + "="*60)
        print("  RESUELVE EL CAPTCHA EN EL NAVEGADOR")
        print("="*60)
        print("""
  1. En el navegador selecciona:
     - Corporacion: SENADO
     - Departamento: cualquiera (ej: ANTIOQUIA)
     - Municipio: cualquiera
     - Zona: cualquiera
     - Puesto: cualquiera

  2. Haz clic en CONSULTAR

  3. Resuelve el CAPTCHA si aparece

  4. Cuando veas las MESAS, vuelve aqui
        """)
        print("="*60)

        input("\n>>> Presiona ENTER cuando hayas resuelto el CAPTCHA: ")

        # Guardar cookies
        self.guardar_cookies()
        print("[OK] Sesion guardada")

    def guardar_cookies(self):
        """Guarda cookies para requests"""
        cookies = self.driver.get_cookies()
        with open('cookies_congreso.pkl', 'wb') as f:
            pickle.dump(cookies, f)

        # Para requests
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])

    def seleccionar_valor(self, select_id, valor, esperar=1):
        """Selecciona un valor en un dropdown"""
        try:
            select_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            select = Select(select_elem)
            select.select_by_value(valor)
            time.sleep(esperar)
            return True
        except Exception as e:
            return False

    def consultar_puesto(self):
        """Hace clic en consultar"""
        try:
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(2)
            return True
        except:
            return False

    def extraer_tokens_pagina(self):
        """Extrae tokens de mesas de la página actual"""
        tokens = []

        try:
            # Esperar a que cargue la tabla de mesas
            time.sleep(1)

            # Buscar botones de mesa
            html = self.driver.page_source

            # Buscar pattern: descargarE14('TOKEN')
            matches = re.findall(r"descargarE14\(['\"]([^'\"]+)['\"]\)", html)

            for token in matches:
                if token and len(token) > 20:
                    tokens.append(token)

            # También buscar en onclick
            if not tokens:
                botones = self.driver.find_elements(By.XPATH, "//*[contains(@onclick, 'descargar')]")
                for btn in botones:
                    onclick = btn.get_attribute('onclick') or ''
                    match = re.search(r"['\"]([a-zA-Z0-9+/=]{50,})['\"]", onclick)
                    if match:
                        tokens.append(match.group(1))

        except Exception as e:
            print(f"    Error extrayendo tokens: {e}")

        return tokens

    def procesar_puesto(self, puesto):
        """Procesa un puesto: navega y extrae tokens"""
        key = f"{puesto['corporacion_cod']}_{puesto['departamento_cod']}_{puesto['municipio_cod']}_{puesto['zona_cod']}_{puesto['puesto_cod']}"

        if key in self.procesados:
            return 0

        try:
            # Seleccionar corporación
            corp_val = puesto['corporacion_cod']  # ej: SEN_1
            self.seleccionar_valor('selectCorp', corp_val, esperar=1)

            # Seleccionar departamento
            self.seleccionar_valor('selectDepto', puesto['departamento_cod'], esperar=1)

            # Seleccionar municipio
            self.seleccionar_valor('selectMpio', puesto['municipio_cod'], esperar=0.5)

            # Seleccionar zona
            self.seleccionar_valor('selectZona', puesto['zona_cod'], esperar=0.5)

            # Seleccionar puesto
            self.seleccionar_valor('selectPto', puesto['puesto_cod'], esperar=0.5)

            # Consultar
            self.consultar_puesto()
            time.sleep(1.5)

            # Verificar CAPTCHA
            if 'captcha' in self.driver.page_source.lower() and 'g-recaptcha-response' in self.driver.page_source:
                # Puede que necesite resolver CAPTCHA de nuevo
                response_elem = self.driver.find_element(By.ID, 'g-recaptcha-response')
                if not response_elem.get_attribute('value'):
                    print("\n[!] CAPTCHA requerido - resuelve en el navegador")
                    input(">>> Presiona ENTER cuando lo resuelvas: ")
                    self.consultar_puesto()
                    time.sleep(1.5)

            # Extraer tokens
            tokens = self.extraer_tokens_pagina()

            for i, token in enumerate(tokens):
                self.tokens_extraidos.append({
                    'token': token,
                    'corporacion': puesto['corporacion'],
                    'departamento': puesto['departamento'],
                    'municipio': puesto['municipio'],
                    'zona': puesto['zona'],
                    'puesto': puesto['puesto'],
                    'mesa': f"Mesa_{i+1:03d}"
                })

            self.procesados.add(key)
            return len(tokens)

        except Exception as e:
            print(f"    Error: {e}")
            return 0

    def extraer_todos_tokens(self):
        """Extrae tokens de todos los puestos"""
        print(f"\n[*] Iniciando extraccion de {len(self.puestos)} puestos...")
        print(f"    Ya procesados: {len(self.procesados)}")
        print(f"    Pendientes: {len(self.puestos) - len(self.procesados)}")

        # Filtrar solo SENADO y CAMARA
        puestos_filtrados = [p for p in self.puestos if p['corporacion_cod'] in ['SEN_1', 'CAM_2']]

        total_tokens = len(self.tokens_extraidos)
        errores_consecutivos = 0

        for i, puesto in enumerate(puestos_filtrados):
            key = f"{puesto['corporacion_cod']}_{puesto['departamento_cod']}_{puesto['municipio_cod']}_{puesto['zona_cod']}_{puesto['puesto_cod']}"

            if key in self.procesados:
                continue

            # Progreso
            if i % 50 == 0:
                print(f"\n[{i}/{len(puestos_filtrados)}] Tokens: {len(self.tokens_extraidos)} | {puesto['departamento'][:20]}")
                self.guardar_progreso()

            try:
                n_tokens = self.procesar_puesto(puesto)

                if n_tokens > 0:
                    errores_consecutivos = 0
                    print(f"  {puesto['puesto'][:40]}: {n_tokens} mesas")
                else:
                    errores_consecutivos += 1

                # Si hay muchos errores, pausar
                if errores_consecutivos > 10:
                    print("\n[!] Muchos errores consecutivos - verificando...")
                    input(">>> Presiona ENTER para continuar: ")
                    errores_consecutivos = 0

                time.sleep(0.3)

            except KeyboardInterrupt:
                print("\n[!] Interrumpido por usuario")
                break
            except Exception as e:
                print(f"  Error en {puesto['puesto']}: {e}")

        self.guardar_progreso()

        print(f"\n{'='*60}")
        print(f"  EXTRACCION COMPLETADA")
        print(f"  Total tokens (mesas): {len(self.tokens_extraidos)}")
        print(f"  Puestos procesados: {len(self.procesados)}")
        print(f"{'='*60}")

    def descargar_pdfs(self, max_workers=5):
        """Descarga PDFs usando los tokens extraidos"""
        print(f"\n[*] Descargando {len(self.tokens_extraidos)} PDFs...")

        os.makedirs('pdfs_congreso_2022', exist_ok=True)

        descargados = 0
        errores = 0

        for i, item in enumerate(self.tokens_extraidos):
            if i % 100 == 0:
                print(f"[{i}/{len(self.tokens_extraidos)}] Descargados: {descargados} | Errores: {errores}")

            # Crear ruta
            corp = item['corporacion'].replace(' ', '_')[:10]
            depto = re.sub(r'[^\w]', '_', item['departamento'])[:20]
            muni = re.sub(r'[^\w]', '_', item['municipio'])[:20]
            puesto = re.sub(r'[^\w]', '_', item['puesto'])[:30]
            mesa = item['mesa']

            dir_path = f"pdfs_congreso_2022/{corp}/{depto}/{muni}"
            os.makedirs(dir_path, exist_ok=True)

            filename = f"{dir_path}/{puesto}_{mesa}.pdf"

            if os.path.exists(filename):
                descargados += 1
                continue

            try:
                response = self.session.post(
                    f"{self.base_url}/descargae14",
                    data={'token': item['token']},
                    timeout=30
                )

                if response.status_code == 200 and response.content[:4] == b'%PDF':
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    descargados += 1
                else:
                    errores += 1

            except Exception as e:
                errores += 1

            time.sleep(0.2)

        print(f"\n[OK] Descarga completada: {descargados} PDFs")
        if errores:
            print(f"[!] Errores: {errores}")

    def cerrar(self):
        if self.driver:
            self.driver.quit()


def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     SELENIUM EXTRACTOR - CONGRESO 2022                     ║
    ║     SENADO + CAMARA                                        ║
    ╠════════════════════════════════════════════════════════════╣
    ║  1. Extraer tokens (requiere resolver CAPTCHA 1 vez)       ║
    ║  2. Descargar PDFs (usa tokens ya extraidos)               ║
    ║  3. Ambos (extraer + descargar)                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    opcion = input("Selecciona opcion (1-3): ").strip()

    extractor = SeleniumCongreso2022()

    if opcion in ['1', '3']:
        if not extractor.iniciar_navegador():
            return

        try:
            extractor.navegar_sitio()
            extractor.esperar_captcha()
            extractor.extraer_todos_tokens()
        finally:
            extractor.cerrar()

    if opcion in ['2', '3']:
        if not extractor.tokens_extraidos:
            print("[ERROR] No hay tokens. Ejecuta opcion 1 primero.")
            return
        extractor.descargar_pdfs()

    print("\n[OK] Proceso terminado")


if __name__ == "__main__":
    main()
