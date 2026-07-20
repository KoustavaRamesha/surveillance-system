from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from rules import is_loggable_incident, normalize_class_name, recommendation_for_event, severity_for_event
from evidence import save_incident_frame
from database import add_incident


class AlertManager:
    def __init__(self, cooldown_seconds: int = 10):
        self.cooldown_seconds = cooldown_seconds
        self._last_logged: Dict[str, datetime] = {}

    def _event_key(self, camera_id: str, zone_name: str, event_type: str) -> str:
        return f"{camera_id}:{zone_name}:{normalize_class_name(event_type)}"

    def process_detections(self, camera_id: str, camera_name: str, detections: List[Dict[str, Any]], annotated_frame) -> List[Dict[str, Any]]:
        """Process detections for a camera, log incidents if rules matched, and return list of logged incidents."""
        logged: List[Dict[str, Any]] = []
        now = datetime.now()
        for det in detections:
            label = normalize_class_name(det.get("label", ""))
            if not is_loggable_incident(label):
                continue

            zone_name = det.get("zone", "") or "Global"
            key = self._event_key(camera_id, zone_name, label)
            last = self._last_logged.get(key)
            if last is not None:
                elapsed = (now - last).total_seconds()
                if elapsed < self.cooldown_seconds:
                    continue

            # save evidence image (annotated)
            incident_id_tag = uuid.uuid4().hex[:8]
            filename_tag = f"{camera_id}_{label}_{incident_id_tag}"
            evidence_path = save_incident_frame(annotated_frame, label, filename_tag)

            severity = severity_for_event(label)
            recommendation = recommendation_for_event(label)

            db_id = add_incident(
                event_type=label,
                severity=severity,
                zone=zone_name,
                confidence=float(det.get("confidence", 0.0)),
                recommendation=recommendation,
                evidence_image_path=str(evidence_path),
                status="Open",
            )

            self._last_logged[key] = now
            logged.append({
                "db_id": db_id,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "event_type": label,
                "severity": severity,
                "recommendation": recommendation,
                "evidence": str(evidence_path),
            })

        return logged
