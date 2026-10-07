from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO
import numpy as np
import logging
from config import DEFAULT_IMG_SIZE

from rules import normalize_class_name


DEMO_EVENT_SEQUENCE = (
    (3, "restricted_area_intrusion"),
    (6, "no_helmet"),
    (9, "fire"),
    (12, "smoke"),
)


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    box: list[float]
    centre: list[float]
    track_id: int = -1
    interpolated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence": self.confidence,
            "box": self.box,
            "centre": self.centre,
            "interpolated": self.interpolated,
        }


def _resolve_model_source(model_path: str | Path) -> str:
    candidate = Path(model_path)
    if candidate.exists():
        return str(candidate)

    model_name = candidate.name.lower()
    if model_name in {"yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11m.pt"}:
        return model_name

    raise FileNotFoundError(f"Model file not found: {candidate}")


def load_model(model_path: str | Path) -> YOLO:
    source = _resolve_model_source(model_path)
    model = YOLO(source)
    try:
        # Fuse Conv2d + BatchNorm2d layers to improve inference speed
        model.fuse()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Model fusion failed: {e}")
    return model


def infer_frame(model: YOLO, frame, confidence_threshold: float) -> list[dict[str, Any]]:
    results = model.predict(frame, conf=confidence_threshold, verbose=False)
    if not results:
        return []

    detections: list[dict[str, Any]] = []
    names = model.names if hasattr(model, "names") else {}

    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            continue

        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)

        for index, box in enumerate(xyxy):
            x1, y1, x2, y2 = [float(value) for value in box]
            centre_x = (x1 + x2) / 2.0
            centre_y = (y1 + y2) / 2.0
            class_id = int(class_ids[index])
            raw_label = names.get(class_id, str(class_id))
            label = normalize_class_name(str(raw_label))
            detections.append(
                Detection(
                    label=label,
                    confidence=float(confidences[index]),
                    box=[x1, y1, x2, y2],
                    centre=[centre_x, centre_y],
                ).to_dict()
            )

    return detections


