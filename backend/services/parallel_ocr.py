"""
Parallel OCR Processing para E-14.

Implementa paralelismo real a múltiples niveles:
1. Multi-documento: Workers OCR paralelos por documento
2. Multi-página: Procesamiento concurrente de páginas
3. Multi-celda: Extracción paralela de celdas dentro de una página

Optimizado para diferentes tipos de elecciones:
- Presidencial/Consulta: 1-2 páginas → paralelo por documento
- Congreso (Cámara/Senado): 3-9 páginas → paralelo por página
- Territorial: Variable → paralelo adaptativo
"""
import asyncio
import logging
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.metrics import get_metrics_registry, OCRMetrics

logger = logging.getLogger(__name__)


class WorkerState(Enum):
    """Estado de un worker."""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class JobPriority(Enum):
    """Prioridad de job en la cola."""
    URGENT = 1      # Procesamiento inmediato (War Room)
    HIGH = 2        # Alta prioridad (Presidencial)
    NORMAL = 3      # Normal
    LOW = 4         # Baja (batch processing)
    BACKGROUND = 5  # Background (re-procesamiento)


@dataclass
class OCRJob:
    """Job de OCR para procesar."""
    job_id: str
    job_type: str  # DOCUMENT | PAGE | CELL

    # Datos de entrada
    input_data: Any  # PDF bytes, page image, cell image
    input_metadata: Dict[str, Any] = field(default_factory=dict)

    # Configuración
    priority: JobPriority = JobPriority.NORMAL
    corporacion: Optional[str] = None
    source_type: Optional[str] = None

    # Estado
    status: str = "PENDING"
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Resultado
    result: Optional[Any] = None
    error: Optional[str] = None

    # Callbacks
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None


@dataclass
class WorkerStats:
    """Estadísticas de un worker."""
    worker_id: str
    jobs_processed: int = 0
    jobs_failed: int = 0
    total_processing_time: float = 0.0
    last_job_time: Optional[datetime] = None
    state: WorkerState = WorkerState.IDLE

    @property
    def avg_processing_time(self) -> float:
        if self.jobs_processed == 0:
            return 0.0
        return self.total_processing_time / self.jobs_processed


class PriorityJobQueue:
    """Cola de jobs con priorización."""

    def __init__(self, maxsize: int = 1000):
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._job_count = 0
        self._pending_by_priority: Dict[JobPriority, int] = {p: 0 for p in JobPriority}

    def put(self, job: OCRJob, block: bool = True, timeout: Optional[float] = None):
        """Agrega un job a la cola."""
        # Priority tuple: (priority_value, timestamp, job)
        # Timestamp asegura FIFO dentro de la misma prioridad
        priority_tuple = (job.priority.value, time.time(), job)

        with self._lock:
            self._queue.put(priority_tuple, block=block, timeout=timeout)
            self._job_count += 1
            self._pending_by_priority[job.priority] += 1

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[OCRJob]:
        """Obtiene el siguiente job de mayor prioridad."""
        try:
            priority_tuple = self._queue.get(block=block, timeout=timeout)
            _, _, job = priority_tuple

            with self._lock:
                self._pending_by_priority[job.priority] -= 1

            return job
        except queue.Empty:
            return None

    def qsize(self) -> int:
        return self._queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_pending': self._queue.qsize(),
                'total_processed': self._job_count - self._queue.qsize(),
                'by_priority': dict(self._pending_by_priority)
            }


