from __future__ import annotations

from typing import Any

import cv2


def validate_zone_coordinates(zone: dict[str, int], frame_width: int, frame_height: int) -> dict[str, int]:
    x1 = max(0, min(frame_width - 1, int(zone["x1"])))
    y1 = max(0, min(frame_height - 1, int(zone["y1"])))
    x2 = max(0, min(frame_width - 1, int(zone["x2"])))
    y2 = max(0, min(frame_height - 1, int(zone["y2"])))

    if x1 >= x2 or y1 >= y2:
        raise ValueError("Restricted-zone coordinates are invalid. Ensure x1 < x2 and y1 < y2.")

    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "name": zone.get("name", "Restricted Zone")}


def point_in_rectangle(point: tuple[float, float], zone: dict[str, int]) -> bool:
    x, y = point
    return zone["x1"] <= x <= zone["x2"] and zone["y1"] <= y <= zone["y2"]


def draw_zone(frame, zone: dict[str, int], in_place: bool = False):
    annotated = frame if in_place else frame.copy()
    x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(
        annotated,
        zone.get("name", "Restricted Zone"),
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )
    return annotated


def detect_intrusions(detections: list[dict[str, Any]], zone: dict[str, int]) -> list[dict[str, Any]]:
    intrusions: list[dict[str, Any]] = []
    for detection in detections:
        if detection.get("label") != "person":
            continue
        centre = detection.get("centre", [0, 0])
        if point_in_rectangle((float(centre[0]), float(centre[1])), zone):
            intrusions.append(detection)
    return intrusions
