"""
E-14 Ingestion Pipeline.

Pipeline completo que:
1. Descarga E-14 desde Registraduría (scraper)
2. Procesa con OCR (Claude Vision)
3. Valida con reglas electorales
4. Crea items de revisión HITL si necesario
5. Guarda en base de datos

Diseñado para procesamiento masivo con paralelismo.
"""
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from services.e14_scraper import (
    E14Scraper,
    E14Download,
    ElectionType,
    CopyType,
    ScraperConfig,
)
from services.e14_ocr_service import (
    E14OCRService,
    get_e14_ocr_service,
    SourceType,
)
from services.qr_parser import parse_qr_barcode, QRParseStatus
from services.hitl_review import (
    ReviewQueue,
    ReviewItem,
    create_review_item_for_low_confidence,
    create_review_item_for_arithmetic_mismatch,
)
from services.parallel_ocr import (
    OCRWorkerPool,
    OCRJob,
    JobPriority,
    get_worker_manager,
)
from utils.metrics import (
    get_metrics_registry,
    OCRMetrics,
    ElectoralMetrics,
    ValidationMetrics,
)

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Etapas del pipeline."""
    DOWNLOAD = "DOWNLOAD"
    OCR = "OCR"
    VALIDATION = "VALIDATION"
    REVIEW = "REVIEW"
    DATABASE = "DATABASE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineStatus(Enum):
    """Estado del pipeline."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class PipelineJob:
    """Job individual en el pipeline."""
    job_id: str
    mesa_id: str

    # Ubicación
    dept_code: str
    muni_code: str
    zone_code: str
    station_code: str
    table_number: int

    # Estado
    stage: PipelineStage = PipelineStage.DOWNLOAD
    status: str = "PENDING"
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Archivos
    pdf_path: Optional[str] = None
    pdf_sha256: Optional[str] = None

    # Resultados
    ocr_result: Optional[Dict] = None
    validation_result: Optional[Dict] = None
    review_item_id: Optional[str] = None

    # Errores
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class PipelineConfig:
    """Configuración del pipeline."""
    # Scraper
    election_type: ElectionType = ElectionType.PRESIDENCIA_1V_2022
    copy_type: CopyType = CopyType.CLAVEROS

    # Workers
    download_workers: int = 2
    ocr_workers: int = 4
    validation_workers: int = 2

    # Limits
    max_retries: int = 3
    batch_size: int = 50

    # Paths
    download_dir: str = "downloads/e14"
    processed_dir: str = "processed/e14"
    failed_dir: str = "failed/e14"

    # Thresholds
    confidence_threshold: float = 0.7
    auto_approve_threshold: float = 0.95