class OCRWorker:
    """Worker individual para procesamiento OCR."""

    def __init__(
        self,
        worker_id: str,
        job_queue: PriorityJobQueue,
        process_func: Callable[[OCRJob], Any],
        worker_pool: str = "default"
    ):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.process_func = process_func
        self.worker_pool = worker_pool

        self.stats = WorkerStats(worker_id=worker_id)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia el worker."""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Worker {self.worker_id} started")

    def stop(self):
        """Detiene el worker."""
        self._running = False
        self.stats.state = WorkerState.STOPPED
        logger.info(f"Worker {self.worker_id} stopping")

    def _run(self):
        """Loop principal del worker."""
        while self._running:
            try:
                # Obtener siguiente job (con timeout para poder verificar _running)
                job = self.job_queue.get(block=True, timeout=1.0)

                if job is None:
                    continue

                # Procesar job
                self._process_job(job)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                self.stats.state = WorkerState.ERROR
                time.sleep(1)  # Backoff on error

    def _process_job(self, job: OCRJob):
        """Procesa un job individual."""
        self.stats.state = WorkerState.PROCESSING
        job.status = "PROCESSING"
        job.started_at = datetime.utcnow()
        start_time = time.time()

        try:
            # Ejecutar procesamiento
            result = self.process_func(job)
            job.result = result
            job.status = "COMPLETED"

            # Actualizar estadísticas
            self.stats.jobs_processed += 1
            processing_time = time.time() - start_time
            self.stats.total_processing_time += processing_time
            self.stats.last_job_time = datetime.utcnow()

            # Callback de éxito
            if job.on_complete:
                job.on_complete(job)

            logger.debug(f"Worker {self.worker_id} completed job {job.job_id} in {processing_time:.2f}s")

        except Exception as e:
            job.status = "ERROR"
            job.error = str(e)
            self.stats.jobs_failed += 1

            # Callback de error
            if job.on_error:
                job.on_error(job, e)

            logger.error(f"Worker {self.worker_id} failed job {job.job_id}: {e}")

        finally:
            job.completed_at = datetime.utcnow()
            self.stats.state = WorkerState.IDLE


class OCRWorkerPool:
    """
    Pool de workers OCR con gestión de recursos.

    Soporta múltiples pools para diferentes tipos de procesamiento.
    """

    def __init__(
        self,
        pool_name: str = "default",
        num_workers: int = 4,
        max_queue_size: int = 1000,
        process_func: Optional[Callable] = None
    ):
        self.pool_name = pool_name
        self.num_workers = num_workers

        self.job_queue = PriorityJobQueue(maxsize=max_queue_size)
        self.workers: List[OCRWorker] = []
        self.process_func = process_func or self._default_process

        self._running = False
        self._lock = threading.Lock()

    def _default_process(self, job: OCRJob) -> Any:
        """Procesamiento por defecto (placeholder)."""
        raise NotImplementedError("Process function not configured")

    def start(self):
        """Inicia el pool de workers."""
        if self._running:
            return

        self._running = True

        for i in range(self.num_workers):
            worker = OCRWorker(
                worker_id=f"{self.pool_name}-worker-{i}",
                job_queue=self.job_queue,
                process_func=self.process_func,
                worker_pool=self.pool_name
            )
            worker.start()
            self.workers.append(worker)

        # Actualizar métricas
        OCRMetrics.set_workers_active(len(self.workers), self.pool_name)

        logger.info(f"Worker pool '{self.pool_name}' started with {self.num_workers} workers")

    def stop(self):
        """Detiene el pool de workers."""
        self._running = False

        for worker in self.workers:
            worker.stop()

        # Actualizar métricas
        OCRMetrics.set_workers_active(0, self.pool_name)

        logger.info(f"Worker pool '{self.pool_name}' stopped")

    def submit(self, job: OCRJob) -> str:
        """
        Envía un job al pool.

        Returns:
            job_id
        """
        self.job_queue.put(job)

        # Actualizar métricas de cola
        OCRMetrics.set_queue_depth(self.job_queue.qsize(), self.pool_name)

        return job.job_id

    def submit_batch(self, jobs: List[OCRJob]) -> List[str]:
        """Envía múltiples jobs."""
        job_ids = []
        for job in jobs:
            job_ids.append(self.submit(job))
        return job_ids

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del pool."""
        worker_stats = []
        for worker in self.workers:
            worker_stats.append({
                'worker_id': worker.worker_id,
                'state': worker.stats.state.value,
                'jobs_processed': worker.stats.jobs_processed,
                'jobs_failed': worker.stats.jobs_failed,
                'avg_processing_time': worker.stats.avg_processing_time
            })

        return {
            'pool_name': self.pool_name,
            'num_workers': self.num_workers,
            'running': self._running,
            'queue_stats': self.job_queue.get_stats(),
            'workers': worker_stats
        }


# ============================================================
# Parallel Page Processing
# ============================================================

