#!/usr/bin/env python3
"""
EXTRACTOR DE TOKENS CON SELENIUM
Resuelve el problema del CAPTCHA mediante interacción manual mínima

ESTRATEGIA:
1. Abrir navegador real
2. Usuario resuelve CAPTCHA UNA VEZ
3. Script navega automáticamente por TODA la estructura
4. Extrae todos los tokens
5. Guarda sesión para descargas posteriores
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import pickle
import os
import re
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('extraccion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExtractorSeleniumE14:
    def __init__(self, headless=False):
        self.base_url = "https://e14_pres1v_2022.registraduria.gov.co"
        self.tokens_extraidos = []
        self.estructura = {}
        self.driver = None
        self.headless = headless

    def iniciar_navegador(self):
        """Inicia Chrome con configuración óptima"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')

        # Evitar detección de Selenium
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            logger.info("Navegador iniciado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error iniciando navegador: {e}")
            logger.info("Asegurate de tener Chrome y ChromeDriver instalados")
            return False

    def navegar_a_sitio(self):
        """Navega al sitio principal"""
        self.driver.get(self.base_url)
        time.sleep(3)
        logger.info(f"Navegando a {self.base_url}")

    def esperar_captcha_manual(self, timeout=300):
        """
        Espera a que el usuario resuelva el CAPTCHA manualmente

        El usuario tiene 5 minutos para:
        1. Resolver el CAPTCHA si aparece
        2. Presionar Enter en la consola cuando termine
        """
        print("\n" + "="*60)
        print("  ACCION REQUERIDA")
        print("="*60)
        print("""
        1. En el navegador que se abrio, selecciona:
           - Departamento
           - Municipio
           - Zona
           - Puesto

        2. Haz clic en 'Consultar'

        3. Si aparece CAPTCHA, resuelvelo manualmente

        4. Cuando veas las MESAS DE VOTACION, vuelve aqui

        5. Presiona ENTER para continuar...
        """)
        print("="*60)

        input("\n>>> Presiona ENTER cuando hayas resuelto el CAPTCHA y veas las mesas: ")

        # Guardar cookies de la sesión autenticada
        self.guardar_sesion()
        logger.info("Sesion guardada correctamente")

    def guardar_sesion(self):
        """Guarda cookies y estado de sesión"""
        cookies = self.driver.get_cookies()
        with open('cookies_selenium.pkl', 'wb') as f:
            pickle.dump(cookies, f)

        # También guardar para requests
        cookies_dict = {c['name']: c['value'] for c in cookies}
        with open('cookies_requests.json', 'w') as f:
            json.dump(cookies_dict, f)

    def cargar_sesion(self):
        """Carga sesión previa"""
        if os.path.exists('cookies_selenium.pkl'):
            with open('cookies_selenium.pkl', 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            logger.info("Sesion cargada")
            return True
        return False

    def obtener_opciones_select(self, selector_name):
        """Obtiene todas las opciones de un select"""
        try:
            select_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, selector_name))
            )
            select = Select(select_element)
            opciones = []
            for option in select.options:
                valor = option.get_attribute('value')
                texto = option.text.strip()
                if valor and valor != '':
                    opciones.append({'valor': valor, 'texto': texto})
            return opciones
        except Exception as e:
            logger.error(f"Error obteniendo opciones de {selector_name}: {e}")
            return []

    def seleccionar_opcion(self, selector_name, valor):
        """Selecciona una opción en un select"""
        try:
            select_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, selector_name))
            )
            select = Select(select_element)
            select.select_by_value(valor)
            time.sleep(1)  # Esperar carga AJAX
            return True
        except Exception as e:
            logger.error(f"Error seleccionando {valor} en {selector_name}: {e}")
            return False

    def hacer_clic_consultar(self):
        """Hace clic en el botón Consultar"""
        try:
            # Intentar varios selectores
            selectores = [
                "//button[contains(text(), 'Consultar')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//a[contains(text(), 'Consultar')]",
                "//*[contains(@class, 'btn') and contains(text(), 'Consultar')]"
            ]

            for selector in selectores:
                try:
                    boton = self.driver.find_element(By.XPATH, selector)
                    boton.click()
                    time.sleep(2)
                    return True
                except:
                    continue

            return False
        except Exception as e:
            logger.error(f"Error haciendo clic en Consultar: {e}")
            return False

    def extraer_tokens_pagina_actual(self):
        """Extrae todos los tokens de la página actual"""
        tokens = []
        html = self.driver.page_source

        # Método 1: Buscar botones de mesa
        try:
            botones_mesa = self.driver.find_elements(By.XPATH,
                "//*[contains(text(), 'Mesa') or contains(text(), 'MESA') or contains(@class, 'mesa')]"
            )

            for boton in botones_mesa:
                try:
                    # Obtener onclick
                    onclick = boton.get_attribute('onclick') or ''
                    data_token = boton.get_attribute('data-token') or ''

                    token = None
                    if data_token:
                        token = data_token
                    else:
                        # Buscar token en onclick
                        match = re.search(r"['\"]([a-zA-Z0-9+/=]{20,})['\"]", onclick)
                        if match:
                            token = match.group(1)

                    if token:
                        mesa_texto = boton.text.strip()
                        tokens.append({
                            'token': token,
                            'mesa': mesa_texto,
                            'url': self.driver.current_url
                        })
                except:
                    continue
        except:
            pass

        # Método 2: Buscar en formularios
        try:
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            for form in forms:
                action = form.get_attribute('action') or ''
                if 'descarga' in action.lower():
                    try:
                        token_input = form.find_element(By.NAME, 'token')
                        token = token_input.get_attribute('value')
                        if token:
                            tokens.append({
                                'token': token,
                                'mesa': f'form_{len(tokens)+1}',
                                'url': self.driver.current_url
                            })
                    except:
                        pass
        except:
            pass

        # Método 3: Ejecutar JavaScript para encontrar tokens
        try:
            js_tokens = self.driver.execute_script("""
                var tokens = [];
                document.querySelectorAll('[onclick]').forEach(function(el) {
                    var onclick = el.getAttribute('onclick');
                    var matches = onclick.match(/['"]([a-zA-Z0-9+/=]{20,})['"]/g);
                    if (matches) {
                        matches.forEach(function(m) {
                            tokens.push({
                                token: m.replace(/['"]/g, ''),
                                mesa: el.textContent.trim()
                            });
                        });
                    }
                });
                document.querySelectorAll('[data-token]').forEach(function(el) {
                    tokens.push({
                        token: el.getAttribute('data-token'),
                        mesa: el.textContent.trim()
                    });
                });
                return tokens;
            """)

            for t in js_tokens:
                if t['token'] and not any(x['token'] == t['token'] for x in tokens):
                    t['url'] = self.driver.current_url
                    tokens.append(t)
        except:
            pass

        return tokens

    def recorrer_estructura_completa(self):
        """
        Recorre TODA la estructura electoral extrayendo tokens

        Departamentos -> Municipios -> Zonas -> Puestos -> Mesas
        """
        logger.info("Iniciando recorrido de estructura completa...")

        # Obtener departamentos
        self.driver.get(self.base_url)
        time.sleep(2)

        departamentos = self.obtener_opciones_select('depart')
        logger.info(f"Encontrados {len(departamentos)} departamentos")

        total_tokens = 0
        progreso = {
            'departamentos_procesados': 0,
            'total_departamentos': len(departamentos),
            'tokens_por_depto': {}
        }

        for i, depto in enumerate(departamentos):
            logger.info(f"\n[{i+1}/{len(departamentos)}] Procesando departamento: {depto['texto']}")

            try:
                # Seleccionar departamento
                self.seleccionar_opcion('depart', depto['valor'])
                time.sleep(1.5)

                # Obtener municipios
                municipios = self.obtener_opciones_select('municipal')
                logger.info(f"  Municipios en {depto['texto']}: {len(municipios)}")

                tokens_depto = 0

                for j, muni in enumerate(municipios):
                    try:
                        self.seleccionar_opcion('municipal', muni['valor'])
                        time.sleep(1)

                        # Obtener zonas
                        zonas = self.obtener_opciones_select('zona')

                        for zona in zonas:
                            try:
                                self.seleccionar_opcion('zona', zona['valor'])
                                time.sleep(1)

                                # Obtener puestos
                                puestos = self.obtener_opciones_select('puesto')

                                for puesto in puestos:
                                    try:
                                        self.seleccionar_opcion('puesto', puesto['valor'])
                                        time.sleep(0.5)

                                        # Consultar
                                        self.hacer_clic_consultar()
                                        time.sleep(2)

                                        # Verificar si hay CAPTCHA
                                        if 'captcha' in self.driver.page_source.lower():
                                            print(f"\n[!] CAPTCHA detectado - Resuelve en el navegador y presiona Enter")
                                            input(">>> ")

                                        # Extraer tokens
                                        tokens = self.extraer_tokens_pagina_actual()

                                        for token in tokens:
                                            token['departamento'] = depto['texto']
                                            token['municipio'] = muni['texto']
                                            token['zona'] = zona['texto']
                                            token['puesto'] = puesto['texto']
                                            self.tokens_extraidos.append(token)
                                            tokens_depto += 1
                                            total_tokens += 1

                                        # Volver atrás
                                        self.driver.back()
                                        time.sleep(1)

                                    except Exception as e:
                                        logger.warning(f"Error en puesto {puesto['valor']}: {e}")
                                        continue

                            except Exception as e:
                                logger.warning(f"Error en zona {zona['valor']}: {e}")
                                continue

                    except Exception as e:
                        logger.warning(f"Error en municipio {muni['valor']}: {e}")
                        continue

                progreso['tokens_por_depto'][depto['texto']] = tokens_depto
                logger.info(f"  Tokens extraidos de {depto['texto']}: {tokens_depto}")

                # Guardar progreso parcial
                self.guardar_tokens()

            except Exception as e:
                logger.error(f"Error procesando departamento {depto['texto']}: {e}")
                continue

            progreso['departamentos_procesados'] = i + 1

            # Guardar progreso
            with open('progreso_extraccion.json', 'w') as f:
                json.dump(progreso, f, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info(f"EXTRACCION COMPLETADA")
        logger.info(f"Total tokens extraidos: {total_tokens}")
        logger.info(f"{'='*60}")

        return self.tokens_extraidos

    def guardar_tokens(self):
        """Guarda tokens extraídos a archivo"""
        # JSON para procesamiento
        with open('tokens_extraidos.json', 'w', encoding='utf-8') as f:
            json.dump(self.tokens_extraidos, f, indent=2, ensure_ascii=False)

        # Python para uso directo
        with open('tokens_python.py', 'w', encoding='utf-8') as f:
            f.write(f"# Tokens extraidos - {datetime.now().isoformat()}\n")
            f.write(f"# Total: {len(self.tokens_extraidos)} tokens\n\n")
            f.write("TOKENS = [\n")
            for t in self.tokens_extraidos:
                ruta = f"{t.get('departamento','')}/{t.get('municipio','')}/{t.get('puesto','')}/{t.get('mesa','')}.pdf"
                ruta = re.sub(r'[<>:"|?*]', '_', ruta)
                f.write(f"    {{'token': '{t['token']}', 'ruta': '{ruta}'}},\n")
            f.write("]\n")

        logger.info(f"Tokens guardados: {len(self.tokens_extraidos)}")

    def modo_extraccion_rapida(self):
        """
        Modo de extracción rápida:
        - Usuario navega manualmente al primer puesto
        - Script extrae tokens de esa vista
        - Luego navega automáticamente a puestos similares
        """
        print("\n" + "="*60)
        print("  MODO EXTRACCION RAPIDA")
        print("="*60)
        print("""
        Este modo te permite:
        1. Navegar manualmente a un puesto de votacion
        2. El script extraera los tokens de las mesas visibles
        3. Luego puedes navegar a otro puesto y repetir

        Para extraer, escribe 'e' y presiona Enter
        Para guardar y salir, escribe 'q' y presiona Enter
        """)
        print("="*60)

        while True:
            comando = input("\n>>> Comando (e=extraer, q=salir): ").strip().lower()

            if comando == 'e':
                tokens = self.extraer_tokens_pagina_actual()
                print(f"\nTokens encontrados en esta pagina: {len(tokens)}")

                for t in tokens:
                    if not any(x['token'] == t['token'] for x in self.tokens_extraidos):
                        # Pedir info de ubicación
                        info = input(f"  Info para '{t['mesa']}' (depto/muni/puesto o Enter para omitir): ").strip()
                        if info:
                            partes = info.split('/')
                            if len(partes) >= 3:
                                t['departamento'] = partes[0]
                                t['municipio'] = partes[1]
                                t['puesto'] = partes[2]
                        self.tokens_extraidos.append(t)

                print(f"Total tokens acumulados: {len(self.tokens_extraidos)}")
                self.guardar_tokens()

            elif comando == 'q':
                self.guardar_tokens()
                print(f"\nGuardados {len(self.tokens_extraidos)} tokens")
                break

    def cerrar(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            logger.info("Navegador cerrado")


def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     EXTRACTOR DE TOKENS CON SELENIUM                       ║
    ╠════════════════════════════════════════════════════════════╣
    ║  MODOS:                                                    ║
    ║  1. Extraccion completa automatica                         ║
    ║     (recorre TODOS los departamentos/municipios)           ║
    ║                                                            ║
    ║  2. Extraccion rapida manual                               ║
    ║     (tu navegas, el script extrae)                         ║
    ║                                                            ║
    ║  3. Continuar extraccion previa                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    modo = input("Selecciona modo (1-3): ").strip()

    extractor = ExtractorSeleniumE14(headless=False)

    if not extractor.iniciar_navegador():
        print("Error: No se pudo iniciar el navegador")
        print("Instala Chrome y ChromeDriver:")
        print("  brew install --cask chromedriver  # Mac")
        print("  O descarga de: https://chromedriver.chromium.org/")
        return

    try:
        extractor.navegar_a_sitio()

        if modo == '1':
            extractor.esperar_captcha_manual()
            extractor.recorrer_estructura_completa()

        elif modo == '2':
            print("\nNavega en el navegador a donde quieras extraer tokens...")
            extractor.modo_extraccion_rapida()

        elif modo == '3':
            # Cargar progreso previo
            if os.path.exists('tokens_extraidos.json'):
                with open('tokens_extraidos.json', 'r') as f:
                    extractor.tokens_extraidos = json.load(f)
                print(f"Cargados {len(extractor.tokens_extraidos)} tokens previos")

            extractor.cargar_sesion()
            extractor.recorrer_estructura_completa()

        extractor.guardar_tokens()

    finally:
        input("\nPresiona Enter para cerrar el navegador...")
        extractor.cerrar()


if __name__ == "__main__":
    main()