class E14IngestionPipeline:
    """
    Pipeline de ingesta de E-14.

    Uso:
        pipeline = E14IngestionPipeline()
        pipeline.start()

        # Agregar jobs por departamento
        pipeline.queue_department("11")  # Bogotá

        # O por mesa específica
        pipeline.queue_table("11", "001", "01", "0001", 1)

        # Monitorear progreso
        stats = pipeline.get_stats()

        # Detener
        pipeline.stop()
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

        # Colas entre etapas
        self.download_queue: queue.Queue = queue.Queue()
        self.ocr_queue: queue.Queue = queue.Queue()
        self.validation_queue: queue.Queue = queue.Queue()
        self.review_queue: ReviewQueue = ReviewQueue()

        # Estado
        self.status = PipelineStatus.IDLE
        self.jobs: Dict[str, PipelineJob] = {}

        # Workers
        self._download_workers: List[threading.Thread] = []
        self._ocr_workers: List[threading.Thread] = []
        self._validation_workers: List[threading.Thread] = []

        # Servicios
        self.scraper: Optional[E14Scraper] = None
        self.ocr_service: Optional[E14OCRService] = None

        # Estadísticas
        self.stats = {
            'total_queued': 0,
            'downloaded': 0,
            'ocr_completed': 0,
            'validated': 0,
            'needs_review': 0,
            'completed': 0,
            'failed': 0,
        }

        # Control
        self._running = False
        self._lock = threading.Lock()

        # Crear directorios
        for dir_path in [self.config.download_dir, self.config.processed_dir, self.config.failed_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def start(self):
        """Inicia el pipeline."""
        if self._running:
            logger.warning("Pipeline already running")
            return

        self._running = True
        self.status = PipelineStatus.RUNNING

        # Iniciar scraper
        self.scraper = E14Scraper(self.config.election_type)
        self.scraper.start_session()

        # Iniciar OCR service
        self.ocr_service = get_e14_ocr_service()

        # Iniciar workers de descarga
        for i in range(self.config.download_workers):
            worker = threading.Thread(
                target=self._download_worker,
                name=f"download-worker-{i}",
                daemon=True
            )
            worker.start()
            self._download_workers.append(worker)

        # Iniciar workers de OCR
        for i in range(self.config.ocr_workers):
            worker = threading.Thread(
                target=self._ocr_worker,
                name=f"ocr-worker-{i}",
                daemon=True
            )
            worker.start()
            self._ocr_workers.append(worker)

        # Iniciar workers de validación
        for i in range(self.config.validation_workers):
            worker = threading.Thread(
                target=self._validation_worker,
                name=f"validation-worker-{i}",
                daemon=True
            )
            worker.start()
            self._validation_workers.append(worker)

        # Actualizar métricas
        OCRMetrics.set_workers_active(
            self.config.download_workers + self.config.ocr_workers,
            "ingestion_pipeline"
        )

        logger.info(f"Pipeline started with {self.config.download_workers} download, "
                   f"{self.config.ocr_workers} OCR, {self.config.validation_workers} validation workers")

    def stop(self):
        """Detiene el pipeline."""
        self._running = False
        self.status = PipelineStatus.STOPPED

        if self.scraper:
            self.scraper.close_session()

        OCRMetrics.set_workers_active(0, "ingestion_pipeline")
        logger.info("Pipeline stopped")

    def pause(self):
        """Pausa el pipeline."""
        self.status = PipelineStatus.PAUSED
        logger.info("Pipeline paused")

    def resume(self):
        """Reanuda el pipeline."""
        if self.status == PipelineStatus.PAUSED:
            self.status = PipelineStatus.RUNNING
            logger.info("Pipeline resumed")

    # ============================================================
    # Métodos para encolar trabajos
    # ============================================================

    def queue_table(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str,
        table_number: int,
        priority: JobPriority = JobPriority.NORMAL
    ) -> str:
        """Encola una mesa específica para procesamiento."""
        mesa_id = f"{dept_code}-{muni_code}-{zone_code}-{station_code}-{table_number:03d}"
        job_id = str(uuid.uuid4())

        job = PipelineJob(
            job_id=job_id,
            mesa_id=mesa_id,
            dept_code=dept_code,
            muni_code=muni_code,
            zone_code=zone_code,
            station_code=station_code,
            table_number=table_number,
        )

        with self._lock:
            self.jobs[job_id] = job
            self.stats['total_queued'] += 1

        self.download_queue.put((priority.value, job_id))

        logger.debug(f"Queued table {mesa_id} as job {job_id}")
        return job_id

    def queue_station(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str
    ) -> List[str]:
        """Encola todas las mesas de un puesto."""
        job_ids = []

        if not self.scraper:
            raise RuntimeError("Pipeline not started")

        tables = self.scraper.get_tables(dept_code, muni_code, zone_code, station_code)

        for table_info in tables:
            job_id = self.queue_table(
                dept_code, muni_code, zone_code, station_code,
                table_info["table_number"]
            )
            job_ids.append(job_id)

        logger.info(f"Queued {len(job_ids)} tables from station {station_code}")
        return job_ids

    def queue_zone(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str
    ) -> List[str]:
        """Encola todas las mesas de una zona."""
        job_ids = []

        if not self.scraper:
            raise RuntimeError("Pipeline not started")

        stations = self.scraper.get_stations(dept_code, muni_code, zone_code)

        for station in stations:
            station_jobs = self.queue_station(
                dept_code, muni_code, zone_code, station["code"]
            )
            job_ids.extend(station_jobs)

        logger.info(f"Queued {len(job_ids)} tables from zone {zone_code}")
        return job_ids

    def queue_municipality(
        self,
        dept_code: str,
        muni_code: str
    ) -> List[str]:
        """Encola todas las mesas de un municipio."""
        job_ids = []

        if not self.scraper:
            raise RuntimeError("Pipeline not started")

        zones = self.scraper.get_zones(dept_code, muni_code)

        for zone in zones:
            zone_jobs = self.queue_zone(dept_code, muni_code, zone["code"])
            job_ids.extend(zone_jobs)

        logger.info(f"Queued {len(job_ids)} tables from municipality {muni_code}")
        return job_ids

    def queue_department(self, dept_code: str) -> List[str]:
        """Encola todas las mesas de un departamento."""
        job_ids = []

        if not self.scraper:
            raise RuntimeError("Pipeline not started")

        municipalities = self.scraper.get_municipalities(dept_code)

        for muni in municipalities:
            muni_jobs = self.queue_municipality(dept_code, muni["code"])
            job_ids.extend(muni_jobs)

        logger.info(f"Queued {len(job_ids)} tables from department {dept_code}")
        return job_ids

    # ============================================================
    # Workers
    # ============================================================

    def _download_worker(self):
        """Worker de descarga."""
        while self._running:
            try:
                # Esperar por trabajo
                try:
                    priority, job_id = self.download_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Verificar si estamos pausados
                while self.status == PipelineStatus.PAUSED:
                    time.sleep(1)

                job = self.jobs.get(job_id)
                if not job:
                    continue

                job.stage = PipelineStage.DOWNLOAD
                job.started_at = datetime.utcnow()

                # Descargar E-14
                download = self.scraper.download_table(
                    job.dept_code,
                    job.muni_code,
                    job.zone_code,
                    job.station_code,
                    job.table_number,
                    copy_type=self.config.copy_type
                )

                if download:
                    job.pdf_path = download.filepath
                    job.pdf_sha256 = download.sha256

                    with self._lock:
                        self.stats['downloaded'] += 1

                    # Pasar a cola de OCR
                    self.ocr_queue.put(job_id)

                    # Métricas
                    ElectoralMetrics.track_form_received(
                        job.dept_code,
                        job.muni_code,
                        "CONSULTA",  # Determinar del tipo de elección
                        self.config.copy_type.value.upper()
                    )
                else:
                    self._handle_job_failure(job, "Download failed")

            except Exception as e:
                logger.error(f"Download worker error: {e}")

    def _ocr_worker(self):
        """Worker de OCR."""
        while self._running:
            try:
                try:
                    job_id = self.ocr_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                while self.status == PipelineStatus.PAUSED:
                    time.sleep(1)

                job = self.jobs.get(job_id)
                if not job or not job.pdf_path:
                    continue

                job.stage = PipelineStage.OCR

                # Procesar con OCR
                try:
                    payload = self.ocr_service.process_pdf_v2(
                        pdf_path=job.pdf_path,
                        source_type=SourceType.REGISTRADURIA
                    )

                    job.ocr_result = {
                        'extraction_id': payload.meta.get('extraction_id'),
                        'mesa_id': payload.document_header_extracted.mesa_id,
                        'overall_confidence': payload.meta.get('overall_confidence', 0),
                        'fields_count': len(payload.ocr_fields),
                        'needs_review_count': payload.meta.get('fields_needing_review', 0),
                        'qr_parsed': payload.meta.get('qr_parsed', False),
                    }

                    with self._lock:
                        self.stats['ocr_completed'] += 1

                    # Pasar a validación
                    self.validation_queue.put(job_id)

                except Exception as e:
                    self._handle_job_failure(job, f"OCR failed: {e}")

            except Exception as e:
                logger.error(f"OCR worker error: {e}")

    def _validation_worker(self):
        """Worker de validación."""
        while self._running:
            try:
                try:
                    job_id = self.validation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                while self.status == PipelineStatus.PAUSED:
                    time.sleep(1)

                job = self.jobs.get(job_id)
                if not job or not job.ocr_result:
                    continue

                job.stage = PipelineStage.VALIDATION

                # Evaluar si necesita revisión
                confidence = job.ocr_result.get('overall_confidence', 0)
                needs_review_count = job.ocr_result.get('needs_review_count', 0)

                if confidence >= self.config.auto_approve_threshold and needs_review_count == 0:
                    # Auto-aprobar
                    job.stage = PipelineStage.COMPLETED
                    job.status = "AUTO_APPROVED"
                    job.completed_at = datetime.utcnow()

                    with self._lock:
                        self.stats['completed'] += 1

                    # Mover a directorio de procesados
                    self._move_to_processed(job)

                    ElectoralMetrics.track_form_processed(
                        job.dept_code,
                        job.muni_code,
                        "CONSULTA",
                        "VALIDATED"
                    )

                elif confidence < self.config.confidence_threshold or needs_review_count > 0:
                    # Necesita revisión humana
                    job.stage = PipelineStage.REVIEW
                    job.status = "NEEDS_REVIEW"

                    # Crear item de revisión
                    review_item = create_review_item_for_low_confidence(
                        form_instance_id=job.ocr_result.get('extraction_id', job.job_id),
                        mesa_id=job.mesa_id,
                        cells=[],  # Se llenaría con los campos del OCR
                        threshold=self.config.confidence_threshold,
                        department=job.dept_code,
                        municipality=job.muni_code,
                        corporacion="CONSULTA"
                    )

                    if review_item:
                        self.review_queue.add_item(review_item)
                        job.review_item_id = review_item.review_id

                    with self._lock:
                        self.stats['needs_review'] += 1
                        self.stats['validated'] += 1

                else:
                    # Confianza media - validar pero marcar
                    job.stage = PipelineStage.COMPLETED
                    job.status = "VALIDATED_WITH_WARNINGS"
                    job.completed_at = datetime.utcnow()

                    with self._lock:
                        self.stats['completed'] += 1
                        self.stats['validated'] += 1

                    self._move_to_processed(job)

            except Exception as e:
                logger.error(f"Validation worker error: {e}")

    def _handle_job_failure(self, job: PipelineJob, error: str):
        """Maneja fallo de un job."""
        job.retry_count += 1
        job.error = error

        if job.retry_count < self.config.max_retries:
            # Reintentar
            logger.warning(f"Job {job.job_id} failed (attempt {job.retry_count}): {error}")
            self.download_queue.put((JobPriority.LOW.value, job.job_id))
        else:
            # Fallo definitivo
            job.stage = PipelineStage.FAILED
            job.status = "FAILED"
            job.completed_at = datetime.utcnow()

            with self._lock:
                self.stats['failed'] += 1

            self._move_to_failed(job)
            logger.error(f"Job {job.job_id} failed permanently: {error}")

    def _move_to_processed(self, job: PipelineJob):
        """Mueve archivo procesado a directorio de procesados."""
        if job.pdf_path and os.path.exists(job.pdf_path):
            dest = Path(self.config.processed_dir) / os.path.basename(job.pdf_path)
            os.rename(job.pdf_path, dest)
            job.pdf_path = str(dest)

    def _move_to_failed(self, job: PipelineJob):
        """Mueve archivo fallido a directorio de fallidos."""
        if job.pdf_path and os.path.exists(job.pdf_path):
            dest = Path(self.config.failed_dir) / os.path.basename(job.pdf_path)
            os.rename(job.pdf_path, dest)
            job.pdf_path = str(dest)

    # ============================================================
    # Estadísticas y monitoreo
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del pipeline."""
        with self._lock:
            return {
                'status': self.status.value,
                'queues': {
                    'download': self.download_queue.qsize(),
                    'ocr': self.ocr_queue.qsize(),
                    'validation': self.validation_queue.qsize(),
                    'review': len([i for i in self.review_queue.items if i.status.value == "PENDING"]),
                },
                'processed': dict(self.stats),
                'workers': {
                    'download': len(self._download_workers),
                    'ocr': len(self._ocr_workers),
                    'validation': len(self._validation_workers),
                }
            }

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Obtiene estado de un job específico."""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            'job_id': job.job_id,
            'mesa_id': job.mesa_id,
            'stage': job.stage.value,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error': job.error,
            'retry_count': job.retry_count,
            'ocr_confidence': job.ocr_result.get('overall_confidence') if job.ocr_result else None,
            'review_item_id': job.review_item_id,
        }


# ============================================================
# Singleton global
# ============================================================

_pipeline: Optional[E14IngestionPipeline] = None


def get_ingestion_pipeline() -> E14IngestionPipeline:
    """Obtiene el pipeline de ingesta global."""
    global _pipeline
    if _pipeline is None:
        _pipeline = E14IngestionPipeline()
    return _pipeline
