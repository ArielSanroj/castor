"""
SQLite-backed incident store for real, persistent incidents.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.schemas.incidents import (
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    INCIDENT_CONFIG,
)

DB_PATH = os.path.expanduser("~/Downloads/Code/Proyectos/castor/backend/data/castor.db")

ANOMALY_TO_INCIDENT = {
    "ARITHMETIC_MISMATCH": IncidentType.ARITHMETIC_FAIL,
    "OCR_LOW_CONFIDENCE": IncidentType.OCR_LOW_CONF,
    "E11_URNA_MISMATCH": IncidentType.E11_VS_URNA,
    "SIGNATURE_MISSING": IncidentType.SIGNATURE_MISSING,
    "STATISTICAL_OUTLIER": IncidentType.DISCREPANCY_RNEC,
    "GEOGRAPHIC_CLUSTER": IncidentType.DISCREPANCY_RNEC,
    "TEMPORAL_ANOMALY": IncidentType.RNEC_DELAY,
    "DUPLICATE_FORM": IncidentType.SOURCE_MISMATCH,
    "IMPOSSIBLE_VALUE": IncidentType.ARITHMETIC_FAIL,
}

ANOMALY_SEVERITY_TO_INCIDENT = {
    "CRITICAL": IncidentSeverity.P0,
    "HIGH": IncidentSeverity.P1,
    "MEDIUM": IncidentSeverity.P2,
    "LOW": IncidentSeverity.P3,
    "INFO": IncidentSeverity.P3,
}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_type TEXT NOT NULL,
            mesa_id TEXT,
            dept_code TEXT,
            muni_code TEXT,
            dept_name TEXT,
            muni_name TEXT,
            puesto TEXT,
            description TEXT,
            severity TEXT,
            status TEXT,
            ocr_confidence REAL,
            delta_value REAL,
            evidence TEXT,
            created_at TEXT,
            sla_deadline TEXT,
            assigned_to TEXT,
            assigned_at TEXT,
            resolved_at TEXT,
            resolution_notes TEXT,
            escalated_to_legal INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(incident_type)"
    )
    conn.commit()
    conn.close()


def _sla_deadline(incident_type: IncidentType) -> datetime:
    config = INCIDENT_CONFIG.get(incident_type, {"sla_minutes": 30})
    return datetime.utcnow() + timedelta(minutes=config.get("sla_minutes", 30))


def _severity_default(incident_type: IncidentType) -> IncidentSeverity:
    config = INCIDENT_CONFIG.get(incident_type, {"default_severity": IncidentSeverity.P2})
    return config.get("default_severity", IncidentSeverity.P2)


def _row_to_incident(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    if data.get("evidence"):
        try:
            data["evidence"] = json.loads(data["evidence"])
        except Exception:
            data["evidence"] = None
    return data


def _calculate_sla_remaining(sla_deadline: Optional[str]) -> Optional[int]:
    if not sla_deadline:
        return None
    try:
        deadline = datetime.fromisoformat(sla_deadline)
    except Exception:
        return None
    delta = deadline - datetime.utcnow()
    return int(delta.total_seconds() // 60)


def find_existing(incident_type: str, mesa_id: str, description: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM incidents
        WHERE incident_type = ? AND mesa_id = ? AND description = ?
        AND status IN ('OPEN','ASSIGNED','INVESTIGATING')
        ORDER BY id DESC LIMIT 1
        """,
        (incident_type, mesa_id, description),
    )
    row = cur.fetchone()
    conn.close()
    return _row_to_incident(row) if row else None


