"""
PostgreSQL-backed task queue for distributed E-14 scraping.
Uses SELECT FOR UPDATE SKIP LOCKED for atomic task claiming.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None  # Will use sync version

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class ScrapingTask:
    """Represents a scraping task for a voting station."""
    id: int
    departamento_id: str
    departamento_nombre: str
    municipio_id: str
    municipio_nombre: str
    zona_id: Optional[str]
    zona_nombre: Optional[str]
    puesto_id: Optional[str]
    puesto_nombre: Optional[str]
    corporacion: str  # 'senado' o 'camara'
    status: TaskStatus
    priority: TaskPriority
    attempts: int
    worker_id: Optional[str]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    e14_url: Optional[str]
    e14_data: Optional[Dict[str, Any]]
    form_instance_id: Optional[int] = None


class TaskQueue:
    """
    PostgreSQL-backed task queue with distributed locking.
    Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions.
    """

    def __init__(self, pool: "asyncpg.Pool"):
        self.pool = pool
        self._lock_timeout = 30  # seconds

    async def claim_task(self, worker_id: str) -> Optional[ScrapingTask]:
        """
        Atomically claim the next available task.
        Uses SELECT FOR UPDATE SKIP LOCKED to avoid conflicts.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE scraper_task
                SET
                    status = 'in_progress',
                    worker_id = $1,
                    attempts = attempts + 1,
                    updated_at = NOW()
                WHERE id = (
                    SELECT id FROM scraper_task
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
        """Mark a task as completed with extracted data."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE scraper_task
                SET
                    status = 'completed',
                    completed_at = NOW(),
                    e14_data = $3,
                    e14_url = $4,
                    updated_at = NOW()
                WHERE id = $1 AND worker_id = $2
            """, task_id, worker_id, e14_data, e14_url)

    async def fail_task(
        self,
        task_id: int,
        worker_id: str,
        error: str,
        should_retry: bool = True,
        max_retries: int = 3
    ):
        """Mark a task as failed with optional retry."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT attempts FROM scraper_task WHERE id = $1",
                task_id
            )
            attempts = row['attempts'] if row else 0
            new_status = 'retry' if (should_retry and attempts < max_retries) else 'failed'

            await conn.execute("""
                UPDATE scraper_task
                SET
                    status = $3,
                    error_message = $4,
                    worker_id = NULL,
                    updated_at = NOW()
                WHERE id = $1 AND worker_id = $2
            """, task_id, worker_id, new_status, error)

    async def release_stale_tasks(self, timeout_minutes: int = 5) -> int:
        """Release tasks stuck in progress (crashed workers)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE scraper_task
                SET
                    status = 'retry',
                    worker_id = NULL,
                    error_message = 'Task timeout - worker may have crashed',
                    updated_at = NOW()
                WHERE status = 'in_progress'
                AND updated_at < NOW() - INTERVAL '%s minutes'
            """ % timeout_minutes)
            # Parse "UPDATE N" to get count
            count = int(result.split()[-1]) if result else 0
            return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
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
                FROM scraper_task
            """)
            return dict(stats)

    async def get_progress_by_dept(self) -> List[Dict[str, Any]]:
        """Get progress by department."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    dept_code,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / NULLIF(COUNT(*), 0), 2) as percent
                FROM scraper_task
                GROUP BY dept_code
                ORDER BY dept_code
            """)
            return [dict(row) for row in rows]

    async def add_task(
        self,
        dept_code: str,
        muni_code: str,
        zone_code: str,
        station_code: str,
        corporacion: str,
        priority: int = 5,
        form_instance_id: Optional[int] = None
    ) -> int:
        """Add a new scraping task."""
        async with self.pool.acquire() as conn:
            task_id = await conn.fetchval("""
                INSERT INTO scraper_task
                (dept_code, muni_code, zone_code, station_code, corporacion, priority, form_instance_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, dept_code, muni_code, zone_code, station_code, corporacion, priority, form_instance_id)
            return task_id

    async def add_tasks_batch(self, tasks: List[Dict[str, Any]]) -> int:
        """Add multiple tasks efficiently."""
        async with self.pool.acquire() as conn:
            records = [
                (
                    t['dept_code'],
                    t['muni_code'],
                    t.get('zone_code', ''),
                    t.get('station_code', ''),
                    t['corporacion'],
                    t.get('priority', 5),
                    t.get('form_instance_id')
                )
                for t in tasks
            ]
            await conn.executemany("""
                INSERT INTO scraper_task
                (dept_code, muni_code, zone_code, station_code, corporacion, priority, form_instance_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, records)
            return len(records)

    def _row_to_task(self, row) -> ScrapingTask:
        """Convert database row to ScrapingTask object."""
        return ScrapingTask(
            id=row['id'],
            departamento_id=row.get('dept_code', ''),
            departamento_nombre=row.get('dept_code', ''),  # Simplified
            municipio_id=row.get('muni_code', ''),
            municipio_nombre=row.get('muni_code', ''),
            zona_id=row.get('zone_code'),
            zona_nombre=row.get('zone_code'),
            puesto_id=row.get('station_code'),
            puesto_nombre=row.get('station_code'),
            corporacion=row['corporacion'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            attempts=row['attempts'],
            worker_id=row.get('worker_id'),
            last_error=row.get('error_message'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            completed_at=row.get('completed_at'),
            e14_url=row.get('e14_url'),
            e14_data=row.get('e14_data'),
            form_instance_id=row.get('form_instance_id'),
        )


# SQL for creating tables (to be used in migrations)
CREATE_TABLES_SQL = """
-- Scraper task queue table
CREATE TABLE IF NOT EXISTS scraper_task (
    id SERIAL PRIMARY KEY,
    form_instance_id INTEGER REFERENCES form_instance(id) ON DELETE SET NULL,
    dept_code VARCHAR(3) NOT NULL,
    muni_code VARCHAR(3) NOT NULL,
    zone_code VARCHAR(3) DEFAULT '',
    station_code VARCHAR(4) DEFAULT '',
    corporacion VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    attempts INTEGER DEFAULT 0,
    worker_id VARCHAR(50),
    error_message TEXT,
    e14_url TEXT,
    e14_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'retry'))
);

-- Index for efficient task claiming
CREATE INDEX IF NOT EXISTS idx_scraper_task_status
ON scraper_task(status, priority DESC, created_at);

-- Index for worker lookup
CREATE INDEX IF NOT EXISTS idx_scraper_task_worker
ON scraper_task(worker_id) WHERE status = 'in_progress';

-- Index for progress by department
CREATE INDEX IF NOT EXISTS idx_scraper_task_dept
ON scraper_task(dept_code);

-- Worker sessions tracking
CREATE TABLE IF NOT EXISTS scraper_worker_session (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    proxy_address VARCHAR(200),
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_worker_active
ON scraper_worker_session(is_active, worker_id);

-- Metrics table
CREATE TABLE IF NOT EXISTS scraper_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    total_tasks INTEGER,
    pending_tasks INTEGER,
    in_progress_tasks INTEGER,
    completed_tasks INTEGER,
    failed_tasks INTEGER,
    active_workers INTEGER,
    avg_task_duration_ms INTEGER,
    captchas_solved INTEGER
);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_scraper_task_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_scraper_task_updated_at ON scraper_task;
CREATE TRIGGER trigger_scraper_task_updated_at
    BEFORE UPDATE ON scraper_task
    FOR EACH ROW
    EXECUTE FUNCTION update_scraper_task_updated_at();
"""


async def init_scraper_tables(db_url: str):
    """Initialize scraper tables in database."""
    if asyncpg is None:
        raise ImportError("asyncpg required for async database operations")

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(CREATE_TABLES_SQL)
        logger.info("Scraper tables initialized successfully")
    finally:
        await conn.close()
