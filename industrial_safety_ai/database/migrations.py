from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

from config import DATABASE_PATH


def _get_columns(table: str, db_path: Path = DATABASE_PATH) -> List[str]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]


def ensure_incidents_columns(db_path: Path = DATABASE_PATH) -> None:
    # desired extra columns per project spec
    extras = {
        "incident_uuid": "TEXT",
        "camera_id": "TEXT",
        "camera_name": "TEXT",
        "camera_location": "TEXT",
        "zone_id": "TEXT",
        "zone_name": "TEXT",
        "evidence_image_path": "TEXT",
        "original_image_path": "TEXT",
        "acknowledged_at": "TEXT",
        "resolved_at": "TEXT",
        "operator_note": "TEXT",
    }
    with sqlite3.connect(db_path) as conn:
        existing = _get_columns("incidents", db_path)
        for col, coltype in extras.items():
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE incidents ADD COLUMN {col} {coltype}")
                except sqlite3.OperationalError:
                    pass
        conn.commit()
