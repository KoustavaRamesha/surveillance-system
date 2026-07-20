from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict, List

from PySide6.QtCore import QThread, Signal

from config import (
    DEFAULT_AI_FPS,
    DEFAULT_CONFIDENCE,
    DEFAULT_INFERENCE_FPS,
    FRAME_QUEUE_MAXLEN,
    TRACKER_CONFIG,
    DEFAULT_IMG_SIZE,
)
from detector import load_model, track_frame, generate_demo_detections, draw_detections
from core.detection_stabilizer import DetectionStabilizer


class InferenceManager(QThread):
    """Shared inference manager that loads the YOLO model once and runs inference
    on the latest frame from each camera at a configurable rate.

    Signals:
        detection_ready(camera_id: str, detections: list)
        status_updated(text: str)
    """

    # emits: camera_id, detections, annotated_frame
    detection_ready = Signal(str, object, object)
    status_updated = Signal(str)

    def __init__(self, model_path: str | None = None, ai_fps: int = DEFAULT_AI_FPS, confidence: float = DEFAULT_CONFIDENCE, demo_mode: bool = False, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        try:
            self.setObjectName("InferenceManager")
        except Exception:
            pass
        self.ai_fps = ai_fps
        self.confidence = confidence
        self.demo_mode = demo_mode
        self._running = False
        # per-camera bounded latest-frame queue
        self._frames: Dict[str, deque] = {}
        self._frames_lock = threading.Lock()
        self._model = None
        # per-camera model instances to keep tracker state separate
        self._camera_models: Dict[str, object] = {}
        # per-camera stabilizers
        self._stabilizers: Dict[str, DetectionStabilizer] = {}
        # inference FPS trackers
        self._last_infer_time: Dict[str, float] = {}

    def start_manager(self) -> None:
        if not self.isRunning():
            self._running = True
            self.start()

    def stop_manager(self) -> None:
        self._running = False
        try:
            # request thread to quit and wait longer for clean shutdown
            self.quit()
            if self.isRunning():
                self.wait(5000)
        except Exception:
            pass

    def load_model(self) -> None:
        if self.demo_mode:
            self._model = None
            self.status_updated.emit("Demo mode: using scripted detections")
            return
        if not self.model_path:
            self.status_updated.emit("No model path provided; demo mode only")
            self._model = None
            return
        try:
            self._model = load_model(self.model_path)
            self.status_updated.emit(f"Model loaded: {self.model_path}")
        except FileNotFoundError as exc:
            self._model = None
            self.status_updated.emit(f"Model load failed: {exc}")

    def submit_frame(self, camera_id: str, frame: Any) -> None:
        with self._frames_lock:
            q = self._frames.get(camera_id)
            if q is None:
                q = deque(maxlen=FRAME_QUEUE_MAXLEN)
                self._frames[camera_id] = q
            # append latest frame; old frames automatically dropped
            q.append((frame, time.time()))

    def run(self) -> None:
        self.load_model()
        # use configured inference fps
        interval = 1.0 / max(1, int(self.ai_fps or DEFAULT_INFERENCE_FPS))
        try:
            # enable debug logs when diagnostic_mode set
            import logging

            if getattr(self, "diagnostic_mode", False):
                logging.basicConfig(level=logging.DEBUG)
            while self._running and not self.isInterruptionRequested():
                start = time.time()
                camera_items: List[tuple[str, Any]] = []
                with self._frames_lock:
                    for cid, q in list(self._frames.items()):
                        if not q:
                            continue
                        # take the latest frame only; record queue size for debug
                        queue_size = len(q)
                        frame, ts = q.pop()
                        q.clear()
                        camera_items.append((cid, frame, queue_size))

                for camera_id, frame, queue_size in camera_items:
                    try:
                        if self.demo_mode or self._model is None:
                            detections = generate_demo_detections(frame, 1, {"x1": 0, "y1": 0, "x2": frame.shape[1], "y2": frame.shape[0], "name": "Zone"})
                        else:
                            # ensure per-camera model instance for persistent tracking
                            cam_model = self._camera_models.get(camera_id)
                            if cam_model is None:
                                cam_model = load_model(self.model_path)
                                self._camera_models[camera_id] = cam_model

                            # run tracker-based inference on the latest frame (per-camera model)
                            detections, plot_img = track_frame(cam_model, frame, self.confidence, imgsz=DEFAULT_IMG_SIZE, tracker=TRACKER_CONFIG)

                        # get per-camera stabilizer
                        stab = self._stabilizers.get(camera_id)
                        if stab is None:
                            # configure stabilizer from current settings
                            from config import DEFAULT_SMOOTHING_ALPHA, DEFAULT_REQUIRED_HITS, DEFAULT_ALLOWED_MISSES

                            stab = DetectionStabilizer(alpha=DEFAULT_SMOOTHING_ALPHA, required_hits=DEFAULT_REQUIRED_HITS, allowed_misses=DEFAULT_ALLOWED_MISSES)
                            self._stabilizers[camera_id] = stab

                        try:
                            # In diagnostic mode skip custom smoothing/confirmation so we can compare raw tracker output
                            if getattr(self, "diagnostic_mode", False):
                                # optional person-only filter for diagnostics
                                if getattr(self, "diagnostic_person_only", False):
                                    stable_detections = [d for d in detections if d.get("label") == "person"]
                                else:
                                    stable_detections = detections
                            else:
                                stable_detections = stab.update(camera_id, detections)
                        except Exception as exc:
                            self.status_updated.emit(f"Stabilizer error for {camera_id}: {exc}")
                            stable_detections = detections

                        # annotate frame: if diagnostic, prefer Ultralytics' own plot for direct comparison
                        try:
                            if getattr(self, "diagnostic_mode", False) and not self.demo_mode and 'plot_img' in locals() and plot_img is not None:
                                annotated = plot_img
                            else:
                                annotated = draw_detections(frame.copy(), stable_detections) if stable_detections else frame
                        except Exception:
                            annotated = frame

                        # compute lightweight inference fps per camera
                        now = time.time()
                        last = self._last_infer_time.get(camera_id, None)
                        if last is None:
                            infer_fps = 0.0
                        else:
                            infer_fps = 1.0 / max(1e-6, now - last)
                        self._last_infer_time[camera_id] = now

                        # attach debug info to detections and log detailed info
                        for det in stable_detections:
                            det["camera_id"] = camera_id
                            det["inference_fps"] = infer_fps
                            det["original_frame_shape"] = frame.shape[:2]
                            det["inference_imgsz"] = DEFAULT_IMG_SIZE
                            det["display_shape"] = annotated.shape[:2]
                            det["queue_size"] = queue_size

                        # log per-camera, per-inference diagnostics
                        try:
                            import logging

                            logger = logging.getLogger("inference_manager")
                            logger.debug("Camera %s original=%s infer=%s display=%s queue=%d fps=%.2f detections=%d", camera_id, frame.shape[:2], DEFAULT_IMG_SIZE, annotated.shape[:2], queue_size, infer_fps, len(stable_detections))
                            for det in stable_detections:
                                logger.debug("DET camera=%s id=%s label=%s conf=%.3f raw=%s scaled=%s established=%s hits=%d misses=%d", camera_id, det.get("track_id"), det.get("label"), det.get("confidence"), det.get("raw_box", det.get("box")), det.get("box"), det.get("established"), det.get("hits", 0), det.get("misses", 0))
                        except Exception:
                            pass

                        # emit stabilized detections and annotated frame
                        self.detection_ready.emit(camera_id, stable_detections, annotated)
                    except Exception as exc:
                        self.status_updated.emit(f"Inference error for {camera_id}: {exc}")

            elapsed = time.time() - start
            to_sleep = max(0.0, interval - elapsed)
            time.sleep(to_sleep)
        except Exception as exc:
            import traceback

            self.status_updated.emit(f"Inference thread error: {exc}")
            traceback.print_exc()
