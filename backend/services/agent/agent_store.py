"""
Persistence for agent processing state (SQLite).
Tracks which E-14 forms have been processed by the agent.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Iterable, List, Optional

DB_PATH = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_e14_processed (
            form_id INTEGER PRIMARY KEY,
            processed_at TEXT NOT NULL,
            incidents_created INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def mark_processed(form_id: int, incidents_created: int = 0) -> None:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO agent_e14_processed (form_id, processed_at, incidents_created)
        VALUES (?, ?, ?)
        """,
        (form_id, datetime.utcnow().isoformat(), incidents_created),
    )
    conn.commit()
    conn.close()


def mark_batch_processed(form_ids: Iterable[int]) -> None:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.executemany(
        "INSERT OR REPLACE INTO agent_e14_processed (form_id, processed_at, incidents_created) VALUES (?, ?, 0)",
        [(fid, now) for fid in form_ids],
    )
    conn.commit()
    conn.close()


def get_unprocessed_form_ids(limit: int = 100) -> List[int]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.id
        FROM e14_scraper_forms f
        LEFT JOIN agent_e14_processed p ON p.form_id = f.id
        WHERE f.ocr_processed = 1 AND p.form_id IS NULL
        ORDER BY f.id ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]