def track_frame(model: YOLO, frame: np.ndarray, confidence_threshold: float, imgsz: int | None = None, tracker: str | None = None, diagnostic: bool = False):
    """Run model.track on a single frame and return structured detections including track ids.

    Returns list of dicts: {"track_id": int, "label": str, "confidence": float, "box": [x1,y1,x2,y2], "centre": [cx,cy], "interpolated": bool}
    """
    if imgsz is None:
        imgsz = int(DEFAULT_IMG_SIZE)

    # ultralytics model.track accepts numpy arrays as source
    # Use quantize instead of deprecated half parameter
    kwargs = {"conf": float(confidence_threshold), "verbose": False}
    if imgsz:
        kwargs["imgsz"] = int(imgsz)
    if tracker:
        kwargs["tracker"] = tracker

    results = model.track(frame, persist=True, **kwargs)
    if not results:
        return [], None

    detections: list[dict[str, Any]] = []
    names = model.names if hasattr(model, "names") else {}

    # results may be a list where results[0] contains boxes
    res0 = results[0]
    boxes = getattr(res0, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return [], None

    xyxy = boxes.xyxy.cpu().numpy()
    confidences = boxes.conf.cpu().numpy()
    class_ids = boxes.cls.cpu().numpy().astype(int)
    # track ids may be available as boxes.id
    try:
        track_ids = boxes.id.cpu().numpy().astype(int)
    except Exception:
        track_ids = [-1] * len(xyxy)

    for index, box in enumerate(xyxy):
        x1, y1, x2, y2 = [float(value) for value in box]
        centre_x = (x1 + x2) / 2.0
        centre_y = (y1 + y2) / 2.0
        class_id = int(class_ids[index])
        raw_label = names.get(class_id, str(class_id))
        label = normalize_class_name(str(raw_label))
        tid = int(track_ids[index]) if track_ids is not None else -1
        detections.append(
            {
                "track_id": tid,
                "label": label,
                "confidence": float(confidences[index]),
                "box": [x1, y1, x2, y2],
                "raw_box": [x1, y1, x2, y2],
                "centre": [centre_x, centre_y],
                "interpolated": False,
            }
        )

    # only generate the expensive Ultralytics plot in diagnostic mode
    plot_img = None
    if diagnostic:
        try:
            plot_img = res0.plot()
        except Exception:
            pass

    return detections, plot_img


def draw_detections(frame, detections: list[dict[str, Any]]) -> Any:
    annotated = frame.copy()
    from rules import severity_for_event

    for detection in detections:
        x1, y1, x2, y2 = [int(value) for value in detection["box"]]
        track_id = detection.get("track_id")
        label = detection["label"]
        confidence = float(detection.get("confidence", 0.0))

        # Severity-based BGR color coding
        sev = severity_for_event(label).lower()
        if sev == "critical":
            colour = (35, 35, 235)    # Vibrant Crimson Red
        elif sev == "high":
            colour = (0, 135, 245)    # Safety Orange
        elif sev == "medium":
            colour = (0, 195, 245)    # Warning Amber / Gold
        else:
            colour = (60, 210, 60)    # Emerald Green (Safe / Low)

        # Draw main bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, 2)

        # Corner accents for a sleek futuristic look
        line_len = min(20, max(8, int((x2 - x1) * 0.15)))
        cv2.line(annotated, (x1, y1), (x1 + line_len, y1), colour, 3)
        cv2.line(annotated, (x1, y1), (x1, y1 + line_len), colour, 3)
        cv2.line(annotated, (x2, y1), (x2 - line_len, y1), colour, 3)
        cv2.line(annotated, (x2, y1), (x2, y1 + line_len), colour, 3)
        cv2.line(annotated, (x1, y2), (x1 + line_len, y2), colour, 3)
        cv2.line(annotated, (x1, y2), (x1, y2 - line_len), colour, 3)
        cv2.line(annotated, (x2, y2), (x2 - line_len, y2), colour, 3)
        cv2.line(annotated, (x2, y2), (x2, y2 - line_len), colour, 3)

        # Clean filled label badge above the bounding box
        display_name = label.replace("_", " ").title()
        if track_id is not None and track_id >= 0:
            text = f"ID:{track_id} {display_name} {int(confidence * 100)}%"
        else:
            text = f"{display_name} {int(confidence * 100)}%"

        (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y1 = max(0, y1 - text_h - 8)
        tag_y2 = max(text_h + 8, y1)
        # Background badge
        cv2.rectangle(annotated, (x1, tag_y1), (x1 + text_w + 10, tag_y2), colour, -1)
        # Label text in white (or dark for light backgrounds)
        text_color = (0, 0, 0) if sev == "medium" else (255, 255, 255)
        cv2.putText(
            annotated,
            text,
            (x1 + 5, tag_y2 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            text_color,
            1,
            cv2.LINE_AA,
        )

    return annotated


def _demo_box(frame_width: int, frame_height: int, x_ratio: float, y_ratio: float, width_ratio: float, height_ratio: float) -> list[float]:
    width = frame_width * width_ratio
    height = frame_height * height_ratio
    centre_x = frame_width * x_ratio
    centre_y = frame_height * y_ratio
    x1 = max(0.0, centre_x - width / 2.0)
    y1 = max(0.0, centre_y - height / 2.0)
    x2 = min(float(frame_width - 1), centre_x + width / 2.0)
    y2 = min(float(frame_height - 1), centre_y + height / 2.0)
    return [x1, y1, x2, y2]


def generate_demo_detections(frame, processed_frame_index: int, zone: dict[str, int]) -> list[dict[str, Any]]:
    """Build simple scripted detections so the final demo works without a trained custom model."""
    frame_height, frame_width = frame.shape[:2]
    demo_detections: list[dict[str, Any]] = []

    for trigger_frame, label in DEMO_EVENT_SEQUENCE:
        if processed_frame_index != trigger_frame:
            continue

        if label == "restricted_area_intrusion":
            zone_width = max(80.0, float(zone["x2"] - zone["x1"]))
            zone_height = max(120.0, float(zone["y2"] - zone["y1"]))
            x1 = max(0.0, float(zone["x1"]) + zone_width * 0.2)
            y1 = max(0.0, float(zone["y1"]) + zone_height * 0.2)
            x2 = min(float(frame_width - 1), x1 + zone_width * 0.4)
            y2 = min(float(frame_height - 1), y1 + zone_height * 0.6)
            demo_detections.append(
                {
                    "label": "person",
                    "confidence": 0.94,
                    "box": [x1, y1, x2, y2],
                    "centre": [(x1 + x2) / 2.0, (y1 + y2) / 2.0],
                }
            )
            continue

        if label == "no_helmet":
            box = _demo_box(frame_width, frame_height, 0.50, 0.52, 0.20, 0.42)
        elif label == "fire":
            box = _demo_box(frame_width, frame_height, 0.78, 0.60, 0.16, 0.20)
        else:
            box = _demo_box(frame_width, frame_height, 0.72, 0.38, 0.18, 0.20)

        demo_detections.append(
            {
                "label": label,
                "confidence": 0.93,
                "box": box,
                "centre": [(box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0],
            }
        )

    return demo_detections
