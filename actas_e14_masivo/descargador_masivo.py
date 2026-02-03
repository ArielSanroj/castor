#!/usr/bin/env python3
"""
DESCARGADOR MASIVO DE ACTAS E14
Para ~103,000 PDFs con manejo de CAPTCHA

Estrategias para CAPTCHA:
1. Resolver manualmente una vez y reutilizar sesión
2. Usar servicio de resolución automática (2Captcha, Anti-Captcha)
3. Usar Selenium con intervención humana mínima
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
import pickle
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('descarga.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GestorProgreso:
    """Guarda progreso para poder resumir descargas interrumpidas"""

    def __init__(self, archivo='progreso.json'):
        self.archivo = archivo
        self.lock = Lock()
        self.datos = self._cargar()

    def _cargar(self):
        if os.path.exists(self.archivo):
            with open(self.archivo, 'r') as f:
                return json.load(f)
        return {
            'descargados': [],
            'fallidos': [],
            'pendientes': [],
            'tokens_extraidos': {},
            'ultima_actualizacion': None
        }

    def guardar(self):
        with self.lock:
            self.datos['ultima_actualizacion'] = datetime.now().isoformat()
            with open(self.archivo, 'w') as f:
                json.dump(self.datos, f, indent=2)

    def marcar_descargado(self, identificador):
        with self.lock:
            if identificador not in self.datos['descargados']:
                self.datos['descargados'].append(identificador)

    def marcar_fallido(self, identificador, error):
        with self.lock:
            self.datos['fallidos'].append({
                'id': identificador,
                'error': str(error),
                'fecha': datetime.now().isoformat()
            })

    def ya_descargado(self, identificador):
        return identificador in self.datos['descargados']

    def agregar_tokens(self, ubicacion, tokens):
        with self.lock:
            self.datos['tokens_extraidos'][ubicacion] = tokens

    def estadisticas(self):
        return {
            'descargados': len(self.datos['descargados']),
            'fallidos': len(self.datos['fallidos']),
            'pendientes': len(self.datos['pendientes'])
        }


class ResolvedorCaptcha:
    """Integración con servicios de resolución de CAPTCHA"""

    def __init__(self, servicio='manual', api_key=None):
        self.servicio = servicio
        self.api_key = api_key

    def resolver_recaptcha(self, site_key, page_url):
        """Resuelve reCAPTCHA v2"""

        if self.servicio == 'manual':
            logger.info("CAPTCHA requerido - Resolución manual necesaria")
            return None

        elif self.servicio == '2captcha':
            return self._resolver_2captcha(site_key, page_url)

        elif self.servicio == 'anticaptcha':
            return self._resolver_anticaptcha(site_key, page_url)

        return None

    def _resolver_2captcha(self, site_key, page_url):
        """Usa 2Captcha API (costo ~$2.99 por 1000 CAPTCHAs)"""
        if not self.api_key:
            logger.error("API key de 2Captcha no configurada")
            return None

        try:
            # Enviar CAPTCHA
            response = requests.post('http://2captcha.com/in.php', data={
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            })

            result = response.json()
            if result['status'] != 1:
                logger.error(f"Error 2Captcha: {result}")
                return None

            captcha_id = result['request']
            logger.info(f"CAPTCHA enviado, ID: {captcha_id}")

            # Esperar resultado
            for _ in range(60):  # Máximo 5 minutos
                time.sleep(5)
                response = requests.get(
                    f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1'
                )
                result = response.json()

                if result['status'] == 1:
                    logger.info("CAPTCHA resuelto!")
                    return result['request']
                elif result['request'] != 'CAPCHA_NOT_READY':
                    logger.error(f"Error: {result['request']}")
                    return None

        except Exception as e:
            logger.error(f"Error con 2Captcha: {e}")

        return None

    def _resolver_anticaptcha(self, site_key, page_url):
        """Usa Anti-Captcha API"""
        if not self.api_key:
            logger.error("API key de Anti-Captcha no configurada")
            return None

        try:
            # Crear tarea
            response = requests.post('https://api.anti-captcha.com/createTask', json={
                'clientKey': self.api_key,
                'task': {
                    'type': 'RecaptchaV2TaskProxyless',
                    'websiteURL': page_url,
                    'websiteKey': site_key
                }
            })

            result = response.json()
            if result['errorId'] != 0:
                logger.error(f"Error Anti-Captcha: {result}")
                return None

            task_id = result['taskId']

            # Esperar resultado
            for _ in range(60):
                time.sleep(5)
                response = requests.post('https://api.anti-captcha.com/getTaskResult', json={
                    'clientKey': self.api_key,
                    'taskId': task_id
                })
                result = response.json()

                if result['status'] == 'ready':
                    return result['solution']['gRecaptchaResponse']

        except Exception as e:
            logger.error(f"Error con Anti-Captcha: {e}")

        return None


class DescargadorMasivoE14:
    """Descargador masivo con soporte para 100k+ archivos"""

    def __init__(self, config=None):
        self.config = config or {}
        self.base_url = "https://e14_pres1v_2022.registraduria.gov.co"
        self.session = requests.Session()
        self.progreso = GestorProgreso()
        self.captcha = ResolvedorCaptcha(
            servicio=self.config.get('captcha_servicio', 'manual'),
            api_key=self.config.get('captcha_api_key')
        )

        # Directorio de descargas
        self.dir_descargas = self.config.get('directorio', 'actas_e14')
        os.makedirs(self.dir_descargas, exist_ok=True)

        # Headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
        })

        # Estadísticas
        self.stats = {'intentos': 0, 'exitos': 0, 'fallos': 0}
        self.stats_lock = Lock()

    def cargar_cookies_sesion(self, archivo='cookies.pkl'):
        """Carga cookies de una sesión previa"""
        if os.path.exists(archivo):
            with open(archivo, 'rb') as f:
                self.session.cookies.update(pickle.load(f))
            logger.info("Cookies cargadas desde archivo")
            return True
        return False

    def guardar_cookies_sesion(self, archivo='cookies.pkl'):
        """Guarda cookies para reutilizar sesión"""
        with open(archivo, 'wb') as f:
            pickle.dump(self.session.cookies, f)
        logger.info("Cookies guardadas")

    def obtener_estructura_electoral(self):
        """
        Obtiene toda la estructura electoral:
        Departamentos -> Municipios -> Zonas -> Puestos -> Mesas
        """
        estructura = {}

        response = self.session.get(f"{self.base_url}/")
        if response.status_code != 200:
            logger.error("No se pudo acceder al sitio")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer departamentos
        select_depart = soup.find('select', {'name': 'depart'}) or soup.find('select', {'id': 'depart'})
        if select_depart:
            for option in select_depart.find_all('option'):
                valor = option.get('value')
                if valor and valor != '':
                    estructura[valor] = {
                        'nombre': option.text.strip(),
                        'municipios': {}
                    }

        logger.info(f"Encontrados {len(estructura)} departamentos")
        return estructura

    def obtener_municipios_ajax(self, depto_codigo):
        """Obtiene municipios via AJAX"""
        urls_posibles = [
            f"{self.base_url}/getMunicipios",
            f"{self.base_url}/api/municipios",
            f"{self.base_url}/municipios"
        ]

        for url in urls_posibles:
            try:
                response = self.session.post(url, data={'depart': depto_codigo}, timeout=10)
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        # Intentar parsear HTML
                        soup = BeautifulSoup(response.text, 'html.parser')
                        municipios = []
                        for option in soup.find_all('option'):
                            if option.get('value'):
                                municipios.append({
                                    'codigo': option.get('value'),
                                    'nombre': option.text.strip()
                                })
                        return municipios
            except:
                continue

        return []

    def extraer_tokens_pagina(self, html):
        """Extrae todos los tokens de descarga de una página"""
        soup = BeautifulSoup(html, 'html.parser')
        tokens = []

        # Método 1: onclick con función de descarga
        for el in soup.find_all(onclick=re.compile(r'descarga|download', re.I)):
            onclick = el.get('onclick', '')
            matches = re.findall(r"['\"]([a-zA-Z0-9+/=]{20,})['\"]", onclick)
            for token in matches:
                mesa = el.text.strip() or f"mesa_{len(tokens)+1}"
                tokens.append({'token': token, 'mesa': mesa})

        # Método 2: data-token
        for el in soup.find_all(attrs={'data-token': True}):
            token = el.get('data-token')
            mesa = el.text.strip() or f"mesa_{len(tokens)+1}"
            tokens.append({'token': token, 'mesa': mesa})

        # Método 3: inputs ocultos
        for form in soup.find_all('form'):
            if 'descarga' in str(form.get('action', '')).lower():
                token_input = form.find('input', {'name': 'token'})
                if token_input and token_input.get('value'):
                    tokens.append({
                        'token': token_input.get('value'),
                        'mesa': f"mesa_{len(tokens)+1}"
                    })

        # Método 4: enlaces directos
        for a in soup.find_all('a', href=re.compile(r'descarga.*token=|token=.*descarga', re.I)):
            href = a.get('href', '')
            match = re.search(r'token=([a-zA-Z0-9+/=]+)', href)
            if match:
                tokens.append({
                    'token': match.group(1),
                    'mesa': a.text.strip() or f"mesa_{len(tokens)+1}"
                })

        return tokens

    def consultar_con_captcha(self, params):
        """Realiza consulta manejando CAPTCHA si es necesario"""
        url = f"{self.base_url}/consultar"

        response = self.session.post(url, data=params, timeout=30)

        # Verificar si hay CAPTCHA
        if 'captcha' in response.text.lower() or 'recaptcha' in response.text.lower():
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar site key de reCAPTCHA
            recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
            if recaptcha_div:
                site_key = recaptcha_div.get('data-sitekey')

                if self.captcha.servicio != 'manual':
                    # Resolver automáticamente
                    token = self.captcha.resolver_recaptcha(site_key, url)
                    if token:
                        params['g-recaptcha-response'] = token
                        response = self.session.post(url, data=params, timeout=30)
                else:
                    logger.warning("CAPTCHA detectado - requiere resolución manual")
                    return None

        return response

    def descargar_pdf(self, token, ruta_archivo, reintentos=3):
        """Descarga un PDF individual con reintentos"""
        if self.progreso.ya_descargado(token[:50]):
            return True

        url = f"{self.base_url}/descargae14"

        for intento in range(reintentos):
            try:
                response = self.session.post(
                    url,
                    data={'token': token},
                    timeout=60,
                    stream=True
                )

                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')

                    if 'pdf' in content_type.lower() or response.content[:4] == b'%PDF':
                        # Crear directorio si no existe
                        os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)

                        with open(ruta_archivo, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        self.progreso.marcar_descargado(token[:50])

                        with self.stats_lock:
                            self.stats['exitos'] += 1

                        return True

                # Si no es PDF, puede ser CAPTCHA
                if 'captcha' in response.text.lower():
                    logger.warning(f"CAPTCHA requerido para {ruta_archivo}")
                    return False

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout intento {intento+1}/{reintentos}: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error intento {intento+1}/{reintentos}: {e}")

            time.sleep(2 ** intento)  # Backoff exponencial

        self.progreso.marcar_fallido(token[:50], "Max reintentos")
        with self.stats_lock:
            self.stats['fallos'] += 1

        return False

    def descargar_lote_paralelo(self, tareas, max_workers=5):
        """
        Descarga múltiples PDFs en paralelo

        tareas: lista de diccionarios con 'token' y 'ruta'
        """
        logger.info(f"Iniciando descarga de {len(tareas)} archivos con {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = {
                executor.submit(
                    self.descargar_pdf,
                    tarea['token'],
                    tarea['ruta']
                ): tarea
                for tarea in tareas
            }

            completados = 0
            for futuro in as_completed(futuros):
                completados += 1
                tarea = futuros[futuro]

                try:
                    resultado = futuro.result()
                    if completados % 100 == 0:
                        stats = self.progreso.estadisticas()
                        logger.info(
                            f"Progreso: {completados}/{len(tareas)} | "
                            f"Exitos: {self.stats['exitos']} | "
                            f"Fallos: {self.stats['fallos']}"
                        )
                        self.progreso.guardar()
                except Exception as e:
                    logger.error(f"Error en tarea: {e}")

        self.progreso.guardar()
        logger.info(f"Lote completado: {self.stats}")

    def generar_reporte(self):
        """Genera reporte de descarga"""
        stats = self.progreso.estadisticas()
        reporte = f"""
