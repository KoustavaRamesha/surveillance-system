from __future__ import annotations

import logging
import time
from typing import Any

from config import (
    DEFAULT_SMOOTHING_ALPHA,
    DEFAULT_REQUIRED_HITS,
    DEFAULT_ALLOWED_MISSES,
    STABILIZER_MAX_SHIFT_RATIO,
    STABILIZER_IOU_THRESHOLD,
    STABILIZER_CONFIDENCE_HIGH,
    STABILIZER_CONFIDENCE_LOW,
)

logger = logging.getLogger(__name__)


class TrackState:
    """Stores per-track state for smoothing and confirmation."""

    __slots__ = (
        "track_id",
        "label",
        "box",
        "confidence",
        "hits",
        "misses",
        "last_seen",
        "established",
    )

    def __init__(self, track_id: int, label: str, box: List[float], confidence: float):
        self.track_id = int(track_id)
        self.label = label
        self.box = box[:]  # smoothed box
        self.confidence = float(confidence)
        self.hits = 1
        self.misses = 0
        self.last_seen = time.time()
        self.established = False


class DetectionStabilizer:
    """Per-camera, per-track stabilizer with EMA smoothing, hits/misses and hysteresis.

    Usage:
      stab = DetectionStabilizer()
      stable = stab.update(camera_id, detections)

    Each detection must include: track_id, label, confidence, box
    """

    def __init__(self, alpha: float | None = None, required_hits: int | None = None, allowed_misses: int | None = None):
        self.alpha = float(alpha) if alpha is not None else float(DEFAULT_SMOOTHING_ALPHA)
        self.required_hits = int(required_hits) if required_hits is not None else int(DEFAULT_REQUIRED_HITS)
        self.allowed_misses = int(allowed_misses) if allowed_misses is not None else int(DEFAULT_ALLOWED_MISSES)
        # camera_id -> track_id -> TrackState
        self._state: Dict[str, Dict[int, TrackState]] = {}

    def update(self, camera_id: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        camera_tracks = self._state.setdefault(camera_id, {})

        seen_ids = set()

        for det in detections:
            tid = int(det.get("track_id", -1))
            if tid < 0:
                # skip untracked detections
                continue
            seen_ids.add(tid)
            label = det.get("label", "")
            box = det.get("box", []).copy()
            conf = float(det.get("confidence", 0.0))

            ts = camera_tracks.get(tid)
            if ts is None:
                # new track observed
                ts = TrackState(tid, label, box, conf)
                camera_tracks[tid] = ts
                logger.info("Track created camera=%s id=%s label=%s conf=%.2f", camera_id, tid, label, conf)
                continue

            # EMA smoothing with clamp to prevent large jumps
            alpha = self.alpha
            proposed = [alpha * b + (1 - alpha) * o for b, o in zip(box, ts.box)]

            old_w = max(1.0, ts.box[2] - ts.box[0])
            old_h = max(1.0, ts.box[3] - ts.box[1])
            max_dx = STABILIZER_MAX_SHIFT_RATIO * old_w
            max_dy = STABILIZER_MAX_SHIFT_RATIO * old_h

            new_box = ts.box.copy()
            # clamp shifts
            dx = max(-max_dx, min(max_dx, proposed[0] - ts.box[0]))
            dy = max(-max_dy, min(max_dy, proposed[1] - ts.box[1]))
            dx2 = max(-max_dx, min(max_dx, proposed[2] - ts.box[2]))
            dy2 = max(-max_dy, min(max_dy, proposed[3] - ts.box[3]))
            new_box[0] = ts.box[0] + dx
            new_box[1] = ts.box[1] + dy
            new_box[2] = ts.box[2] + dx2
            new_box[3] = ts.box[3] + dy2

            ts.box = new_box
            ts.confidence = alpha * conf + (1 - alpha) * ts.confidence
            ts.hits += 1
            ts.misses = 0
            ts.last_seen = now

            # confirm establishment based on hits and confidence
            if not ts.established:
                if ts.hits >= self.required_hits and ts.confidence >= STABILIZER_CONFIDENCE_HIGH:
                    ts.established = True
                    logger.info("Track confirmed camera=%s id=%s", camera_id, tid)

        # increment misses for unseen tracks
        for tid, ts in list(camera_tracks.items()):
            if tid not in seen_ids:
                ts.misses += 1
                if ts.misses == 1:
                    logger.info("Track missed camera=%s id=%s misses=%d", camera_id, tid, ts.misses)

        # remove stale tracks
        for tid, ts in list(camera_tracks.items()):
            if ts.misses > self.allowed_misses:
                logger.info("Track removed camera=%s id=%s after %d misses", camera_id, tid, ts.misses)
                del camera_tracks[tid]

        # build output: only return visual-confirmed tracks (established or high confidence)
        out: List[Dict[str, Any]] = []
        for tid, ts in camera_tracks.items():
            # treat as visual-confirmed if established or confidence above low threshold
            visual_confirmed = ts.established or ts.confidence >= STABILIZER_CONFIDENCE_LOW
            if visual_confirmed:
                x1, y1, x2, y2 = ts.box
                centre = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
                out.append(
                    {
                        "track_id": ts.track_id,
                        "label": ts.label,
                        "confidence": float(ts.confidence),
                        "box": ts.box.copy(),
                        "centre": centre,
                        "visual_confirmed": visual_confirmed,
                        "established": ts.established,
                        "misses": ts.misses,
                        "hits": ts.hits,
                    }
                )

        return out
