#!/usr/bin/env python3
"""
EJECUTAR EXTRACCION AUTOMATICA - CONGRESO 2022
Abre Chrome, extrae tokens y descarga PDFs
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
import pickle
import sys

class ExtractorCongreso:
    def __init__(self):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.driver = None
        self.tokens_extraidos = []
        self.session = requests.Session()
        self.procesados = set()

        # Cargar puestos
        print("[*] Cargando lista de puestos...")
        with open('lista_puestos_congreso_2022.json', 'r') as f:
            self.puestos = json.load(f)
        print(f"[OK] {len(self.puestos)} puestos cargados")

        # Cargar progreso previo
        self.cargar_progreso()

    def cargar_progreso(self):
        if os.path.exists('progreso_tokens.json'):
            with open('progreso_tokens.json', 'r') as f:
                data = json.load(f)
                self.tokens_extraidos = data.get('tokens', [])
                self.procesados = set(data.get('procesados', []))
            print(f"[OK] Progreso previo: {len(self.tokens_extraidos)} tokens, {len(self.procesados)} puestos")

    def guardar_progreso(self):
        with open('progreso_tokens.json', 'w') as f:
            json.dump({
                'tokens': self.tokens_extraidos,
                'procesados': list(self.procesados),
                'ultima_actualizacion': datetime.now().isoformat()
            }, f)

        with open('tokens_mesas_congreso.json', 'w') as f:
            json.dump(self.tokens_extraidos, f, indent=2, ensure_ascii=False)

    def iniciar_chrome(self):
        print("[*] Iniciando Chrome...")

        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1400,900')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            print("[OK] Chrome iniciado")
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            print("\n>>> Instala ChromeDriver:")
            print("    brew install --cask chromedriver")
            return False

    def ir_a_sitio(self):
        print(f"[*] Navegando a {self.base_url}")
        self.driver.get(self.base_url)
        time.sleep(3)

    def seleccionar(self, select_id, valor, espera=0.8):
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            Select(elem).select_by_value(valor)
            time.sleep(espera)
            return True
        except:
            return False

    def click_consultar(self):
        try:
            btn = self.driver.find_element(By.ID, 'btnConsultarE14')
            btn.click()
            time.sleep(2)
            return True
        except:
            return False

    def obtener_tokens_mesas(self):
        """Extrae tokens de la página actual"""
        tokens = []
        html = self.driver.page_source

        # Buscar descargarE14('TOKEN')
        matches = re.findall(r"descargarE14\(['\"]([^'\"]+)['\"]\)", html)
        for t in matches:
            if len(t) > 30:
                tokens.append(t)

        return tokens

    def procesar_un_puesto(self, p):
        """Procesa un puesto y extrae sus tokens"""
        key = f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"

        if key in self.procesados:
            return 0

        try:
            self.seleccionar('selectCorp', p['corporacion_cod'], 1)
            self.seleccionar('selectDepto', p['departamento_cod'], 1)
            self.seleccionar('selectMpio', p['municipio_cod'], 0.5)
            self.seleccionar('selectZona', p['zona_cod'], 0.5)
            self.seleccionar('selectPto', p['puesto_cod'], 0.5)

            self.click_consultar()
            time.sleep(1)

            tokens = self.obtener_tokens_mesas()

            for i, token in enumerate(tokens):
                self.tokens_extraidos.append({
                    'token': token,
                    'corp': p['corporacion'],
                    'depto': p['departamento'],
                    'muni': p['municipio'],
                    'zona': p['zona'],
                    'puesto': p['puesto'],
                    'mesa': i + 1
                })

            self.procesados.add(key)
            return len(tokens)

        except Exception as e:
            return 0

    def extraer_todo(self):
        """Extrae tokens de todos los puestos"""
        pendientes = [p for p in self.puestos
                     if f"{p['corporacion_cod']}|{p['departamento_cod']}|{p['municipio_cod']}|{p['zona_cod']}|{p['puesto_cod']}"
                     not in self.procesados]

        print(f"\n[*] Puestos pendientes: {len(pendientes)}")
        print(f"[*] Ya procesados: {len(self.procesados)}")
        print(f"[*] Tokens acumulados: {len(self.tokens_extraidos)}")

        for i, p in enumerate(pendientes):
            if i % 100 == 0:
                print(f"\n>>> [{i}/{len(pendientes)}] Tokens: {len(self.tokens_extraidos)}")
                print(f"    {p['corporacion'][:10]} | {p['departamento'][:25]}")
                self.guardar_progreso()

            n = self.procesar_un_puesto(p)

            if n > 0:
                sys.stdout.write('.')
                sys.stdout.flush()

            time.sleep(0.2)

        self.guardar_progreso()
        print(f"\n\n[OK] Extraccion completada: {len(self.tokens_extraidos)} tokens")

    def descargar_pdfs(self):
        """Descarga todos los PDFs"""
        print(f"\n[*] Descargando {len(self.tokens_extraidos)} PDFs...")

        # Cargar cookies del navegador
        if self.driver:
            for cookie in self.driver.get_cookies():
                self.session.cookies.set(cookie['name'], cookie['value'])

        os.makedirs('pdfs_congreso', exist_ok=True)

        ok = 0
        err = 0

        for i, t in enumerate(self.tokens_extraidos):
            if i % 500 == 0:
                print(f"[{i}/{len(self.tokens_extraidos)}] OK:{ok} ERR:{err}")

            # Nombre archivo
            corp = re.sub(r'[^\w]', '', t['corp'])[:8]
            depto = re.sub(r'[^\w]', '', t['depto'])[:15]
            muni = re.sub(r'[^\w]', '', t['muni'])[:15]
            puesto = re.sub(r'[^\w]', '', t['puesto'])[:20]

            carpeta = f"pdfs_congreso/{corp}/{depto}"
            os.makedirs(carpeta, exist_ok=True)

            archivo = f"{carpeta}/{muni}_{puesto}_M{t['mesa']:03d}.pdf"

            if os.path.exists(archivo):
                ok += 1
                continue

            try:
                r = self.session.post(
                    f"{self.base_url}/descargae14",
                    data={'token': t['token']},
                    timeout=30
                )

                if r.content[:4] == b'%PDF':
                    with open(archivo, 'wb') as f:
                        f.write(r.content)
                    ok += 1
                else:
                    err += 1
            except:
                err += 1

            time.sleep(0.1)

        print(f"\n[OK] Descarga: {ok} exitosos, {err} errores")

    def cerrar(self):
        if self.driver:
            self.driver.quit()


def main():
    print("="*60)
    print("  EXTRACTOR CONGRESO 2022 - SENADO + CAMARA")
    print("="*60)

    ext = ExtractorCongreso()

    if not ext.iniciar_chrome():
        return

    try:
        ext.ir_a_sitio()

        print("\n" + "="*60)
        print("  >>> VE AL NAVEGADOR CHROME <<<")
        print("="*60)
        print("""
  1. Selecciona cualquier combinacion:
     - Corporacion (SENADO)
     - Departamento
     - Municipio
     - Zona
     - Puesto

  2. Clic en CONSULTAR

  3. RESUELVE EL CAPTCHA

  4. Cuando veas las mesas, vuelve aqui
""")
        print("="*60)

        input("\n>>> Presiona ENTER cuando hayas resuelto el CAPTCHA: ")

        print("\n[OK] Iniciando extraccion automatica...")
        ext.extraer_todo()

        print("\n[*] Iniciando descarga de PDFs...")
        ext.descargar_pdfs()

    except KeyboardInterrupt:
        print("\n[!] Interrumpido")
        ext.guardar_progreso()
    finally:
        ext.cerrar()

    print("\n[OK] Proceso terminado")


if __name__ == "__main__":
    main()
