#!/usr/bin/env python3
"""
EXTRACTOR DE ESTRUCTURA - CONGRESO 2022
https://e14_congreso_2022.registraduria.gov.co/

Extrae TODA la jerarquía sin necesitar CAPTCHA:
Corporaciones -> Departamentos -> Municipios -> Zonas -> Puestos
"""

import requests
import json
import time
import re
import os
from datetime import datetime

class ExtractorCongreso2022:
    def __init__(self):
        self.base_url = "https://e14_congreso_2022.registraduria.gov.co"
        self.session = requests.Session()
        self.token = None
        self.estructura = {
            'fecha_extraccion': datetime.now().isoformat(),
            'sitio': 'e14_congreso_2022',
            'corporaciones': {}
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

    def obtener_corporaciones(self):
        """Obtiene lista de corporaciones"""
        response = self.session.post(
            f"{self.base_url}/getCorp",
            data={'corp': '', 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_departamentos(self, corp, cod_corp):
        """Obtiene departamentos de una corporación"""
        response = self.session.post(
            f"{self.base_url}/selectCorp",
            data={'corp': corp, 'codCorp': cod_corp, 'codDepto': '', 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_municipios(self, corp, cod_depto):
        """Obtiene municipios de un departamento"""
        response = self.session.post(
            f"{self.base_url}/selectDepto",
            data={'corp': corp, 'codDepto': cod_depto, 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_zonas(self, corp, cod_depto, cod_mpio):
        """Obtiene zonas de un municipio"""
        response = self.session.post(
            f"{self.base_url}/selectMpio",
            data={'corp': corp, 'codDepto': cod_depto, 'codMpio': cod_mpio, 'token': self.token},
            timeout=30
        )
        if response.status_code == 200:
            return self.extraer_opciones(response.text)
        return []

    def obtener_puestos(self, corp, cod_depto, cod_mpio, cod_zona):
        """Obtiene puestos de una zona"""
        response = self.session.post(
            f"{self.base_url}/selectZona",
            data={
                'corp': corp,
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
        print("  EXTRACCION CONGRESO 2022")
        print("  https://e14_congreso_2022.registraduria.gov.co")
        print("="*60 + "\n")

        if not self.obtener_token():
            return None

        # Obtener corporaciones
        corporaciones = self.obtener_corporaciones()
        print(f"[OK] {len(corporaciones)} corporaciones encontradas:")
        for c in corporaciones:
            print(f"    - {c['nombre']}")
        print()

        for corp_data in corporaciones:
            # Parsear código de corporación (ej: "SEN_1" -> corp="SEN", codCorp="1")
            partes = corp_data['codigo'].split('_')
            corp = partes[0]
            cod_corp = partes[1] if len(partes) > 1 else '1'
            nombre_corp = corp_data['nombre']

            print(f"\n{'='*60}")
            print(f"CORPORACION: {nombre_corp}")
            print(f"{'='*60}")

            self.estructura['corporaciones'][corp_data['codigo']] = {
                'nombre': nombre_corp,
                'departamentos': {}
            }

            # Obtener departamentos
            departamentos = self.obtener_departamentos(corp, cod_corp)
            print(f"[OK] {len(departamentos)} departamentos")

            for i, depto in enumerate(departamentos):
                cod_depto = depto['codigo']
                nombre_depto = depto['nombre']
                print(f"  [{i+1}/{len(departamentos)}] {nombre_depto}", end='', flush=True)

                self.estructura['corporaciones'][corp_data['codigo']]['departamentos'][cod_depto] = {
                    'nombre': nombre_depto,
                    'municipios': {}
                }

                try:
                    # Obtener municipios
                    municipios = self.obtener_municipios(corp, cod_depto)
                    puestos_depto = 0

                    for muni in municipios:
                        cod_mpio = muni['codigo']
                        nombre_mpio = muni['nombre']

                        self.estructura['corporaciones'][corp_data['codigo']]['departamentos'][cod_depto]['municipios'][cod_mpio] = {
                            'nombre': nombre_mpio,
                            'zonas': {}
                        }

                        try:
                            # Obtener zonas
                            zonas = self.obtener_zonas(corp, cod_depto, cod_mpio)

                            for zona in zonas:
                                cod_zona = zona['codigo']
                                nombre_zona = zona['nombre']

                                self.estructura['corporaciones'][corp_data['codigo']]['departamentos'][cod_depto]['municipios'][cod_mpio]['zonas'][cod_zona] = {
                                    'nombre': nombre_zona,
                                    'puestos': {}
                                }

                                try:
                                    # Obtener puestos
                                    puestos = self.obtener_puestos(corp, cod_depto, cod_mpio, cod_zona)

                                    for puesto in puestos:
                                        cod_puesto = puesto['codigo']
                                        nombre_puesto = puesto['nombre']

                                        self.estructura['corporaciones'][corp_data['codigo']]['departamentos'][cod_depto]['municipios'][cod_mpio]['zonas'][cod_zona]['puestos'][cod_puesto] = {
                                            'nombre': nombre_puesto
                                        }
                                        self.total_puestos += 1
                                        puestos_depto += 1

                                    time.sleep(0.05)

                                except Exception as e:
                                    self.errores.append(f"Puestos {corp}/{cod_depto}/{cod_mpio}/{cod_zona}: {e}")

                            time.sleep(0.05)

                        except Exception as e:
                            self.errores.append(f"Zonas {corp}/{cod_depto}/{cod_mpio}: {e}")

                    print(f" -> {puestos_depto} puestos")
                    time.sleep(0.1)

                except Exception as e:
                    print(f" -> ERROR")
                    self.errores.append(f"Municipios {corp}/{cod_depto}: {e}")

            # Guardar progreso parcial después de cada corporación
            self.guardar_estructura()

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

        with open('estructura_congreso_2022.json', 'w', encoding='utf-8') as f:
            json.dump(self.estructura, f, indent=2, ensure_ascii=False)

    def generar_lista_puestos(self):
        """Genera una lista plana de todos los puestos"""
        lista = []

        for cod_corp, corp in self.estructura.get('corporaciones', {}).items():
            for cod_depto, depto in corp.get('departamentos', {}).items():
                for cod_mpio, mpio in depto.get('municipios', {}).items():
                    for cod_zona, zona in mpio.get('zonas', {}).items():
                        for cod_puesto, puesto in zona.get('puestos', {}).items():
                            lista.append({
                                'corporacion_cod': cod_corp,
                                'corporacion': corp['nombre'],
                                'departamento_cod': cod_depto,
                                'departamento': depto['nombre'],
                                'municipio_cod': cod_mpio,
                                'municipio': mpio['nombre'],
                                'zona_cod': cod_zona,
                                'zona': zona['nombre'],
                                'puesto_cod': cod_puesto,
                                'puesto': puesto['nombre']
                            })

        with open('lista_puestos_congreso_2022.json', 'w', encoding='utf-8') as f:
            json.dump(lista, f, indent=2, ensure_ascii=False)

        print(f"[OK] Lista de {len(lista)} puestos guardada en lista_puestos_congreso_2022.json")
        return lista


def main():
    extractor = ExtractorCongreso2022()
    extractor.extraer_todo()
    extractor.generar_lista_puestos()


if __name__ == "__main__":
    main()
