"""
Modelos de base de datos para el orquestador E-14
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import asyncpg
from dataclasses import dataclass


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class TaskPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class ScrapingTask:
    """Representa una tarea de scraping (un puesto de votación)"""
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


@dataclass
class E14Result:
    """Resultado extraído de un formulario E-14"""
    task_id: int
    mesa_numero: str
    total_votos: int
    votos_blancos: int
    votos_nulos: int
    votos_no_marcados: int
    votos_por_partido: Dict[str, int]
    imagen_url: Optional[str]
    imagen_path: Optional[str]
    raw_data: Dict[str, Any]
    extracted_at: datetime


# SQL para crear las tablas
CREATE_TABLES_SQL = """
-- Tabla de tareas de scraping
CREATE TABLE IF NOT EXISTS scraping_tasks (
    id SERIAL PRIMARY KEY,
    departamento_id VARCHAR(10) NOT NULL,
    departamento_nombre VARCHAR(100) NOT NULL,
    municipio_id VARCHAR(10) NOT NULL,
    municipio_nombre VARCHAR(100) NOT NULL,
    zona_id VARCHAR(10),
    zona_nombre VARCHAR(100),
    puesto_id VARCHAR(20),
    puesto_nombre VARCHAR(200),
    corporacion VARCHAR(20) NOT NULL DEFAULT 'senado',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 5,
    attempts INTEGER NOT NULL DEFAULT 0,
    worker_id VARCHAR(50),
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    e14_url TEXT,
    e14_data JSONB,

    -- Índices para búsqueda rápida
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'retry'))
);

-- Índices para el orquestador
CREATE INDEX IF NOT EXISTS idx_tasks_status ON scraping_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority_status ON scraping_tasks(priority DESC, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_tasks_worker ON scraping_tasks(worker_id) WHERE status = 'in_progress';
CREATE INDEX IF NOT EXISTS idx_tasks_departamento ON scraping_tasks(departamento_id);
CREATE INDEX IF NOT EXISTS idx_tasks_municipio ON scraping_tasks(municipio_id);

-- Tabla de resultados E-14
CREATE TABLE IF NOT EXISTS e14_results (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES scraping_tasks(id),
    mesa_numero VARCHAR(20),
    total_votos INTEGER,
    votos_blancos INTEGER,
    votos_nulos INTEGER,
    votos_no_marcados INTEGER,
    votos_por_partido JSONB,
    imagen_url TEXT,
    imagen_path TEXT,
    raw_data JSONB,
    extracted_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES scraping_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_results_task ON e14_results(task_id);

-- Tabla de sesiones de workers
CREATE TABLE IF NOT EXISTS worker_sessions (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    proxy_address VARCHAR(200),
    cookies JSONB,
    captcha_score FLOAT,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_worker_active ON worker_sessions(is_active, worker_id);

-- Tabla de progreso y métricas
CREATE TABLE IF NOT EXISTS scraping_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    total_tasks INTEGER,
    pending_tasks INTEGER,
    in_progress_tasks INTEGER,
    completed_tasks INTEGER,
    failed_tasks INTEGER,
    active_workers INTEGER,
    avg_task_duration_ms INTEGER,
    captchas_solved INTEGER,
    requests_per_minute FLOAT
);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para updated_at
DROP TRIGGER IF EXISTS update_scraping_tasks_updated_at ON scraping_tasks;
CREATE TRIGGER update_scraping_tasks_updated_at
    BEFORE UPDATE ON scraping_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


async def init_database(db_url: str):
    """Inicializa la base de datos con las tablas necesarias"""
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(CREATE_TABLES_SQL)
        print("✓ Base de datos inicializada correctamente")
    finally:
        await conn.close()
