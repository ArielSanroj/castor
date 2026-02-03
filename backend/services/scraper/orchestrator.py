"""
Orchestrator for distributed E-14 scraping.
Manages task queue and worker coordination.
"""
import asyncio
import logging
import signal
import sys
from typing import Any, Dict, List, Optional, Type

try:
    import asyncpg
except ImportError:
    asyncpg = None

from .config import get_scraper_config, ScraperConfig
from .task_queue import TaskQueue, init_scraper_tables
from .e14_worker import E14Worker

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that coordinates workers and tasks.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or get_scraper_config()
        self.pool: Optional["asyncpg.Pool"] = None
        self.queue: Optional[TaskQueue] = None
        self.workers: List[asyncio.Task] = []
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize database connections and resources."""
        if asyncpg is None:
            raise ImportError("asyncpg is required for the orchestrator")

        logger.info("Initializing orchestrator...")

        # Create connection pool
        self.pool = await asyncpg.create_pool(
            host=self.config.db_host,
            port=self.config.db_port,
            database=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password,
            min_size=5,
            max_size=self.config.num_workers + 10
        )

        # Initialize tables
        await init_scraper_tables(self.config.database_url)

        # Create task queue
        self.queue = TaskQueue(self.pool)

        logger.info(f"Orchestrator initialized with {self.config.num_workers} workers")

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Starting graceful shutdown...")
        self.running = False
        self._shutdown_event.set()

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        # Close connection pool
        if self.pool:
            await self.pool.close()

        logger.info("Orchestrator shutdown complete")

    async def load_tasks_from_data(self, departamentos_data: List[Dict[str, Any]]) -> int:
        """
        Load initial tasks from department/municipality structure.
        """
        async with self.pool.acquire() as conn:
            # Check if tasks exist
            count = await conn.fetchval("SELECT COUNT(*) FROM scraper_task")
            if count > 0:
                logger.info(f"Found {count} existing tasks in database")
                return count

            # Build task list
            tasks_to_insert = []
            for dep in departamentos_data:
                for mun in dep.get('municipios', []):
                    zonas = mun.get('zonas', [])

                    if zonas and any(z.get('id') for z in zonas):
                        for zona in zonas:
                            puestos = zona.get('puestos', [])
                            if puestos and any(p.get('id') for p in puestos):
                                for puesto in puestos:
                                    for corporacion in ['senado', 'camara']:
                                        tasks_to_insert.append((
                                            dep['id'],
                                            mun['id'],
                                            zona.get('id', ''),
                                            puesto.get('id', ''),
                                            corporacion,
                                            'pending',
                                            5
                                        ))
                            else:
                                for corporacion in ['senado', 'camara']:
                                    tasks_to_insert.append((
                                        dep['id'],
                                        mun['id'],
                                        zona.get('id', ''),
                                        '',
                                        corporacion,
                                        'pending',
                                        5
                                    ))
                    else:
                        for corporacion in ['senado', 'camara']:
                            tasks_to_insert.append((
                                dep['id'],
                                mun['id'],
                                '',
                                '',
                                corporacion,
                                'pending',
                                5
                            ))

            # Batch insert
            batch_size = 1000
            for i in range(0, len(tasks_to_insert), batch_size):
                batch = tasks_to_insert[i:i + batch_size]
                await conn.executemany("""
                    INSERT INTO scraper_task
                    (dept_code, muni_code, zone_code, station_code, corporacion, status, priority)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, batch)
                logger.info(f"Inserted {min(i + batch_size, len(tasks_to_insert))}/{len(tasks_to_insert)} tasks")

            return len(tasks_to_insert)

    async def run_monitoring(self):
        """Monitoring loop that shows progress."""
        while self.running:
            stats = await self.queue.get_stats()

            total = stats['total'] or 1
            completed = stats['completed']
            percent = (completed / total) * 100

            logger.info(
                f"Scraping progress: {completed}/{total} ({percent:.1f}%) | "
                f"Pending: {stats['pending']} | In Progress: {stats['in_progress']} | "
                f"Failed: {stats['failed']} | Workers: {stats['active_workers']}"
            )

            # Save metrics
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scraper_metrics
                    (total_tasks, pending_tasks, in_progress_tasks, completed_tasks,
                     failed_tasks, active_workers)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, stats['total'], stats['pending'], stats['in_progress'],
                    stats['completed'], stats['failed'], stats['active_workers'])

            await asyncio.sleep(self.config.progress_update_interval)

    async def run_stale_task_checker(self):
        """Check for abandoned tasks periodically."""
        while self.running:
            released = await self.queue.release_stale_tasks(timeout_minutes=5)
            if released > 0:
                logger.warning(f"Released {released} stale tasks")
            await asyncio.sleep(60)

    async def start(self, worker_class: Type[E14Worker] = E14Worker):
        """
        Start the orchestrator with workers.
        """
        self.running = True

        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                asyncio.get_event_loop().add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        logger.info(f"Starting {self.config.num_workers} workers...")

        # Create workers
        for i in range(self.config.num_workers):
            worker_id = f"worker-{i:03d}"
            worker = worker_class(
                worker_id=worker_id,
                queue=self.queue,
                pool=self.pool,
                shutdown_event=self._shutdown_event
            )
            task = asyncio.create_task(worker.run())
            self.workers.append(task)

        # Start monitoring
        monitor_task = asyncio.create_task(self.run_monitoring())
        stale_checker_task = asyncio.create_task(self.run_stale_task_checker())

        # Wait for completion
        try:
            await asyncio.gather(*self.workers, monitor_task, stale_checker_task)
        except asyncio.CancelledError:
            logger.info("Orchestrator cancelled")
        finally:
            await self.shutdown()


async def run_orchestrator(
    worker_class: Type[E14Worker] = E14Worker,
    departamentos_data: Optional[List[Dict]] = None,
    config: Optional[ScraperConfig] = None
):
    """
    Main function to run the orchestrator.

    Args:
        worker_class: Worker class to use
        departamentos_data: Department/municipality data (optional if already loaded)
        config: Optional custom configuration
    """
    orchestrator = Orchestrator(config=config)

    try:
        await orchestrator.initialize()

        if departamentos_data:
            await orchestrator.load_tasks_from_data(departamentos_data)

        await orchestrator.start(worker_class)

    except Exception as e:
        logger.exception(f"Error in orchestrator: {e}")
        raise
    finally:
        await orchestrator.shutdown()


# CLI entry point
def main():
    """CLI entry point for the orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="E-14 Scraper Orchestrator")
    parser.add_argument("--workers", type=int, help="Number of workers")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--dept", type=str, help="Test specific department")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    config = get_scraper_config()
    if args.workers:
        config.num_workers = args.workers

    # Run
    asyncio.run(run_orchestrator(config=config))


if __name__ == "__main__":
    main()
