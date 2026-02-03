#!/usr/bin/env python3
"""
DESCARGADOR DE PDFs DESDE TOKENS EXTRAIDOS
Usa los tokens guardados por selenium_extractor.py para descargar masivamente
"""

import requests
import json
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('descarga_pdfs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DescargadorPDFs:
    def __init__(self, directorio_salida='actas_e14'):
        self.base_url = "https://e14_pres1v_2022.registraduria.gov.co"
        self.directorio = directorio_salida
        self.session = requests.Session()

        # Headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'es-ES,es;q=0.9',
        })

        # Cargar cookies si existen
        self.cargar_cookies()

        # Control de progreso
        self.lock = Lock()
        self.descargados = set()
        self.fallidos = []
        self.cargar_progreso()

        # Estadísticas
        self.stats = {
            'total': 0,
            'exitosos': 0,
            'fallidos': 0,
            'omitidos': 0,
            'bytes_descargados': 0
        }

    def cargar_cookies(self):
        """Carga cookies de sesión de Selenium"""
        try:
            if os.path.exists('cookies_requests.json'):
                with open('cookies_requests.json', 'r') as f:
                    cookies = json.load(f)
                    self.session.cookies.update(cookies)
                logger.info("Cookies cargadas")
        except Exception as e:
            logger.warning(f"No se pudieron cargar cookies: {e}")

    def cargar_progreso(self):
        """Carga progreso de descargas previas"""
        if os.path.exists('descargados.json'):
            with open('descargados.json', 'r') as f:
                self.descargados = set(json.load(f))
            logger.info(f"Progreso cargado: {len(self.descargados)} archivos previos")

    def guardar_progreso(self):
        """Guarda progreso actual"""
        with open('descargados.json', 'w') as f:
            json.dump(list(self.descargados), f)

        with open('fallidos.json', 'w') as f:
            json.dump(self.fallidos, f, indent=2)

    def limpiar_nombre(self, nombre):
        """Limpia nombre de archivo para el sistema de archivos"""
        # Reemplazar caracteres no válidos
        nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
        nombre = re.sub(r'\s+', '_', nombre)
        nombre = re.sub(r'_+', '_', nombre)
        return nombre.strip('_')

    def descargar_pdf(self, token, ruta_relativa, reintentos=3):
        """Descarga un PDF individual"""

        # Crear identificador único
        identificador = token[:50] if len(token) > 50 else token

        # Verificar si ya fue descargado
        if identificador in self.descargados:
            with self.lock:
                self.stats['omitidos'] += 1
            return True

        # Crear ruta completa
        ruta_completa = os.path.join(self.directorio, ruta_relativa)

        # Verificar si el archivo ya existe
        if os.path.exists(ruta_completa):
            with self.lock:
                self.descargados.add(identificador)
                self.stats['omitidos'] += 1
            return True

        # Crear directorio
        os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)

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

                    # Verificar que sea PDF
                    contenido = response.content
                    if contenido[:4] == b'%PDF' or 'pdf' in content_type.lower():
                        with open(ruta_completa, 'wb') as f:
                            f.write(contenido)

                        with self.lock:
                            self.descargados.add(identificador)
                            self.stats['exitosos'] += 1
                            self.stats['bytes_descargados'] += len(contenido)

                        return True
                    else:
                        # No es PDF - puede ser error o CAPTCHA
                        logger.warning(f"Respuesta no es PDF: {ruta_relativa}")

                        # Guardar respuesta para debug
                        with open(f"debug_{identificador[:20]}.html", 'w') as f:
                            try:
                                f.write(response.text)
                            except:
                                pass

                        if 'captcha' in response.text.lower():
                            logger.error("CAPTCHA detectado - sesion expirada")
                            return False

                elif response.status_code == 429:
                    # Rate limiting
                    logger.warning("Rate limiting detectado, esperando...")
                    time.sleep(30)
                    continue

                else:
                    logger.warning(f"Status {response.status_code}: {ruta_relativa}")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout (intento {intento+1}): {ruta_relativa}")
            except Exception as e:
                logger.error(f"Error (intento {intento+1}): {e}")

            # Esperar antes de reintentar
            time.sleep(2 ** intento)

        # Falló después de todos los reintentos
        with self.lock:
            self.stats['fallidos'] += 1
            self.fallidos.append({
                'token': token[:50],
                'ruta': ruta_relativa,
                'fecha': datetime.now().isoformat()
            })

        return False

    def descargar_lote(self, tokens, workers=10, delay=0.5):
        """
        Descarga un lote de PDFs en paralelo

        tokens: lista de dicts con 'token' y 'ruta'
        workers: número de descargas paralelas
        delay: segundos entre envío de tareas
        """
        self.stats['total'] = len(tokens)

        logger.info(f"""
        ========================================
        INICIANDO DESCARGA MASIVA
        ========================================
        Total a descargar: {len(tokens)}
        Workers paralelos: {workers}
        Directorio: {self.directorio}
        ========================================
        """)

        inicio = datetime.now()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futuros = {}

            for i, item in enumerate(tokens):
                token = item.get('token')
                ruta = item.get('ruta', f'acta_{i}.pdf')

                futuro = executor.submit(self.descargar_pdf, token, ruta)
                futuros[futuro] = ruta

                # Pequeño delay para no saturar
                if i % workers == 0 and delay > 0:
                    time.sleep(delay)

            # Procesar resultados
            completados = 0
            for futuro in as_completed(futuros):
                completados += 1

                # Mostrar progreso cada 100 archivos
                if completados % 100 == 0:
                    transcurrido = (datetime.now() - inicio).total_seconds()
                    velocidad = completados / transcurrido if transcurrido > 0 else 0
                    restante = (len(tokens) - completados) / velocidad if velocidad > 0 else 0

                    logger.info(
                        f"Progreso: {completados}/{len(tokens)} | "
                        f"OK: {self.stats['exitosos']} | "
                        f"FAIL: {self.stats['fallidos']} | "
                        f"SKIP: {self.stats['omitidos']} | "
                        f"Vel: {velocidad:.1f}/s | "
                        f"ETA: {restante/60:.1f} min"
                    )

                    # Guardar progreso periódicamente
                    self.guardar_progreso()

        # Guardar progreso final
        self.guardar_progreso()

        # Reporte final
        fin = datetime.now()
        duracion = (fin - inicio).total_seconds()

        logger.info(f"""
        ========================================
        DESCARGA COMPLETADA
        ========================================
        Tiempo total: {duracion/60:.1f} minutos
        Total procesados: {self.stats['total']}
        Exitosos: {self.stats['exitosos']}
        Fallidos: {self.stats['fallidos']}
        Omitidos (ya existian): {self.stats['omitidos']}
        Datos descargados: {self.stats['bytes_descargados']/1024/1024:.1f} MB
        ========================================
        """)

        return self.stats


