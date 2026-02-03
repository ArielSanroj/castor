"""
Módulo para cargar los datos de departamentos, municipios, zonas y puestos
desde la página de la Registraduría o desde archivos locales.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
import aiohttp
import structlog
from playwright.async_api import async_playwright

from config import settings

logger = structlog.get_logger()


class RegistraduriaDataLoader:
    """Carga la estructura de datos de la Registraduría"""

    def __init__(self):
        self.base_url = settings.base_url
        self.log = logger.bind(component="data_loader")

    async def load_from_page(self) -> List[Dict[str, Any]]:
        """
        Carga los datos navegando por la página de la Registraduría.
        Extrae la jerarquía: Departamentos -> Municipios -> Zonas -> Puestos
        """
        self.log.info("Cargando datos desde la Registraduría...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(self.base_url, wait_until='networkidle')

                # Extraer departamentos
                departamentos = await self._extract_departamentos(page)
                self.log.info(f"Encontrados {len(departamentos)} departamentos")

                # Para cada departamento, extraer municipios
                for dep in departamentos:
                    self.log.info(f"Procesando departamento: {dep['nombre']}")
                    dep['municipios'] = await self._extract_municipios(page, dep['id'])

                    # Para cada municipio, extraer zonas
                    for mun in dep['municipios']:
                        mun['zonas'] = await self._extract_zonas(page, dep['id'], mun['id'])

                        # Para cada zona, extraer puestos
                        for zona in mun['zonas']:
                            zona['puestos'] = await self._extract_puestos(
                                page, dep['id'], mun['id'], zona['id']
                            )

                return departamentos

            finally:
                await browser.close()

    async def _extract_departamentos(self, page) -> List[Dict[str, str]]:
        """Extrae la lista de departamentos del select"""
        await page.wait_for_selector('#selectDepto', timeout=15000)

        departamentos = await page.evaluate("""
            () => {
                const select = document.querySelector('#selectDepto');
                if (!select) return [];

                return Array.from(select.options)
                    .filter(opt => opt.value && opt.value !== '' && opt.value !== '0')
                    .map(opt => ({
                        id: opt.value,
                        nombre: opt.text.trim()
                    }));
            }
        """)
        return departamentos

    async def _extract_municipios(self, page, departamento_id: str) -> List[Dict[str, str]]:
        """Extrae municipios para un departamento dado"""
        try:
            # Seleccionar el departamento
            await page.select_option('#selectDepto', departamento_id)
            await asyncio.sleep(1.5)  # Esperar a que cargue via AJAX

            # Extraer municipios
            municipios = await page.evaluate("""
                () => {
                    const select = document.querySelector('#selectMpio');
                    if (!select) return [];

                    return Array.from(select.options)
                        .filter(opt => opt.value && opt.value !== '' && opt.value !== '0')
                        .map(opt => ({
                            id: opt.value,
                            nombre: opt.text.trim()
                        }));
                }
            """)
            return municipios

        except Exception as e:
            self.log.warning(f"Error extrayendo municipios para {departamento_id}", error=str(e))
            return []

    async def _extract_zonas(self, page, departamento_id: str, municipio_id: str) -> List[Dict[str, str]]:
        """Extrae zonas para un municipio dado"""
        try:
            # Seleccionar departamento y municipio
            await page.select_option('#selectDepto', departamento_id)
            await asyncio.sleep(1)
            await page.select_option('#selectMpio', municipio_id)
            await asyncio.sleep(1.5)

            # Extraer zonas
            zonas = await page.evaluate("""
                () => {
                    const select = document.querySelector('#selectZona');
                    if (!select) return [{ id: null, nombre: null }];

                    const options = Array.from(select.options)
                        .filter(opt => opt.value && opt.value !== '' && opt.value !== '0')
                        .map(opt => ({
                            id: opt.value,
                            nombre: opt.text.trim()
                        }));

                    return options.length > 0 ? options : [{ id: null, nombre: null }];
                }
            """)
            return zonas

        except Exception as e:
            self.log.warning(f"Error extrayendo zonas para {municipio_id}", error=str(e))
            return [{'id': None, 'nombre': None}]

    async def _extract_puestos(
        self,
        page,
        departamento_id: str,
        municipio_id: str,
        zona_id: Optional[str]
    ) -> List[Dict[str, str]]:
        """Extrae puestos de votación para una zona dada"""
        try:
            # Seleccionar departamento, municipio y zona
            await page.select_option('#selectDepto', departamento_id)
            await asyncio.sleep(1)
            await page.select_option('#selectMpio', municipio_id)
            await asyncio.sleep(1)

            if zona_id:
                await page.select_option('#selectZona', zona_id)
                await asyncio.sleep(1)

            # Extraer puestos
            puestos = await page.evaluate("""
                () => {
                    const select = document.querySelector('#selectPto');
                    if (!select) return [{ id: null, nombre: null }];

                    const options = Array.from(select.options)
                        .filter(opt => opt.value && opt.value !== '' && opt.value !== '0')
                        .map(opt => ({
                            id: opt.value,
                            nombre: opt.text.trim()
                        }));

                    return options.length > 0 ? options : [{ id: null, nombre: null }];
                }
            """)
            return puestos

        except Exception as e:
            self.log.warning(f"Error extrayendo puestos", error=str(e))
            return [{'id': None, 'nombre': None}]

    async def load_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Carga datos desde un archivo JSON local"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def save_to_file(self, data: List[Dict[str, Any]], filepath: str):
        """Guarda los datos a un archivo JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.log.info(f"Datos guardados en {filepath}")


