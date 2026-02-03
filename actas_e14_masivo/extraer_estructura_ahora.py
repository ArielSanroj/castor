#!/usr/bin/env python3
"""
EXTRACTOR DE ESTRUCTURA ELECTORAL
Extrae TODA la jerarquía sin necesitar CAPTCHA:
Departamentos -> Municipios -> Zonas -> Puestos

El CAPTCHA solo se necesita para el paso final (consultar mesas)
"""

import requests
import json
import time
import re
import os
from datetime import datetime

class ExtractorEstructura:
    def __init__(self):
        self.base_url = "https://e14_pres1v_2022.registraduria.gov.co"
        self.session = requests.Session()
        self.token = None
        self.estructura = {
            'fecha_extraccion': datetime.now().isoformat(),
            'departamentos': {}
        }
        self.total_puestos = 0
        self.errores = []

    def obtener_token(self):
        """Obtiene token CSRF"""
        try:
            response = self.session.get(f"{self.base_url}/auth/csrf", timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                print(f"[OK] Token obtenido")
                return True
        except Exception as e:
            print(f"[ERROR] No se pudo obtener token: {e}")
        return False

    def extraer_opciones(self, html):
        """Extrae opciones de un HTML de select"""
        opciones = []
        matches = re.findall(r'<option\s+value="([^"]*)"[^>]*>\s*([^<]+)</option>', html, re.IGNORECASE)
        for valor, texto in matches:
            if valor.strip():
                opciones.append({
                    'codigo': valor.strip(),
                    'nombre': texto.strip()
                })
        return opciones

    def obtener_departamentos(self):
        """Obtiene lista de departamentos"""
        response = self.session.post(
            f"{self.base_url}/selectCorp",
            data={'corp': 'PRE', 'codCorp': '1', 'codDepto': '', 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_municipios(self, cod_depto):
        """Obtiene municipios de un departamento"""
        response = self.session.post(
            f"{self.base_url}/selectDepto",
            data={'corp': 'PRE', 'codDepto': cod_depto, 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_zonas(self, cod_depto, cod_mpio):
        """Obtiene zonas de un municipio"""
        response = self.session.post(
            f"{self.base_url}/selectMpio",
            data={'corp': 'PRE', 'codDepto': cod_depto, 'codMpio': cod_mpio, 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_puestos(self, cod_depto, cod_mpio, cod_zona):
        """Obtiene puestos de una zona"""
        response = self.session.post(
            f"{self.base_url}/selectZona",
            data={
                'corp': 'PRE',
                'codDepto': cod_depto,
                'codMpio': cod_mpio,
                'codZona': cod_zona,
                'token': self.token
            },
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def extraer_todo(self):
        """Extrae toda la estructura electoral"""
        print("\n" + "="*60)
        print("  EXTRACCION DE ESTRUCTURA ELECTORAL")
        print("  (Sin necesidad de CAPTCHA)")
        print("="*60 + "\n")

        if not self.obtener_token():
            return None

        # Obtener departamentos
        departamentos = self.obtener_departamentos()
        print(f"[OK] {len(departamentos)} departamentos encontrados\n")

        for i, depto in enumerate(departamentos):
            cod_depto = depto['codigo']
            nombre_depto = depto['nombre']
            print(f"[{i+1}/{len(departamentos)}] {nombre_depto}")

            self.estructura['departamentos'][cod_depto] = {
                'nombre': nombre_depto,
                'municipios': {}
            }

            try:
                # Obtener municipios
                municipios = self.obtener_municipios(cod_depto)
                print(f"    Municipios: {len(municipios)}")

                for muni in municipios:
                    cod_mpio = muni['codigo']
                    nombre_mpio = muni['nombre']

                    self.estructura['departamentos'][cod_depto]['municipios'][cod_mpio] = {
                        'nombre': nombre_mpio,
                        'zonas': {}
                    }

                    try:
                        # Obtener zonas
                        zonas = self.obtener_zonas(cod_depto, cod_mpio)

                        for zona in zonas:
                            cod_zona = zona['codigo']
                            nombre_zona = zona['nombre']

                            self.estructura['departamentos'][cod_depto]['municipios'][cod_mpio]['zonas'][cod_zona] = {
                                'nombre': nombre_zona,
                                'puestos': {}
                            }

                            try:
                                # Obtener puestos
                                puestos = self.obtener_puestos(cod_depto, cod_mpio, cod_zona)

                                for puesto in puestos:
                                    cod_puesto = puesto['codigo']
                                    nombre_puesto = puesto['nombre']

                                    self.estructura['departamentos'][cod_depto]['municipios'][cod_mpio]['zonas'][cod_zona]['puestos'][cod_puesto] = {
                                        'nombre': nombre_puesto
                                    }
                                    self.total_puestos += 1

                                time.sleep(0.1)  # Pequeña pausa

                            except Exception as e:
                                self.errores.append(f"Puestos {cod_depto}/{cod_mpio}/{cod_zona}: {e}")

                        time.sleep(0.1)

                    except Exception as e:
                        self.errores.append(f"Zonas {cod_depto}/{cod_mpio}: {e}")

                time.sleep(0.2)

            except Exception as e:
                self.errores.append(f"Municipios {cod_depto}: {e}")

            # Guardar progreso parcial
            self.guardar_estructura()

            print(f"    Puestos acumulados: {self.total_puestos}")

        print(f"\n{'='*60}")
        print(f"  EXTRACCION COMPLETADA")
        print(f"  Total puestos: {self.total_puestos}")
        print(f"  Errores: {len(self.errores)}")
        print(f"{'='*60}\n")

        return self.estructura

    def guardar_estructura(self):
        """Guarda la estructura a archivo"""
        self.estructura['total_puestos'] = self.total_puestos
        self.estructura['errores'] = self.errores

        with open('estructura_electoral.json', 'w', encoding='utf-8') as f:
            json.dump(self.estructura, f, indent=2, ensure_ascii=False)

    def generar_lista_puestos(self):
        """Genera una lista plana de todos los puestos para facilitar el scraping"""
        lista = []

        for cod_depto, depto in self.estructura.get('departamentos', {}).items():
            for cod_mpio, mpio in depto.get('municipios', {}).items():
                for cod_zona, zona in mpio.get('zonas', {}).items():
                    for cod_puesto, puesto in zona.get('puestos', {}).items():
                        lista.append({
                            'departamento_cod': cod_depto,
                            'departamento': depto['nombre'],
                            'municipio_cod': cod_mpio,
                            'municipio': mpio['nombre'],
                            'zona_cod': cod_zona,
                            'zona': zona['nombre'],
                            'puesto_cod': cod_puesto,
                            'puesto': puesto['nombre']
                        })

        with open('lista_puestos.json', 'w', encoding='utf-8') as f:
            json.dump(lista, f, indent=2, ensure_ascii=False)

        print(f"[OK] Lista de {len(lista)} puestos guardada en lista_puestos.json")
        return lista


def main():
    extractor = ExtractorEstructura()
    extractor.extraer_todo()
    extractor.generar_lista_puestos()


if __name__ == "__main__":
    main()