def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     DESCARGADOR DE PDFs DESDE TOKENS                       ║
    ╠════════════════════════════════════════════════════════════╣
    ║  Asegurate de haber ejecutado primero:                     ║
    ║  python selenium_extractor.py                              ║
    ║                                                            ║
    ║  Los tokens deben estar en: tokens_extraidos.json          ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # Verificar que existen los tokens
    if not os.path.exists('tokens_extraidos.json'):
        print("[ERROR] No se encontro tokens_extraidos.json")
        print("        Ejecuta primero: python selenium_extractor.py")
        return

    # Cargar tokens
    with open('tokens_extraidos.json', 'r') as f:
        tokens_raw = json.load(f)

    print(f"\nTokens encontrados: {len(tokens_raw)}")

    # Preparar lista de descargas
    tokens = []
    for t in tokens_raw:
        # Crear ruta organizada
        depto = t.get('departamento', 'SIN_DEPTO')
        muni = t.get('municipio', 'SIN_MUNICIPIO')
        puesto = t.get('puesto', 'SIN_PUESTO')
        mesa = t.get('mesa', 'mesa')

        # Limpiar nombres
        depto = re.sub(r'[<>:"/\\|?*]', '_', depto)
        muni = re.sub(r'[<>:"/\\|?*]', '_', muni)
        puesto = re.sub(r'[<>:"/\\|?*]', '_', puesto)
        mesa = re.sub(r'[<>:"/\\|?*]', '_', mesa)

        ruta = f"{depto}/{muni}/{puesto}/{mesa}.pdf"

        tokens.append({
            'token': t['token'],
            'ruta': ruta
        })

    # Configuración
    print("\n--- CONFIGURACION ---")
    workers = input("Numero de descargas paralelas (default 10): ").strip()
    workers = int(workers) if workers.isdigit() else 10

    directorio = input("Directorio de salida (default 'actas_e14'): ").strip()
    directorio = directorio or 'actas_e14'

    # Confirmar
    print(f"\n{'='*50}")
    print(f"  Tokens a procesar: {len(tokens)}")
    print(f"  Workers paralelos: {workers}")
    print(f"  Directorio: {directorio}")
    print(f"{'='*50}")

    confirmar = input("\nIniciar descarga? (s/n): ").strip().lower()
    if confirmar != 's':
        print("Cancelado")
        return

    # Iniciar descarga
    descargador = DescargadorPDFs(directorio_salida=directorio)
    descargador.descargar_lote(tokens, workers=workers)


if __name__ == "__main__":
    main()