# Datos de ejemplo para testing (Colombia - algunos departamentos)
SAMPLE_DEPARTAMENTOS = [
    {
        "id": "11",
        "nombre": "BOGOTA D.C.",
        "municipios": [
            {
                "id": "11001",
                "nombre": "BOGOTA",
                "zonas": [
                    {"id": "01", "nombre": "ZONA 1", "puestos": [
                        {"id": "001", "nombre": "PUESTO 1"},
                        {"id": "002", "nombre": "PUESTO 2"},
                    ]},
                    {"id": "02", "nombre": "ZONA 2", "puestos": [
                        {"id": "003", "nombre": "PUESTO 3"},
                    ]},
                ]
            }
        ]
    },
    {
        "id": "05",
        "nombre": "ANTIOQUIA",
        "municipios": [
            {
                "id": "05001",
                "nombre": "MEDELLIN",
                "zonas": [
                    {"id": "01", "nombre": "ZONA 1", "puestos": [
                        {"id": "001", "nombre": "PUESTO 1"},
                    ]},
                ]
            },
            {
                "id": "05088",
                "nombre": "BELLO",
                "zonas": [
                    {"id": "01", "nombre": "ZONA 1", "puestos": [
                        {"id": "001", "nombre": "PUESTO 1"},
                    ]},
                ]
            }
        ]
    },
]


async def load_all_data(use_cache: bool = True, cache_file: str = "departamentos_cache.json") -> List[Dict[str, Any]]:
    """
    Función principal para cargar todos los datos.
    Usa caché si está disponible para evitar scraping repetido.
    """
    loader = RegistraduriaDataLoader()

    if use_cache:
        try:
            data = await loader.load_from_file(cache_file)
            logger.info(f"Datos cargados desde caché: {cache_file}")
            return data
        except FileNotFoundError:
            logger.info("Caché no encontrado, cargando desde web...")

    # Cargar desde la web
    data = await loader.load_from_page()

    # Guardar caché
    await loader.save_to_file(data, cache_file)

    return data


if __name__ == "__main__":
    # Test: cargar datos y mostrar resumen
    async def test():
        data = await load_all_data()
        total_municipios = sum(len(d['municipios']) for d in data)
        print(f"Total departamentos: {len(data)}")
        print(f"Total municipios: {total_municipios}")

    asyncio.run(test())
