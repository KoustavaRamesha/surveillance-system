from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2

from config import EVIDENCE_DIR


def ensure_evidence_directory(base_dir: Path = EVIDENCE_DIR) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def build_evidence_filename(incident_type: str, incident_id: int | str) -> str:
    safe_type = incident_type.strip().lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid4().hex[:8]
    return f"{safe_type}_{timestamp}_{incident_id}_{unique_id}.jpg"


def save_incident_frame(frame, incident_type: str, incident_id: int | str, base_dir: Path = EVIDENCE_DIR) -> Path:
    evidence_dir = ensure_evidence_directory(base_dir)
    filename = build_evidence_filename(incident_type, incident_id)
    output_path = evidence_dir / filename

    success = cv2.imwrite(str(output_path), frame)
    if not success:
        raise RuntimeError(f"Failed to save evidence image: {output_path}")

    return output_path
