from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

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
from zone_monitor import detect_intrusions, validate_zone_coordinates
from config import DEFAULT_ZONE
import json
import cv2


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
        self._frames: dict[str, deque] = {}
        self._frames_lock = threading.Lock()
        self._model = None
        # per-camera model instances to keep tracker state separate
        self._camera_models: dict[str, object] = {}
        # per-camera stabilizers
        self._stabilizers: dict[str, DetectionStabilizer] = {}
        # inference FPS trackers
        self._last_infer_time: dict[str, float] = {}
        # per-camera demo frame counter
        self._demo_frame_counter: dict[str, int] = {}
        # per-camera zone configuration
        self._camera_zones: dict[str, dict] = {}

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

    def submit_frame(self, camera_id: str, frame: Any, zone_config: dict | None = None) -> None:
        """Add a frame to the processing queue. Overwrites if full (keeps only latest)."""
        if not self._running:
            return
        
        with self._frames_lock:
            # Update or clear camera zone config
            self._camera_zones[camera_id] = zone_config

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
                camera_items: list[tuple[str, Any]] = []
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
                        if self.demo_mode or self.model_path is None:
                            counter = self._demo_frame_counter.get(camera_id, 0) + 1
                            self._demo_frame_counter[camera_id] = counter
                            detections = generate_demo_detections(frame, counter, {"x1": 0, "y1": 0, "x2": frame.shape[1], "y2": frame.shape[0], "name": "Zone"})
                        else:
                            # ensure per-camera model instance for persistent tracking
                            cam_model = self._camera_models.get(camera_id)
                            if cam_model is None:
                                cam_model = load_model(self.model_path)
                                self._camera_models[camera_id] = cam_model

                            # run tracker-based inference on the latest frame (per-camera model)
                            is_diag = getattr(self, "diagnostic_mode", False)
                            detections, plot_img = track_frame(cam_model, frame, self.confidence, imgsz=DEFAULT_IMG_SIZE, tracker=TRACKER_CONFIG, diagnostic=is_diag)

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
                            
                        # Apply restricted zone intrusion detection if configured for this camera
                        zone_cfg = self._camera_zones.get(camera_id)
                        if not self.demo_mode and zone_cfg and len(stable_detections) > 0:
                            try:
                                h, w = frame.shape[:2]
                                validated_zone = validate_zone_coordinates(zone_cfg, w, h)
                                
                                # Scale zone coordinates if the frame was resized for inference
                                if "ref_width" in zone_cfg and "ref_height" in zone_cfg:
                                    rw = zone_cfg["ref_width"]
                                    rh = zone_cfg["ref_height"]
                                    rx = w / max(1, rw)
                                    ry = h / max(1, rh)
                                    scaled_zone = {
                                        "x1": int(zone_cfg["x1"] * rx),
                                        "y1": int(zone_cfg["y1"] * ry),
                                        "x2": int(zone_cfg["x2"] * rx),
                                        "y2": int(zone_cfg["y2"] * ry),
                                        "name": zone_cfg.get("name", "Restricted Zone")
                                    }
                                    validated_zone = validate_zone_coordinates(scaled_zone, w, h)
                                    
                                intrusion_detections = detect_intrusions(stable_detections, validated_zone)
                                # Append intrusion specific labels
                                for intrusion in intrusion_detections:
                                    # Clone it to add a new event
                                    new_det = intrusion.copy()
                                    new_det["label"] = "restricted_area_intrusion"
                                    new_det["zone"] = validated_zone["name"]
                                    stable_detections.append(new_det)
                                    
                            except Exception as e:
                                print(f"Error checking intrusions for {camera_id}: {e}")

                        # annotate frame: if diagnostic, prefer Ultralytics' own plot for direct comparison
                        try:
                            if getattr(self, "diagnostic_mode", False) and not self.demo_mode and 'plot_img' in locals() and plot_img is not None:
                                annotated = plot_img
                            else:
                                annotated = draw_detections(frame, stable_detections) if stable_detections else frame.copy()

                            # Draw restricted zone boundary on feed if configured
                            if zone_cfg and not self.demo_mode:
                                h, w = annotated.shape[:2]
                                zx1 = int(zone_cfg.get("x1", 0))
                                zy1 = int(zone_cfg.get("y1", 0))
                                zx2 = int(zone_cfg.get("x2", 0))
                                zy2 = int(zone_cfg.get("y2", 0))
                                if "ref_width" in zone_cfg and "ref_height" in zone_cfg:
                                    rx = w / max(1, zone_cfg["ref_width"])
                                    ry = h / max(1, zone_cfg["ref_height"])
                                    zx1, zx2 = int(zx1 * rx), int(zx2 * rx)
                                    zy1, zy2 = int(zy1 * ry), int(zy2 * ry)
                                z_name = zone_cfg.get("name", "Restricted Area")
                                cv2.rectangle(annotated, (zx1, zy1), (zx2, zy2), (0, 140, 255), 2)
                                z_tag = f"RESTRICTED: {z_name}"
                                (zt_w, zt_h), _ = cv2.getTextSize(z_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                                tag_y = max(zt_h + 4, zy1)
                                cv2.rectangle(annotated, (zx1, max(0, tag_y - zt_h - 6)), (zx1 + zt_w + 10, tag_y), (0, 140, 255), -1)
                                cv2.putText(annotated, z_tag, (zx1 + 5, tag_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                        except Exception:
                            annotated = frame
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
                
                # Proper throttle: sleep for the remainder of the interval
                sleep_time = interval - elapsed
                if sleep_time > 0.001:
                    time.sleep(sleep_time)
                elif not camera_items:
                    # No frames to process — yield to avoid 100% CPU spin
                    time.sleep(0.005)
                else:
                    # Let the thread breathe just for a fraction of a millisecond
                    time.sleep(0.001)
                    
        except Exception as exc:
            import traceback

            self.status_updated.emit(f"Inference thread error: {exc}")
            traceback.print_exc()
