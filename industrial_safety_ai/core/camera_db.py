from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import DATABASE_PATH


def get_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def create_cameras_table(db_path: Path = DATABASE_PATH) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id TEXT UNIQUE NOT NULL,
        name TEXT,
        location TEXT,
        source_type TEXT,
        source TEXT,
        username TEXT,
        enabled INTEGER DEFAULT 1,
        analytics_enabled INTEGER DEFAULT 0,
        recording_enabled INTEGER DEFAULT 0,
        expected_resolution TEXT,
        expected_fps REAL,
        created_at TEXT
    )
    """
    with get_connection(db_path) as conn:
        conn.execute(sql)
        conn.commit()


def add_camera(camera: Dict[str, Any], db_path: Path = DATABASE_PATH) -> int:
    create_cameras_table(db_path)
    sql = """
    INSERT INTO cameras (
        camera_id, name, location, source_type, source, username, enabled,
        analytics_enabled, recording_enabled, expected_resolution, expected_fps, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params = (
        camera.get("camera_id"),
        camera.get("name"),
        camera.get("location"),
        camera.get("source_type"),
        camera.get("source"),
        camera.get("username"),
        1 if camera.get("enabled", True) else 0,
        1 if camera.get("analytics_enabled", False) else 0,
        1 if camera.get("recording_enabled", False) else 0,
        camera.get("expected_resolution"),
        camera.get("expected_fps"),
        now,
    )
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return int(cursor.lastrowid)


def list_cameras(db_path: Path = DATABASE_PATH) -> List[Dict[str, Any]]:
    create_cameras_table(db_path)
    sql = "SELECT * FROM cameras ORDER BY id"
    with get_connection(db_path) as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]


def get_camera(camera_id: str, db_path: Path = DATABASE_PATH) -> Dict[str, Any] | None:
    create_cameras_table(db_path)
    sql = "SELECT * FROM cameras WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        row = conn.execute(sql, (camera_id,)).fetchone()
        return dict(row) if row else None


def delete_camera(camera_id: str, db_path: Path = DATABASE_PATH) -> None:
    create_cameras_table(db_path)
    sql = "DELETE FROM cameras WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        conn.execute(sql, (camera_id,))
        conn.commit()


def update_camera(camera_id: str, fields: Dict[str, Any], db_path: Path = DATABASE_PATH) -> None:
    """Update arbitrary fields for a camera record."""
    create_cameras_table(db_path)
    if not fields:
        return
    keys = list(fields.keys())
    setters = ", ".join(f"{k} = ?" for k in keys)
    params = [fields[k] for k in keys] + [camera_id]
    sql = f"UPDATE cameras SET {setters} WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        conn.execute(sql, params)
        conn.commit()
