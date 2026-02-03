-- Migration: Add E-14 Scraper Tables
-- Date: 2025-02-01
-- Description: Creates tables for distributed E-14 scraping task queue

-- ============================================================
-- Scraper Task Queue
-- ============================================================

CREATE TABLE IF NOT EXISTS scraper_task (
    id SERIAL PRIMARY KEY,

    -- Link to form instance if available
    form_instance_id INTEGER REFERENCES form_instance(id) ON DELETE SET NULL,

    -- Location codes
    dept_code VARCHAR(3) NOT NULL,
    muni_code VARCHAR(3) NOT NULL,
    zone_code VARCHAR(3) DEFAULT '',
    station_code VARCHAR(4) DEFAULT '',

    -- Election type
    corporacion VARCHAR(20) NOT NULL,  -- senado, camara, etc.

    -- Task status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    priority INTEGER DEFAULT 5 NOT NULL,
    attempts INTEGER DEFAULT 0 NOT NULL,

    -- Worker assignment
    worker_id VARCHAR(50),
    error_message TEXT,

    -- Results
    e14_url TEXT,
    e14_data JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_scraper_task_status CHECK (
        status IN ('pending', 'in_progress', 'completed', 'failed', 'retry')
    )
);

-- Indexes for efficient task claiming
CREATE INDEX IF NOT EXISTS idx_scraper_task_status_priority
ON scraper_task(status, priority DESC, created_at)
WHERE status IN ('pending', 'retry');

CREATE INDEX IF NOT EXISTS idx_scraper_task_worker
ON scraper_task(worker_id)
WHERE status = 'in_progress';

CREATE INDEX IF NOT EXISTS idx_scraper_task_dept
ON scraper_task(dept_code);

CREATE INDEX IF NOT EXISTS idx_scraper_task_corporacion
ON scraper_task(corporacion);

-- ============================================================
-- Scraper Results
-- ============================================================

CREATE TABLE IF NOT EXISTS scraper_result (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES scraper_task(id) ON DELETE CASCADE,

    -- Mesa info
    mesa_numero VARCHAR(20),
    total_votos INTEGER,
    votos_blancos INTEGER,
    votos_nulos INTEGER,
    votos_no_marcados INTEGER,

    -- Results data
    votos_por_partido JSONB,
    imagen_url TEXT,
    imagen_path TEXT,
    raw_data JSONB,

    -- Timestamps
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scraper_result_task
ON scraper_result(task_id);

-- ============================================================
-- Worker Sessions
-- ============================================================

CREATE TABLE IF NOT EXISTS scraper_worker_session (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    proxy_address VARCHAR(200),

    -- Statistics
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scraper_worker_active
ON scraper_worker_session(is_active, worker_id);

-- ============================================================
-- Metrics
-- ============================================================

CREATE TABLE IF NOT EXISTS scraper_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Task counts
    total_tasks INTEGER DEFAULT 0,
    pending_tasks INTEGER DEFAULT 0,
    in_progress_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,

    -- Worker stats
    active_workers INTEGER DEFAULT 0,
    avg_task_duration_ms INTEGER,

    -- CAPTCHA stats
    captchas_solved INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scraper_metrics_timestamp
ON scraper_metrics(timestamp DESC);

-- ============================================================
-- Auto-update trigger for updated_at
-- ============================================================

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

-- ============================================================
-- Grant permissions (adjust role name as needed)
-- ============================================================

-- GRANT ALL ON scraper_task TO castor_app;
-- GRANT ALL ON scraper_result TO castor_app;
-- GRANT ALL ON scraper_worker_session TO castor_app;
-- GRANT ALL ON scraper_metrics TO castor_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO castor_app;
