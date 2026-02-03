#!/usr/bin/env python3
"""
Script para descargar Actas E14 de la Registraduría de Colombia
Elecciones Presidenciales 2022
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import os
import re

class DescargadorActasE14:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://e14_pres1v_2022.registraduria.gov.co"
        self.descargas = []
        self.errores = []

        # Headers para simular navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })

    def obtener_sesion(self):
        """Obtiene una sesión válida desde la página principal"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=30)
            print(f"[OK] Sesion iniciada: Status {response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] No se pudo conectar: {e}")
            return None

    def obtener_departamentos(self):
        """Obtiene la lista de departamentos disponibles"""
        response = self.session.get(f"{self.base_url}/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            select_depart = soup.find('select', {'name': 'depart'})
            if select_depart:
                departamentos = {}
                for option in select_depart.find_all('option'):
                    if option.get('value'):
                        departamentos[option.get('value')] = option.text.strip()
                return departamentos
        return {}

    def obtener_municipios(self, departamento):
        """Obtiene municipios de un departamento"""
        # Esto requiere hacer una solicitud AJAX al servidor
        url = f"{self.base_url}/getMunicipios"
        try:
            response = self.session.post(url, data={'depart': departamento}, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def extraer_tokens_de_pagina(self, html_content):
        """Extrae tokens de descarga del HTML de la página"""
        soup = BeautifulSoup(html_content, 'html.parser')
        tokens = []

        # Buscar botones o enlaces con tokens
        # Patron comun: onclick="descargar('TOKEN')" o data-token="TOKEN"

        # Buscar en onclick
        for element in soup.find_all(onclick=True):
            onclick = element.get('onclick', '')
            # Buscar patrones como descargar('...') o download('...')
            matches = re.findall(r"(?:descargar|download|descargae14)\(['\"]([^'\"]+)['\"]\)", onclick)
            for match in matches:
                mesa_text = element.text.strip() if element.text else f"mesa_{len(tokens)+1}"
                tokens.append((match, f"{mesa_text}.pdf"))

        # Buscar en data-token
        for element in soup.find_all(attrs={'data-token': True}):
            token = element.get('data-token')
            mesa_text = element.text.strip() if element.text else f"mesa_{len(tokens)+1}"
            tokens.append((token, f"{mesa_text}.pdf"))

        # Buscar formularios ocultos con tokens
        for form in soup.find_all('form'):
            action = form.get('action', '')
            if 'descarga' in action.lower():
                token_input = form.find('input', {'name': 'token'})
                if token_input:
                    tokens.append((token_input.get('value'), f"acta_{len(tokens)+1}.pdf"))

        return tokens

    def consultar_puesto(self, departamento, municipio, zona, puesto):
        """
        Consulta un puesto de votación específico
        """
        url = f"{self.base_url}/consultar"

        data = {
            'depart': departamento,
            'municipal': municipio,
            'zona': zona,
            'puesto': puesto
        }

        try:
            response = self.session.post(url, data=data, timeout=30)
            if response.status_code == 200:
                print(f"[OK] Consulta exitosa: Depto {departamento}, Municipio {municipio}, Zona {zona}, Puesto {puesto}")
                return response.text
            else:
                print(f"[ERROR] Status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error en consulta: {e}")
            return None

    def descargar_acta(self, token, nombre_archivo=None):
        """
        Descarga un acta E14 usando el token
        """
        if nombre_archivo is None:
            nombre_archivo = f"acta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Limpiar nombre de archivo
        nombre_archivo = re.sub(r'[<>:"/\\|?*]', '_', nombre_archivo)

        url = f"{self.base_url}/descargae14"

        try:
            # Intentar con POST
            response = self.session.post(url, data={'token': token}, timeout=30)

            # Si falla, intentar con GET
            if response.status_code != 200:
                response = self.session.get(f"{url}?token={token}", timeout=30)

            if response.status_code == 200:
                # Verificar que sea un PDF
                content_type = response.headers.get('Content-Type', '')

                if 'pdf' in content_type.lower() or response.content[:4] == b'%PDF':
                    # Crear directorio si no existe
                    os.makedirs("actas_descargadas", exist_ok=True)

                    # Guardar el PDF
                    filepath = f"actas_descargadas/{nombre_archivo}"
                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    tamano_kb = len(response.content) / 1024
                    print(f"[OK] Descargada: {nombre_archivo} ({tamano_kb:.1f} KB)")

                    self.descargas.append({
                        'archivo': nombre_archivo,
                        'fecha': datetime.now().isoformat(),
                        'tamano_bytes': len(response.content),
                        'token': token[:20] + '...' if len(token) > 20 else token
                    })
                    return True
                else:
                    print(f"[WARN] Respuesta no es PDF: {nombre_archivo}")
                    # Guardar respuesta para debug
                    with open(f"debug_{nombre_archivo}.html", 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    return False
            else:
                print(f"[ERROR] Status {response.status_code}: {nombre_archivo}")
                self.errores.append({
                    'archivo': nombre_archivo,
                    'error': f"Status {response.status_code}",
                    'token': token
                })
                return False

        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout descargando {nombre_archivo}")
            self.errores.append({'archivo': nombre_archivo, 'error': 'Timeout'})
            return False
        except Exception as e:
            print(f"[ERROR] Error descargando {nombre_archivo}: {str(e)}")
            self.errores.append({'archivo': nombre_archivo, 'error': str(e)})
            return False

    def procesar_lote(self, tokens_y_nombres, delay=1.5):
        """
        Descarga múltiples actas
        tokens_y_nombres: lista de tuplas (token, nombre_archivo)
        delay: segundos de espera entre descargas
        """
        print(f"\n{'='*60}")
        print(f"  Iniciando descarga de {len(tokens_y_nombres)} actas")
        print(f"{'='*60}\n")

        exitosas = 0
        fallidas = 0

        for i, (token, nombre) in enumerate(tokens_y_nombres, 1):
            print(f"[{i}/{len(tokens_y_nombres)}] Procesando {nombre}...")

            if self.descargar_acta(token, nombre):
                exitosas += 1
            else:
                fallidas += 1

            # Esperar entre descargas para no sobrecargar el servidor
            if i < len(tokens_y_nombres):
                time.sleep(delay)

        print(f"\n{'='*60}")
        print(f"  RESUMEN")
        print(f"  - Exitosas: {exitosas}")
        print(f"  - Fallidas: {fallidas}")
        print(f"  - Total: {len(tokens_y_nombres)}")
        print(f"{'='*60}\n")

        # Guardar registro de descargas
        self.guardar_registro()

        return exitosas, fallidas

    def guardar_registro(self):
        """Guarda un registro en JSON de todas las descargas"""
        registro = {
            'fecha_ejecucion': datetime.now().isoformat(),
            'total_descargadas': len(self.descargas),
            'total_errores': len(self.errores),
            'descargas': self.descargas,
            'errores': self.errores
        }

        with open("registro_descargas.json", "w", encoding='utf-8') as f:
            json.dump(registro, f, indent=2, ensure_ascii=False)
        print("[OK] Registro guardado en: registro_descargas.json")

    def modo_interactivo(self):
        """Modo interactivo para seleccionar opciones"""
        print("\n" + "="*60)
        print("  DESCARGADOR DE ACTAS E14 - MODO INTERACTIVO")
        print("="*60 + "\n")

        # Obtener sesión
        if not self.obtener_sesion():
            print("[ERROR] No se pudo establecer conexion. Verifica tu internet.")
            return

        print("\nOpciones disponibles:")
        print("1. Descargar actas por tokens manuales")
        print("2. Explorar estructura del sitio")
        print("3. Salir")

        opcion = input("\nSelecciona opcion (1-3): ").strip()

        if opcion == "1":
            self.descargar_por_tokens_manuales()
        elif opcion == "2":
            self.explorar_sitio()
        else:
            print("Saliendo...")

    def descargar_por_tokens_manuales(self):
        """Permite ingresar tokens manualmente"""
        print("\n[INFO] Ingresa los tokens uno por uno.")
        print("[INFO] Escribe 'fin' cuando termines.\n")

        tokens = []
        contador = 1

        while True:
            token = input(f"Token {contador} (o 'fin'): ").strip()
            if token.lower() == 'fin':
                break
            if token:
                nombre = input(f"Nombre archivo (Enter para mesa_{contador}.pdf): ").strip()
                if not nombre:
                    nombre = f"mesa_{contador}.pdf"
                if not nombre.endswith('.pdf'):
                    nombre += '.pdf'
                tokens.append((token, nombre))
                contador += 1

        if tokens:
            self.procesar_lote(tokens)
        else:
            print("[INFO] No se ingresaron tokens.")

    def explorar_sitio(self):
        """Explora la estructura del sitio"""
        print("\n[INFO] Explorando sitio web...")

        response = self.session.get(f"{self.base_url}/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar selectores
            selects = soup.find_all('select')
            print(f"\n[INFO] Encontrados {len(selects)} selectores:")
            for select in selects:
                name = select.get('name', 'sin-nombre')
                options = len(select.find_all('option'))
                print(f"  - {name}: {options} opciones")

            # Buscar formularios
            forms = soup.find_all('form')
            print(f"\n[INFO] Encontrados {len(forms)} formularios:")
            for form in forms:
                action = form.get('action', 'sin-action')
                method = form.get('method', 'GET')
                print(f"  - {method} -> {action}")

            # Guardar HTML para análisis
            with open("pagina_principal.html", "w", encoding='utf-8') as f:
                f.write(response.text)
            print("\n[OK] HTML guardado en: pagina_principal.html")
        else:
            print(f"[ERROR] No se pudo acceder al sitio: {response.status_code}")


def main():
    """Función principal"""
    descargador = DescargadorActasE14()

    print("""
    ============================================================
      DESCARGADOR DE ACTAS E14
      Registraduria Nacional - Colombia
    ============================================================

    INSTRUCCIONES:
    1. Primero, abre el sitio en tu navegador
    2. Navega hasta el puesto de votacion deseado
    3. Abre las herramientas de desarrollador (F12)
    4. Ve a la pestana 'Network' (Red)
    5. Haz clic en una mesa para ver la solicitud
    6. Copia el token de la solicitud

    """)

    # Modo interactivo
    descargador.modo_interactivo()


if __name__ == "__main__":
    main()