async def process_pages_parallel(
    pages: List[bytes],
    process_page_func: Callable[[int, bytes], Dict],
    max_concurrent: int = 4
) -> List[Dict]:
    """
    Procesa múltiples páginas en paralelo usando asyncio.

    Args:
        pages: Lista de imágenes de página en bytes
        process_page_func: Función que procesa una página
        max_concurrent: Máximo de páginas concurrentes

    Returns:
        Lista de resultados por página
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(page_no: int, page_data: bytes) -> Dict:
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                process_page_func,
                page_no,
                page_data
            )

    tasks = [
        process_with_semaphore(i + 1, page)
        for i, page in enumerate(pages)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convertir excepciones a errores
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                'page_no': i + 1,
                'error': str(result),
                'status': 'ERROR'
            })
        else:
            processed_results.append(result)

    return processed_results


def process_pages_threaded(
    pages: List[bytes],
    process_page_func: Callable[[int, bytes], Dict],
    max_workers: int = 4
) -> List[Dict]:
    """
    Procesa múltiples páginas en paralelo usando ThreadPool.

    Args:
        pages: Lista de imágenes de página en bytes
        process_page_func: Función que procesa una página
        max_workers: Número de threads

    Returns:
        Lista de resultados por página (ordenados)
    """
    results = [None] * len(pages)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {
            executor.submit(process_page_func, i + 1, page): i
            for i, page in enumerate(pages)
        }

        for future in as_completed(future_to_page):
            page_index = future_to_page[future]
            try:
                results[page_index] = future.result()
            except Exception as e:
                results[page_index] = {
                    'page_no': page_index + 1,
                    'error': str(e),
                    'status': 'ERROR'
                }

    return results


# ============================================================
# Parallel Cell Processing
# ============================================================

def process_cells_parallel(
    cells: List[Tuple[str, bytes]],  # List of (cell_id, cell_image)
    process_cell_func: Callable[[str, bytes], Dict],
    max_workers: int = 8
) -> Dict[str, Dict]:
    """
    Procesa múltiples celdas en paralelo.

    Args:
        cells: Lista de tuplas (cell_id, cell_image)
        process_cell_func: Función que procesa una celda
        max_workers: Número de threads

    Returns:
        Diccionario cell_id -> resultado
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cell = {
            executor.submit(process_cell_func, cell_id, cell_image): cell_id
            for cell_id, cell_image in cells
        }

        for future in as_completed(future_to_cell):
            cell_id = future_to_cell[future]
            try:
                results[cell_id] = future.result()
            except Exception as e:
                results[cell_id] = {
                    'cell_id': cell_id,
                    'error': str(e),
                    'status': 'ERROR'
                }

    return results


# ============================================================
# Estrategias de paralelismo por tipo de elección
# ============================================================

def get_parallelism_strategy(
    corporacion: str,
    page_count: int,
    queue_depth: int = 0
) -> Dict[str, Any]:
    """
    Determina la estrategia de paralelismo óptima.

    Args:
        corporacion: Tipo de corporación
        page_count: Número de páginas del documento
        queue_depth: Profundidad actual de la cola

    Returns:
        Configuración de paralelismo
    """
    # Elecciones simples (1-2 páginas)
    if corporacion in ['CONSULTA', 'PRESIDENCIA', 'GOBERNACION', 'ALCALDIA'] or page_count <= 2:
        return {
            'strategy': 'DOCUMENT_PARALLEL',
            'description': 'Un worker por documento completo',
            'document_workers': 4,
            'page_workers': 1,
            'cell_workers': 1,
            'batch_size': 10
        }

    # Elecciones multi-página (Congreso, Asamblea, Concejo)
    if corporacion in ['CAMARA', 'SENADO', 'ASAMBLEA', 'CONCEJO'] or page_count > 2:
        # Calcular workers óptimos basado en páginas
        page_workers = min(page_count, 4)  # Max 4 páginas paralelas

        return {
            'strategy': 'PAGE_PARALLEL',
            'description': 'Procesamiento paralelo por página',
            'document_workers': 2,
            'page_workers': page_workers,
            'cell_workers': 4,
            'batch_size': 5
        }

    # Fallback
    return {
        'strategy': 'ADAPTIVE',
        'description': 'Estrategia adaptativa',
        'document_workers': 3,
        'page_workers': 2,
        'cell_workers': 2,
        'batch_size': 8
    }


# ============================================================
# Manager global de workers
# ============================================================

class OCRWorkerManager:
    """
    Manager global para pools de workers OCR.

    Gestiona múltiples pools especializados:
    - document_pool: Procesamiento de documentos completos
    - page_pool: Procesamiento de páginas individuales
    - cell_pool: Procesamiento de celdas individuales
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.pools: Dict[str, OCRWorkerPool] = {}
        self._initialized = True

    def create_pool(
        self,
        pool_name: str,
        num_workers: int,
        process_func: Callable,
        max_queue_size: int = 1000
    ) -> OCRWorkerPool:
        """Crea un nuevo pool de workers."""
        pool = OCRWorkerPool(
            pool_name=pool_name,
            num_workers=num_workers,
            max_queue_size=max_queue_size,
            process_func=process_func
        )
        self.pools[pool_name] = pool
        return pool

    def get_pool(self, pool_name: str) -> Optional[OCRWorkerPool]:
        """Obtiene un pool por nombre."""
        return self.pools.get(pool_name)

    def start_all(self):
        """Inicia todos los pools."""
        for pool in self.pools.values():
            pool.start()

    def stop_all(self):
        """Detiene todos los pools."""
        for pool in self.pools.values():
            pool.stop()

    def get_all_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de todos los pools."""
        return {
            name: pool.get_stats()
            for name, pool in self.pools.items()
        }


def get_worker_manager() -> OCRWorkerManager:
    """Obtiene el manager singleton."""
    return OCRWorkerManager()
