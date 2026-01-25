"""
E-14 Scraper Service para Registraduría Nacional.

Descarga y procesa formularios E-14 desde los portales de la Registraduría:
- https://e14_pres1v_2022.registraduria.gov.co/
- https://e14_congreso_2022.registraduria.gov.co/
- https://divulgacione14.registraduria.gov.co/

Características:
- Navegación por departamento/municipio/zona/puesto
- Manejo de CAPTCHA (manual o servicio externo)
- Rate limiting para evitar bloqueos
- Retry con backoff exponencial
- Registro de descargas para auditoría
"""
import hashlib
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)


class ElectionType(Enum):
    """Tipos de elección soportados."""
    PRESIDENCIA_1V_2022 = "e14_pres1v_2022"
    PRESIDENCIA_2V_2022 = "e14_pres2v_2022"
    CONGRESO_2022 = "e14_congreso_2022"
    CONSULTA_2026 = "e14_consulta_2026"  # Futuro


class CopyType(Enum):
    """Tipo de copia del E-14."""
    CLAVEROS = "claveros"
    DELEGADOS = "delegados"


@dataclass
class ScraperConfig:
    """Configuración del scraper."""
    # URLs base por tipo de elección
    base_urls: Dict[str, str] = field(default_factory=lambda: {
        "e14_pres1v_2022": "https://e14_pres1v_2022.registraduria.gov.co",
        "e14_pres2v_2022": "https://e14_pres2v_2022.registraduria.gov.co",
        "e14_congreso_2022": "https://e14_congreso_2022.registraduria.gov.co",
        "divulgacion": "https://divulgacione14.registraduria.gov.co",
    })

    # Rate limiting
    requests_per_minute: int = 30
    delay_between_requests: float = 2.0  # segundos

    # Retries
    max_retries: int = 3
    retry_backoff: float = 2.0  # multiplicador

    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 60.0

    # Storage
    download_dir: str = "downloads/e14"
    cache_dir: str = "cache/e14"

    # Headers
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class PollingLocation:
    """Ubicación de una mesa de votación."""
    dept_code: str
    dept_name: str
    muni_code: str
    muni_name: str
    zone_code: str
    zone_name: Optional[str] = None
    station_code: str = ""
    station_name: Optional[str] = None
    table_number: Optional[int] = None

    @property
    def location_id(self) -> str:
        """ID único de la ubicación."""
        return f"{self.dept_code}-{self.muni_code}-{self.zone_code}-{self.station_code}"

    @property
    def mesa_id(self) -> Optional[str]:
        """ID completo incluyendo mesa."""
        if self.table_number is not None:
            return f"{self.location_id}-{self.table_number:03d}"
        return None


@dataclass
class E14Download:
    """Registro de una descarga de E-14."""
    download_id: str
    election_type: str
    location: PollingLocation
    copy_type: CopyType
    table_number: int

    # Archivo
    filename: str
    filepath: str
    file_size: int
    sha256: str

    # Metadata
    downloaded_at: datetime
    source_url: str
    response_code: int

    # Estado
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ScraperState:
    """Estado del scraper para resumir descargas."""
    session_id: str
    election_type: str
    started_at: datetime
    last_activity: datetime

    # Progreso
    total_locations: int = 0
    processed_locations: int = 0
    total_tables: int = 0
    downloaded_tables: int = 0
    failed_tables: int = 0

    # Último punto
    last_dept: Optional[str] = None
    last_muni: Optional[str] = None
    last_zone: Optional[str] = None
    last_station: Optional[str] = None
    last_table: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'election_type': self.election_type,
            'started_at': self.started_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'progress': {
                'locations': f"{self.processed_locations}/{self.total_locations}",
                'tables': f"{self.downloaded_tables}/{self.total_tables}",
                'failed': self.failed_tables
            },
            'checkpoint': {
                'dept': self.last_dept,
                'muni': self.last_muni,
                'zone': self.last_zone,
                'station': self.last_station,
                'table': self.last_table
            }
        }


