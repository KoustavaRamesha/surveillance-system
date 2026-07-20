from __future__ import annotations

import time
import cv2
from typing import Any

from PySide6.QtCore import QThread, Signal


class CameraWorker(QThread):
    """Camera capture worker with automatic reconnection/backoff.

    Signals:
        frame_received(camera_id: str, frame: Any)
        status_updated(camera_id: str, status: str)
    """

    frame_received = Signal(str, object)
    status_updated = Signal(str, str)

    def __init__(
        self,
        camera_id: str,
        source: str | int,
        name: str | None = None,
        reconnect_initial: float = 2.0,
        reconnect_max: float = 30.0,
        display_fps: int = 8,
        parent=None,
    ):
        super().__init__(parent)
        self.camera_id = camera_id
        self.source = source
        self.name = name or camera_id
        try:
            # name the thread for easier debugging
            self.setObjectName(str(self.camera_id))
        except Exception:
            pass
        self._running = False
        self.reconnect_initial = reconnect_initial
        self.reconnect_max = reconnect_max
        self.display_fps = max(1, display_fps)
        self._last_emit_time = 0.0

    def _open_capture(self):
        # Try different backends on Windows for more reliable access
        try:
            if isinstance(self.source, str) and self.source.isdigit():
                idx = int(self.source)
            elif isinstance(self.source, int):
                idx = int(self.source)
            else:
                # assume string URI
                return cv2.VideoCapture(self.source)

            # Try DirectShow first, then MSMF, then default
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap is not None and cap.isOpened():
                        return cap
                    try:
                        cap.release()
                    except Exception:
                        pass
                except Exception:
                    continue
            # final fallback
            return cv2.VideoCapture(idx)
        except Exception:
            return cv2.VideoCapture(self.source)

    def run(self) -> None:
        self._running = True
        backoff = self.reconnect_initial
        cap = None
        try:
            while self._running and not self.isInterruptionRequested():
                self.status_updated.emit(self.camera_id, "Connecting")
                cap = self._open_capture()
                if not cap or not cap.isOpened():
                    self.status_updated.emit(self.camera_id, f"Reconnect in {backoff:.0f}s")
                    time.sleep(backoff)
                    backoff = min(self.reconnect_max, backoff * 2)
                    continue

                # reset backoff after successful open
                backoff = self.reconnect_initial
                self.status_updated.emit(self.camera_id, "Online")

                consecutive_failures = 0
                min_emit_interval = 1.0 / self.display_fps
                while self._running and cap.isOpened() and not self.isInterruptionRequested():
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        consecutive_failures += 1
                        self.status_updated.emit(self.camera_id, "No Frame")
                        time.sleep(0.5)
                        if consecutive_failures >= 5:
                            # treat as lost connection
                            self.status_updated.emit(self.camera_id, "Reconnecting")
                            break
                        continue

                    consecutive_failures = 0
                    now = time.time()
                    if now - self._last_emit_time >= min_emit_interval:
                        self._last_emit_time = now
                        self.frame_received.emit(self.camera_id, frame)
                    # small sleep to avoid flooding UI (display FPS separate from capture rate)
                    time.sleep(0.01)

                # release capture and try reconnecting
                try:
                    if cap is not None and cap.isOpened():
                        cap.release()
                except Exception:
                    pass
                self.status_updated.emit(self.camera_id, "Disconnected")
                time.sleep(backoff)
                backoff = min(self.reconnect_max, backoff * 2)

        except Exception as exc:
            import traceback

            self.status_updated.emit(self.camera_id, f"Error: {exc}")
            traceback.print_exc()
        finally:
            try:
                if cap is not None and cap.isOpened():
                    cap.release()
            except Exception:
                pass
            self.status_updated.emit(self.camera_id, "Stopped")

    def stop(self) -> None:
        # Request cooperative stop and allow interruption
        self._running = False
        try:
            self.requestInterruption()
        except Exception:
            pass
        try:
            if self.isRunning():
                self.wait(5000)
        except Exception:
            pass