========================================
REPORTE DE DESCARGA - ACTAS E14
========================================
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ESTADÍSTICAS:
- Descargados exitosamente: {stats['descargados']}
- Fallidos: {stats['fallidos']}
- Pendientes: {stats['pendientes']}

DIRECTORIO: {self.dir_descargas}
========================================
"""
        print(reporte)

        with open('reporte_descarga.txt', 'w') as f:
            f.write(reporte)

        return stats


def main():
    """Función principal"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     DESCARGADOR MASIVO DE ACTAS E14                        ║
    ║     ~103,000 PDFs con manejo de CAPTCHA                    ║
    ╠════════════════════════════════════════════════════════════╣
    ║  OPCIONES:                                                 ║
    ║  1. Usar Selenium (recomendado para CAPTCHA)               ║
    ║  2. Usar sesión guardada                                   ║
    ║  3. Usar servicio de CAPTCHA (2Captcha/Anti-Captcha)       ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    opcion = input("Selecciona opción (1-3): ").strip()

    if opcion == '1':
        print("\nEjecuta el script de Selenium: python selenium_extractor.py")
    elif opcion == '2':
        descargador = DescargadorMasivoE14()
        if descargador.cargar_cookies_sesion():
            print("Sesión cargada. Continuando descargas...")
        else:
            print("No hay sesión guardada. Usa opción 1 primero.")
    elif opcion == '3':
        api_key = input("Ingresa tu API key de 2Captcha: ").strip()
        config = {
            'captcha_servicio': '2captcha',
            'captcha_api_key': api_key
        }
        descargador = DescargadorMasivoE14(config)
        print("Configurado con 2Captcha. Iniciando...")


if __name__ == "__main__":
    main()
