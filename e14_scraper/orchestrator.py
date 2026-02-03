"""
Orquestador principal - Gestiona la cola de tareas y los workers
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog
from contextlib import asynccontextmanager
import signal
import sys

from config import settings
from models import TaskStatus, TaskPriority, ScrapingTask, init_database

logger = structlog.get_logger()


class TaskQueue:
    """Cola de tareas basada en PostgreSQL con soporte para trabajo distribuido"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self._lock_timeout = 30  # segundos para considerar una tarea abandonada

    async def claim_task(self, worker_id: str) -> Optional[ScrapingTask]:
        """
        Reclama la siguiente tarea disponible de forma atómica.
        Usa SELECT FOR UPDATE SKIP LOCKED para evitar conflictos entre workers.
        """
        async with self.pool.acquire() as conn:
            # Transacción atómica para reclamar tarea
            row = await conn.fetchrow("""
                UPDATE scraping_tasks
                SET
                    status = 'in_progress',
                    worker_id = $1,
                    attempts = attempts + 1,
                    updated_at = NOW()
                WHERE id = (
                    SELECT id FROM scraping_tasks
                    WHERE status IN ('pending', 'retry')
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
            """, worker_id)

            if row:
                return self._row_to_task(row)
            return None

    async def complete_task(
        self,
        task_id: int,
        worker_id: str,
        e14_data: Optional[Dict[str, Any]] = None,
        e14_url: Optional[str] = None
    ):
        """Marca una tarea como completada"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE scraping_tasks
                SET
                    status = 'completed',
                    completed_at = NOW(),
                    e14_data = $3,
                    e14_url = $4
                WHERE id = $1 AND worker_id = $2
            """, task_id, worker_id, e14_data, e14_url)

    async def fail_task(
        self,
        task_id: int,
        worker_id: str,
        error: str,
        should_retry: bool = True
    ):
        """Marca una tarea como fallida, con opción de reintento"""
        max_retries = settings.max_retries
        async with self.pool.acquire() as conn:
            # Obtener intentos actuales
            row = await conn.fetchrow(
                "SELECT attempts FROM scraping_tasks WHERE id = $1",
                task_id
            )
            attempts = row['attempts'] if row else 0

            new_status = 'retry' if (should_retry and attempts < max_retries) else 'failed'

            await conn.execute("""
                UPDATE scraping_tasks
                SET
                    status = $3,
                    last_error = $4,
                    worker_id = NULL
                WHERE id = $1 AND worker_id = $2
            """, task_id, worker_id, new_status, error)

    async def release_stale_tasks(self, timeout_minutes: int = 5):
        """Libera tareas que llevan demasiado tiempo en progreso (worker caído)"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE scraping_tasks
                SET
                    status = 'retry',
                    worker_id = NULL,
                    last_error = 'Task timeout - worker may have crashed'
                WHERE status = 'in_progress'
                AND updated_at < NOW() - INTERVAL '%s minutes'
            """ % timeout_minutes)
            return result

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales de la cola"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'retry') as retry,
                    COUNT(DISTINCT worker_id) FILTER (WHERE status = 'in_progress') as active_workers
                FROM scraping_tasks
            """)
            return dict(stats)

    async def get_progress_by_departamento(self) -> List[Dict[str, Any]]:
        """Obtiene progreso desglosado por departamento"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    departamento_nombre,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 2) as percent
                FROM scraping_tasks
                GROUP BY departamento_id, departamento_nombre
                ORDER BY departamento_nombre
            """)
            return [dict(row) for row in rows]

    def _row_to_task(self, row) -> ScrapingTask:
        """Convierte una fila de DB a objeto ScrapingTask"""
        return ScrapingTask(
            id=row['id'],
            departamento_id=row['departamento_id'],
            departamento_nombre=row['departamento_nombre'],
            municipio_id=row['municipio_id'],
            municipio_nombre=row['municipio_nombre'],
            zona_id=row['zona_id'],
            zona_nombre=row['zona_nombre'],
            puesto_id=row['puesto_id'],
            puesto_nombre=row['puesto_nombre'],
            corporacion=row['corporacion'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            attempts=row['attempts'],
            worker_id=row['worker_id'],
            last_error=row['last_error'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=row['completed_at'],
            e14_url=row['e14_url'],
            e14_data=row['e14_data']
        )


class Orchestrator:
    """Orquestador principal que coordina workers y tareas"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.queue: Optional[TaskQueue] = None
        self.workers: List[asyncio.Task] = []
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Inicializa conexiones y recursos"""
        logger.info("Inicializando orquestador...")

        # Crear pool de conexiones
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            min_size=5,
            max_size=settings.num_workers + 10
        )

        # Inicializar tablas si no existen
        await init_database(settings.database_url)

        # Crear cola de tareas
        self.queue = TaskQueue(self.pool)

        logger.info("Orquestador inicializado", num_workers=settings.num_workers)

    async def shutdown(self):
        """Cierre ordenado del orquestador"""
        logger.info("Iniciando cierre ordenado...")
        self.running = False
        self._shutdown_event.set()

        # Esperar a que los workers terminen
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        # Cerrar pool de conexiones
        if self.pool:
            await self.pool.close()

        logger.info("Orquestador cerrado correctamente")

    async def load_initial_tasks(self, departamentos_data: List[Dict[str, Any]]):
        """
        Carga las tareas iniciales desde la estructura de departamentos/municipios.
        Esta función debe ser llamada con los datos de la Registraduría.
        Crea tareas a nivel de municipio (zonas/puestos se descubren durante scraping).
        """
        async with self.pool.acquire() as conn:
            # Verificar si ya hay tareas
            count = await conn.fetchval("SELECT COUNT(*) FROM scraping_tasks")
            if count > 0:
                logger.info(f"Ya existen {count} tareas en la base de datos")
                return count

            # Insertar tareas en batch - una por municipio+corporación
            tasks_to_insert = []
            for dep in departamentos_data:
                for mun in dep.get('municipios', []):
                    zonas = mun.get('zonas', [])

                    # Si hay zonas definidas, crear tarea por cada zona
                    if zonas and any(z.get('id') for z in zonas):
                        for zona in zonas:
                            puestos = zona.get('puestos', [])
                            if puestos and any(p.get('id') for p in puestos):
                                # Hay puestos, crear tarea por puesto
                                for puesto in puestos:
                                    for corporacion in ['senado', 'camara']:
                                        tasks_to_insert.append((
                                            dep['id'], dep['nombre'],
                                            mun['id'], mun['nombre'],
                                            zona.get('id'), zona.get('nombre'),
                                            puesto.get('id'), puesto.get('nombre'),
                                            corporacion, 'pending', 5
                                        ))
                            else:
                                # Solo zona, sin puestos
                                for corporacion in ['senado', 'camara']:
                                    tasks_to_insert.append((
                                        dep['id'], dep['nombre'],
                                        mun['id'], mun['nombre'],
                                        zona.get('id'), zona.get('nombre'),
                                        None, None,
                                        corporacion, 'pending', 5
                                    ))
                    else:
                        # Sin zonas - crear tarea a nivel municipio
                        for corporacion in ['senado', 'camara']:
                            tasks_to_insert.append((
                                dep['id'], dep['nombre'],
                                mun['id'], mun['nombre'],
                                None, None,
                                None, None,
                                corporacion, 'pending', 5
                            ))

            # Insertar en batches de 1000
            batch_size = 1000
            for i in range(0, len(tasks_to_insert), batch_size):
                batch = tasks_to_insert[i:i + batch_size]
                await conn.executemany("""
                    INSERT INTO scraping_tasks
                    (departamento_id, departamento_nombre, municipio_id, municipio_nombre,
                     zona_id, zona_nombre, puesto_id, puesto_nombre, corporacion, status, priority)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, batch)
                logger.info(f"Insertadas {min(i + batch_size, len(tasks_to_insert))}/{len(tasks_to_insert)} tareas")

            return len(tasks_to_insert)

    async def run_monitoring(self):
        """Loop de monitoreo que muestra progreso periódicamente"""
        from rich.console import Console
        from rich.table import Table
        from rich.live import Live

        console = Console()

        while self.running:
            stats = await self.queue.get_stats()

            # Calcular velocidad
            total = stats['total'] or 1
            completed = stats['completed']
            percent = (completed / total) * 100

            # Crear tabla de progreso
            table = Table(title="📊 Estado del Scraping E-14")
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="green")

            table.add_row("Total tareas", str(stats['total']))
            table.add_row("Pendientes", str(stats['pending']))
            table.add_row("En progreso", str(stats['in_progress']))
            table.add_row("Completadas", f"{stats['completed']} ({percent:.1f}%)")
            table.add_row("Fallidas", str(stats['failed']))
            table.add_row("Reintento", str(stats['retry']))
            table.add_row("Workers activos", str(stats['active_workers']))

            console.clear()
            console.print(table)

            # Guardar métricas
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scraping_metrics
                    (total_tasks, pending_tasks, in_progress_tasks, completed_tasks,
                     failed_tasks, active_workers)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, stats['total'], stats['pending'], stats['in_progress'],
                    stats['completed'], stats['failed'], stats['active_workers'])

            await asyncio.sleep(settings.progress_update_interval)

    async def run_stale_task_checker(self):
        """Revisa periódicamente tareas abandonadas"""
        while self.running:
            await self.queue.release_stale_tasks(timeout_minutes=5)
            await asyncio.sleep(60)  # Revisar cada minuto

    async def start(self, worker_class):
        """
        Inicia el orquestador con los workers especificados.

        Args:
            worker_class: Clase del worker a usar (debe implementar run())
        """
        self.running = True

        # Configurar señales de terminación
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )

        logger.info("Iniciando workers...", count=settings.num_workers)

        # Crear workers
        for i in range(settings.num_workers):
            worker_id = f"worker-{i:03d}"
            worker = worker_class(
                worker_id=worker_id,
                queue=self.queue,
                pool=self.pool,
                shutdown_event=self._shutdown_event
            )
            task = asyncio.create_task(worker.run())
            self.workers.append(task)

        # Iniciar monitoreo
        monitor_task = asyncio.create_task(self.run_monitoring())
        stale_checker_task = asyncio.create_task(self.run_stale_task_checker())

        # Esperar a que terminen todos los workers o se solicite shutdown
        try:
            await asyncio.gather(*self.workers, monitor_task, stale_checker_task)
        except asyncio.CancelledError:
            logger.info("Orquestador cancelado")
        finally:
            await self.shutdown()


# Función de utilidad para ejecutar el orquestador
async def run_orchestrator(worker_class, departamentos_data: Optional[List[Dict]] = None):
    """
    Función principal para ejecutar el orquestador.

    Args:
        worker_class: Clase del worker a usar
        departamentos_data: Datos de departamentos/municipios (opcional si ya están cargados)
    """
    orchestrator = Orchestrator()

    try:
        await orchestrator.initialize()

        if departamentos_data:
            await orchestrator.load_initial_tasks(departamentos_data)

        await orchestrator.start(worker_class)

    except Exception as e:
        logger.exception("Error en orquestador", error=str(e))
        raise
    finally:
        await orchestrator.shutdown()