class E14Scraper:
    """
    Scraper para formularios E-14 de la Registraduría.

    Uso:
        scraper = E14Scraper(ElectionType.PRESIDENCIA_1V_2022)
        scraper.start_session()

        # Descargar por departamento
        downloads = scraper.download_department("11")  # Bogotá

        # O descargar mesa específica
        download = scraper.download_table(
            dept_code="11",
            muni_code="001",
            zone_code="01",
            station_code="0001",
            table_number=1
        )
    """

    def __init__(
        self,
        election_type: ElectionType,
        config: Optional[ScraperConfig] = None
    ):
        self.election_type = election_type
        self.config = config or ScraperConfig()

        self.base_url = self.config.base_urls.get(
            election_type.value,
            self.config.base_urls["divulgacion"]
        )

        self.client: Optional[httpx.Client] = None
        self.state: Optional[ScraperState] = None
        self.downloads: List[E14Download] = []

        # Crear directorios
        Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)

    def start_session(self) -> str:
        """Inicia una nueva sesión de scraping."""
        session_id = str(uuid.uuid4())[:8]

        self.client = httpx.Client(
            timeout=httpx.Timeout(
                connect=self.config.connect_timeout,
                read=self.config.read_timeout
            ),
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Referer": self.base_url
            },
            follow_redirects=True
        )

        self.state = ScraperState(
            session_id=session_id,
            election_type=self.election_type.value,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )

        # Obtener cookies iniciales
        try:
            response = self.client.get(self.base_url)
            logger.info(f"Session started: {session_id}, status={response.status_code}")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

        return session_id

    def close_session(self):
        """Cierra la sesión y guarda estado."""
        if self.client:
            self.client.close()
            self.client = None

        if self.state:
            self._save_state()
            logger.info(f"Session closed: {self.state.session_id}")

    def _save_state(self):
        """Guarda el estado para poder resumir."""
        if not self.state:
            return

        state_file = Path(self.config.cache_dir) / f"state_{self.state.session_id}.json"
        with open(state_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def _rate_limit(self):
        """Aplica rate limiting."""
        time.sleep(self.config.delay_between_requests)

    def _retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Ejecuta función con retry y backoff exponencial."""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                wait_time = self.config.retry_backoff ** attempt
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        raise last_exception

    # ============================================================
    # Métodos de navegación (obtener listas)
    # ============================================================

    def get_departments(self) -> List[Dict[str, str]]:
        """
        Obtiene la lista de departamentos disponibles.

        Returns:
            Lista de dicts con 'code' y 'name'
        """
        # Departamentos de Colombia (códigos DANE)
        # En producción, esto se extraería del HTML de la página
        departments = [
            {"code": "05", "name": "ANTIOQUIA"},
            {"code": "08", "name": "ATLÁNTICO"},
            {"code": "11", "name": "BOGOTÁ D.C."},
            {"code": "13", "name": "BOLÍVAR"},
            {"code": "15", "name": "BOYACÁ"},
            {"code": "17", "name": "CALDAS"},
            {"code": "18", "name": "CAQUETÁ"},
            {"code": "19", "name": "CAUCA"},
            {"code": "20", "name": "CESAR"},
            {"code": "23", "name": "CÓRDOBA"},
            {"code": "25", "name": "CUNDINAMARCA"},
            {"code": "27", "name": "CHOCÓ"},
            {"code": "41", "name": "HUILA"},
            {"code": "44", "name": "LA GUAJIRA"},
            {"code": "47", "name": "MAGDALENA"},
            {"code": "50", "name": "META"},
            {"code": "52", "name": "NARIÑO"},
            {"code": "54", "name": "NORTE DE SANTANDER"},
            {"code": "63", "name": "QUINDÍO"},
            {"code": "66", "name": "RISARALDA"},
            {"code": "68", "name": "SANTANDER"},
            {"code": "70", "name": "SUCRE"},
            {"code": "73", "name": "TOLIMA"},
            {"code": "76", "name": "VALLE DEL CAUCA"},
            {"code": "81", "name": "ARAUCA"},
            {"code": "85", "name": "CASANARE"},
            {"code": "86", "name": "PUTUMAYO"},
            {"code": "88", "name": "SAN ANDRÉS"},
            {"code": "91", "name": "AMAZONAS"},
            {"code": "94", "name": "GUAINÍA"},
            {"code": "95", "name": "GUAVIARE"},
            {"code": "97", "name": "VAUPÉS"},
            {"code": "99", "name": "VICHADA"},
        ]

        return departments

    def get_municipalities(self, dept_code: str) -> List[Dict[str, str]]:
        """
        Obtiene municipios de un departamento.

        En producción, hace request AJAX a la página.
        """
        if not self.client:
            raise RuntimeError("Session not started")

        # URL típica para obtener municipios (varía por portal)
        url = f"{self.base_url}/ajax/municipios"

        try:
            response = self.client.post(url, data={"depart": dept_code})
            self._rate_limit()

            if response.status_code == 200:
                # Parsear respuesta (puede ser HTML select options o JSON)
                return self._parse_select_options(response.text)
            else:
                logger.warning(f"Failed to get municipalities: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting municipalities: {e}")
            return []

    def get_zones(self, dept_code: str, muni_code: str) -> List[Dict[str, str]]:
        """Obtiene zonas de un municipio."""
        if not self.client:
            raise RuntimeError("Session not started")

        url = f"{self.base_url}/ajax/zonas"

        try:
            response = self.client.post(url, data={
                "depart": dept_code,
                "municipal": muni_code
            })
            self._rate_limit()

            if response.status_code == 200:
                return self._parse_select_options(response.text)
            return []

        except Exception as e:
            logger.error(f"Error getting zones: {e}")
            return []

    def get_stations(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str
    ) -> List[Dict[str, str]]:
        """Obtiene puestos de votación de una zona."""
        if not self.client:
            raise RuntimeError("Session not started")

        url = f"{self.base_url}/ajax/puestos"

        try:
            response = self.client.post(url, data={
                "depart": dept_code,
                "municipal": muni_code,
                "zona": zone_code
            })
            self._rate_limit()

            if response.status_code == 200:
                return self._parse_select_options(response.text)
            return []

        except Exception as e:
            logger.error(f"Error getting stations: {e}")
            return []

    def get_tables(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las mesas de un puesto de votación con sus tokens de descarga.
        """
        if not self.client:
            raise RuntimeError("Session not started")

        # Esta es la consulta principal que devuelve la lista de mesas
        url = f"{self.base_url}/consultar"

        try:
            response = self.client.post(url, data={
                "depart": dept_code,
                "municipal": muni_code,
                "zona": zone_code,
                "puesto": station_code
            })
            self._rate_limit()

            if response.status_code == 200:
                return self._parse_tables_response(response.text)
            return []

        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []

    def _parse_select_options(self, html: str) -> List[Dict[str, str]]:
        """Parsea opciones de un select HTML."""
        # Patrón para extraer <option value="X">Nombre</option>
        pattern = r'<option\s+value=["\']([^"\']+)["\']>([^<]+)</option>'
        matches = re.findall(pattern, html, re.IGNORECASE)

        return [
            {"code": code.strip(), "name": name.strip()}
            for code, name in matches
            if code.strip()  # Ignorar opciones vacías
        ]

    def _parse_tables_response(self, html: str) -> List[Dict[str, Any]]:
        """
        Parsea la respuesta que contiene las mesas y tokens.

        Busca botones/links con tokens para descargar E-14.
        """
        tables = []

        # Patrón para extraer tokens de descarga
        # Los tokens suelen estar en data-attributes o en onclick handlers
        patterns = [
            # data-token="xxx"
            r'data-token=["\']([^"\']+)["\'].*?mesa[^\d]*(\d+)',
            # onclick="descargar('xxx')"
            r'onclick=["\']descargar\(["\']([^"\']+)["\']\)["\'].*?mesa[^\d]*(\d+)',
            # href con token
            r'href=["\'][^"\']*token=([^"\'&]+)["\'].*?mesa[^\d]*(\d+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for token, table_num in matches:
                tables.append({
                    "table_number": int(table_num),
                    "token": token,
                    "copy_type": "claveros"  # Determinar del contexto
                })

        # Eliminar duplicados
        seen = set()
        unique_tables = []
        for t in tables:
            key = (t["table_number"], t["token"])
            if key not in seen:
                seen.add(key)
                unique_tables.append(t)

        return unique_tables

    # ============================================================
    # Métodos de descarga
    # ============================================================

    def download_table(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str,
        table_number: int,
        token: Optional[str] = None,
        copy_type: CopyType = CopyType.CLAVEROS
    ) -> Optional[E14Download]:
        """
        Descarga el E-14 de una mesa específica.

        Args:
            dept_code: Código de departamento
            muni_code: Código de municipio
            zone_code: Código de zona
            station_code: Código de puesto
            table_number: Número de mesa
            token: Token de descarga (si se conoce)
            copy_type: Tipo de copia (CLAVEROS o DELEGADOS)

        Returns:
            E14Download con información de la descarga o None si falla
        """
        if not self.client:
            raise RuntimeError("Session not started")

        location = PollingLocation(
            dept_code=dept_code,
            dept_name="",  # Se puede enriquecer después
            muni_code=muni_code,
            muni_name="",
            zone_code=zone_code,
            station_code=station_code,
            table_number=table_number
        )

        # Si no tenemos token, obtenerlo
        if not token:
            tables = self.get_tables(dept_code, muni_code, zone_code, station_code)
            table_info = next(
                (t for t in tables if t["table_number"] == table_number),
                None
            )
            if not table_info:
                logger.error(f"Could not find table {table_number} in station {station_code}")
                return None
            token = table_info["token"]

        # URL de descarga
        download_url = f"{self.base_url}/descargae14"

        try:
            response = self._retry_with_backoff(
                self.client.post,
                download_url,
                data={"token": token}
            )
            self._rate_limit()

            if response.status_code != 200:
                logger.error(f"Download failed: {response.status_code}")
                if self.state:
                    self.state.failed_tables += 1
                return None

            # Verificar que es un PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not response.content[:4] == b'%PDF':
                logger.error(f"Response is not a PDF: {content_type}")
                if self.state:
                    self.state.failed_tables += 1
                return None

            # Guardar archivo
            filename = f"E14_{dept_code}_{muni_code}_{zone_code}_{station_code}_{table_number:03d}_{copy_type.value}.pdf"
            filepath = Path(self.config.download_dir) / filename

            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Calcular hash
            sha256 = hashlib.sha256(response.content).hexdigest()

            # Crear registro
            download = E14Download(
                download_id=str(uuid.uuid4()),
                election_type=self.election_type.value,
                location=location,
                copy_type=copy_type,
                table_number=table_number,
                filename=filename,
                filepath=str(filepath),
                file_size=len(response.content),
                sha256=sha256,
                downloaded_at=datetime.utcnow(),
                source_url=download_url,
                response_code=response.status_code
            )

            self.downloads.append(download)

            # Actualizar estado
            if self.state:
                self.state.downloaded_tables += 1
                self.state.last_dept = dept_code
                self.state.last_muni = muni_code
                self.state.last_zone = zone_code
                self.state.last_station = station_code
                self.state.last_table = table_number
                self.state.last_activity = datetime.utcnow()

            logger.info(f"Downloaded: {filename} ({len(response.content)} bytes)")
            return download

        except Exception as e:
            logger.error(f"Error downloading table {table_number}: {e}")
            if self.state:
                self.state.failed_tables += 1
            return None

    def download_station(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str,
        copy_type: CopyType = CopyType.CLAVEROS
    ) -> List[E14Download]:
        """Descarga todos los E-14 de un puesto de votación."""
        downloads = []

        tables = self.get_tables(dept_code, muni_code, zone_code, station_code)
        logger.info(f"Found {len(tables)} tables in station {station_code}")

        for table_info in tables:
            download = self.download_table(
                dept_code=dept_code,
                muni_code=muni_code,
                zone_code=zone_code,
                station_code=station_code,
                table_number=table_info["table_number"],
                token=table_info["token"],
                copy_type=copy_type
            )
            if download:
                downloads.append(download)

        return downloads

    def download_zone(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        copy_type: CopyType = CopyType.CLAVEROS
    ) -> List[E14Download]:
        """Descarga todos los E-14 de una zona."""
        downloads = []

        stations = self.get_stations(dept_code, muni_code, zone_code)
        logger.info(f"Found {len(stations)} stations in zone {zone_code}")

        for station in stations:
            station_downloads = self.download_station(
                dept_code=dept_code,
                muni_code=muni_code,
                zone_code=zone_code,
                station_code=station["code"],
                copy_type=copy_type
            )
            downloads.extend(station_downloads)

        return downloads

    def download_municipality(
        self,
        dept_code: str,
        muni_code: str,
        copy_type: CopyType = CopyType.CLAVEROS
    ) -> List[E14Download]:
        """Descarga todos los E-14 de un municipio."""
        downloads = []

        zones = self.get_zones(dept_code, muni_code)
        logger.info(f"Found {len(zones)} zones in municipality {muni_code}")

        for zone in zones:
            zone_downloads = self.download_zone(
                dept_code=dept_code,
                muni_code=muni_code,
                zone_code=zone["code"],
                copy_type=copy_type
            )
            downloads.extend(zone_downloads)

        return downloads

    def download_department(
        self,
        dept_code: str,
        copy_type: CopyType = CopyType.CLAVEROS
    ) -> List[E14Download]:
        """Descarga todos los E-14 de un departamento."""
        downloads = []

        municipalities = self.get_municipalities(dept_code)
        logger.info(f"Found {len(municipalities)} municipalities in department {dept_code}")

        if self.state:
            self.state.total_locations = len(municipalities)

        for muni in municipalities:
            muni_downloads = self.download_municipality(
                dept_code=dept_code,
                muni_code=muni["code"],
                copy_type=copy_type
            )
            downloads.extend(muni_downloads)

            if self.state:
                self.state.processed_locations += 1
                self._save_state()

        return downloads

    # ============================================================
    # Métodos de utilidad
    # ============================================================

    def get_download_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de descargas."""
        if not self.downloads:
            return {"total": 0}

        total_size = sum(d.file_size for d in self.downloads)
        by_dept = {}
        by_copy_type = {}

        for d in self.downloads:
            dept = d.location.dept_code
            by_dept[dept] = by_dept.get(dept, 0) + 1

            copy = d.copy_type.value
            by_copy_type[copy] = by_copy_type.get(copy, 0) + 1

        return {
            "total": len(self.downloads),
            "total_size_mb": total_size / (1024 * 1024),
            "by_department": by_dept,
            "by_copy_type": by_copy_type,
            "failed": self.state.failed_tables if self.state else 0
        }

    def export_downloads_manifest(self, filepath: str):
        """Exporta manifiesto de descargas a JSON."""
        manifest = {
            "session_id": self.state.session_id if self.state else None,
            "election_type": self.election_type.value,
            "exported_at": datetime.utcnow().isoformat(),
            "stats": self.get_download_stats(),
            "downloads": [
                {
                    "download_id": d.download_id,
                    "mesa_id": d.location.mesa_id,
                    "filename": d.filename,
                    "sha256": d.sha256,
                    "file_size": d.file_size,
                    "downloaded_at": d.downloaded_at.isoformat(),
                    "copy_type": d.copy_type.value
                }
                for d in self.downloads
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest exported to {filepath}")


# ============================================================
# Función de conveniencia para uso rápido
# ============================================================

def download_e14(
    dept_code: str,
    muni_code: str,
    zone_code: str,
    station_code: str,
    table_number: int,
    election_type: ElectionType = ElectionType.PRESIDENCIA_1V_2022
) -> Optional[str]:
    """
    Descarga un E-14 específico y retorna la ruta del archivo.

    Uso:
        filepath = download_e14("11", "001", "01", "0001", 1)
        if filepath:
            print(f"Downloaded to {filepath}")
    """
    scraper = E14Scraper(election_type)

    try:
        scraper.start_session()
        download = scraper.download_table(
            dept_code=dept_code,
            muni_code=muni_code,
            zone_code=zone_code,
            station_code=station_code,
            table_number=table_number
        )
        return download.filepath if download else None

    finally:
        scraper.close_session()
