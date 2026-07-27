from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATABASE_PATH
from database import get_connection


_ALLOWED_CAMERA_COLUMNS = frozenset({
    "name", "location", "source_type", "source", "username",
    "enabled", "analytics_enabled", "recording_enabled",
    "expected_resolution", "expected_fps", "zone_config",
})


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
        zone_config TEXT,
        created_at TEXT
    )
    """
    with get_connection(db_path) as conn:
        conn.execute(sql)
        # Handle migration for existing databases smoothly
        try:
            conn.execute("ALTER TABLE cameras ADD COLUMN zone_config TEXT;")
        except Exception:
            pass  # Column likely already exists
        conn.commit()


def add_camera(camera: dict[str, Any], db_path: Path = DATABASE_PATH) -> int:
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


def list_cameras(db_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    sql = "SELECT * FROM cameras ORDER BY id"
    with get_connection(db_path) as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]


def get_camera(camera_id: str, db_path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    sql = "SELECT * FROM cameras WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        row = conn.execute(sql, (camera_id,)).fetchone()
        return dict(row) if row else None


def delete_camera(camera_id: str, db_path: Path = DATABASE_PATH) -> None:
    sql = "DELETE FROM cameras WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        conn.execute(sql, (camera_id,))
        conn.commit()


def update_camera(camera_id: str, fields: dict[str, Any], db_path: Path = DATABASE_PATH) -> None:
    """Update arbitrary fields for a camera record."""
    if not fields:
        return
    invalid = set(fields.keys()) - _ALLOWED_CAMERA_COLUMNS
    if invalid:
        raise ValueError(f"Invalid column names: {invalid}")
    keys = list(fields.keys())
    setters = ", ".join(f"{k} = ?" for k in keys)
    params = [fields[k] for k in keys] + [camera_id]
    sql = f"UPDATE cameras SET {setters} WHERE camera_id = ?"
    with get_connection(db_path) as conn:
        conn.execute(sql, params)
        conn.commit()
