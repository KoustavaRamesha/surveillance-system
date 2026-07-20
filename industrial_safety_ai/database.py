from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import DATABASE_PATH, INCIDENT_STATUSES


def get_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_incidents_table(db_path: Path = DATABASE_PATH) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_uuid TEXT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        zone TEXT NOT NULL,
        confidence REAL NOT NULL,
        recommendation TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Open',
        evidence_image_path TEXT,
        original_image_path TEXT,
        camera_id TEXT,
        camera_name TEXT,
        camera_location TEXT,
        acknowledged_at TEXT,
        resolved_at TEXT,
        operator_note TEXT
    )
    """
    try:
        with get_connection(db_path) as connection:
            connection.execute(sql)
            connection.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to create incidents table: {exc}") from exc


def add_incident(
    event_type: str,
    severity: str,
    zone: str,
    confidence: float,
    recommendation: str,
    evidence_image_path: str,
    status: str = "Open",
    timestamp: str | None = None,
    db_path: Path = DATABASE_PATH,
) -> int:
    create_incidents_table(db_path)
    if status not in INCIDENT_STATUSES:
        raise ValueError(f"Unsupported incident status: {status}")
    incident_timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
    INSERT INTO incidents (
        incident_uuid, timestamp, event_type, severity, zone, confidence, recommendation, status, evidence_image_path, camera_id, camera_name, camera_location
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with get_connection(db_path) as connection:
            incident_uuid = uuid4().hex[:12]
            cursor = connection.execute(
                sql,
                (
                    incident_uuid,
                    incident_timestamp,
                    event_type,
                    severity,
                    zone,
                    confidence,
                    recommendation,
                    status,
                    evidence_image_path,
                    None,
                    None,
                    None,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to add incident: {exc}") from exc


def read_incidents(
    db_path: Path = DATABASE_PATH,
    severity: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    create_incidents_table(db_path)
    query = "SELECT * FROM incidents"
    filters: list[str] = []
    params: list[Any] = []

    if severity:
        filters.append("severity = ?")
        params.append(severity)
    if status:
        filters.append("status = ?")
        params.append(status)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY timestamp DESC, id DESC"

    try:
        with get_connection(db_path) as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to read incidents: {exc}") from exc


def update_incident_status(
    incident_id: int,
    status: str,
    db_path: Path = DATABASE_PATH,
) -> None:
    create_incidents_table(db_path)
    if status not in INCIDENT_STATUSES:
        raise ValueError(f"Unsupported incident status: {status}")
    try:
        with get_connection(db_path) as connection:
            connection.execute(
                "UPDATE incidents SET status = ? WHERE id = ?",
                (status, incident_id),
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to update incident status: {exc}") from exc