def create_incident(data: Dict[str, Any], dedupe: bool = True) -> Dict[str, Any]:
    init_db()

    incident_type = data.get("incident_type", "UNKNOWN")
    try:
        incident_type_enum = IncidentType(incident_type)
    except Exception:
        incident_type_enum = IncidentType.ARITHMETIC_FAIL

    description = data.get("description") or "Incidente detectado"
    mesa_id = data.get("mesa_id") or ""

    if dedupe:
        existing = find_existing(incident_type_enum.value, mesa_id, description)
        if existing:
            existing["sla_remaining_minutes"] = _calculate_sla_remaining(existing.get("sla_deadline"))
            return existing

    severity = data.get("severity")
    if not severity:
        severity = _severity_default(incident_type_enum).value
    else:
        severity = str(severity)

    created_at = datetime.utcnow()
    sla_deadline = _sla_deadline(incident_type_enum)

    payload = {
        "incident_type": incident_type_enum.value,
        "mesa_id": mesa_id,
        "dept_code": data.get("dept_code"),
        "muni_code": data.get("muni_code"),
        "dept_name": data.get("dept_name"),
        "muni_name": data.get("muni_name"),
        "puesto": data.get("puesto"),
        "description": description,
        "severity": severity,
        "status": IncidentStatus.OPEN.value,
        "ocr_confidence": data.get("ocr_confidence"),
        "delta_value": data.get("delta_value"),
        "evidence": json.dumps(data.get("evidence") or {}),
        "created_at": created_at.isoformat(),
        "sla_deadline": sla_deadline.isoformat(),
        "assigned_to": None,
        "assigned_at": None,
        "resolved_at": None,
        "resolution_notes": None,
        "escalated_to_legal": 0,
    }

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO incidents (
            incident_type, mesa_id, dept_code, muni_code, dept_name, muni_name, puesto,
            description, severity, status, ocr_confidence, delta_value, evidence,
            created_at, sla_deadline, assigned_to, assigned_at, resolved_at,
            resolution_notes, escalated_to_legal
        ) VALUES (
            :incident_type, :mesa_id, :dept_code, :muni_code, :dept_name, :muni_name, :puesto,
            :description, :severity, :status, :ocr_confidence, :delta_value, :evidence,
            :created_at, :sla_deadline, :assigned_to, :assigned_at, :resolved_at,
            :resolution_notes, :escalated_to_legal
        )
        """,
        payload,
    )
    conn.commit()
    incident_id = cur.lastrowid
    conn.close()

    payload["id"] = incident_id
    payload["sla_remaining_minutes"] = _calculate_sla_remaining(payload["sla_deadline"])
    payload["evidence"] = data.get("evidence") or {}
    return payload


def create_incidents_from_anomalies(anomalies: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for anomaly in anomalies:
        anomaly_type = anomaly.get("anomaly_type") or anomaly.get("incident_type")
        incident_type = ANOMALY_TO_INCIDENT.get(anomaly_type, IncidentType.ARITHMETIC_FAIL)
        severity = ANOMALY_SEVERITY_TO_INCIDENT.get(anomaly.get("severity"), IncidentSeverity.P2)
        incident = create_incident(
            {
                "incident_type": incident_type.value,
                "severity": severity.value,
                "mesa_id": anomaly.get("mesa_id"),
                "dept_code": anomaly.get("dept_code"),
                "muni_code": anomaly.get("muni_code"),
                "description": anomaly.get("description") or anomaly.get("details", {}).get("message") or str(anomaly_type),
                "ocr_confidence": anomaly.get("confidence") or anomaly.get("details", {}).get("avg_confidence"),
                "delta_value": anomaly.get("details", {}).get("delta") or anomaly.get("details", {}).get("anomaly_count"),
                "evidence": anomaly,
            },
            dedupe=True,
        )
        results.append(incident)
    return results


def list_incidents(
    status: Optional[List[str]] = None,
    incident_type: Optional[List[str]] = None,
    limit: int = 50,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()

    where = []
    params: List[Any] = []
    if status:
        placeholders = ",".join("?" * len(status))
        where.append(f"status IN ({placeholders})")
        params.extend(status)
    if incident_type:
        placeholders = ",".join("?" * len(incident_type))
        where.append(f"incident_type IN ({placeholders})")
        params.extend(incident_type)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    cur.execute(f"SELECT * FROM incidents {where_sql} ORDER BY created_at DESC LIMIT ?", params + [limit])
    rows = cur.fetchall()
    incidents = []
    for row in rows:
        item = _row_to_incident(row)
        item["sla_remaining_minutes"] = _calculate_sla_remaining(item.get("sla_deadline"))
        incidents.append(item)

    cur.execute("SELECT COUNT(*) FROM incidents")
    total = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM incidents WHERE status = 'OPEN'")
    open_count = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'P0' AND status = 'OPEN'")
    p0_count = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'P1' AND status = 'OPEN'")
    p1_count = cur.fetchone()[0] or 0

    conn.close()
    return incidents, {
        "total": total,
        "open_count": open_count,
        "p0_count": p0_count,
        "p1_count": p1_count,
    }


def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    item = _row_to_incident(row)
    item["sla_remaining_minutes"] = _calculate_sla_remaining(item.get("sla_deadline"))
    return item


def update_incident(incident_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    columns = []
    params = []
    for key, value in updates.items():
        columns.append(f"{key} = ?")
        params.append(value)
    if not columns:
        conn.close()
        return get_incident(incident_id)
    params.append(incident_id)
    cur.execute(f"UPDATE incidents SET {', '.join(columns)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return get_incident(incident_id)


def stats() -> Dict[str, Any]:
    init_db()
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM incidents")
    total = cur.fetchone()[0] or 0
    cur.execute("SELECT severity, COUNT(*) FROM incidents GROUP BY severity")
    by_severity = {row[0]: row[1] for row in cur.fetchall()}
    cur.execute("SELECT status, COUNT(*) FROM incidents GROUP BY status")
    by_status = {row[0]: row[1] for row in cur.fetchall()}
    cur.execute("SELECT incident_type, COUNT(*) FROM incidents GROUP BY incident_type")
    by_type = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return {
        "total": total,
        "by_severity": {**{"P0": 0, "P1": 0, "P2": 0, "P3": 0}, **by_severity},
        "by_status": {**{
            "OPEN": 0, "ASSIGNED": 0, "INVESTIGATING": 0,
            "RESOLVED": 0, "FALSE_POSITIVE": 0, "ESCALATED": 0
        }, **by_status},
        "by_type": by_type,
    }
