from __future__ import annotations

import cv2
import sys
import time

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QDialog,
)

from config import MODELS_DIR, BASE_DIR
from core.alert_manager import AlertManager
from core.camera_db import add_camera, delete_camera, get_camera, list_cameras, update_camera
from core.camera_worker import CameraWorker
from core.inference_manager import InferenceManager
from core.model_utils import resolve_model_path
from ui.alert_panel import AlertPanel
from ui.camera_dialog import CameraDialog
from ui.camera_tile import CameraTile


class CameraDiscoveryWorker(QThread):
    """Scans USB indices 0..5 for available cameras in a background thread."""

    camera_found = Signal(int)  # emits the USB index
    finished_scan = Signal()

    def run(self):
        for idx in range(6):
            try:
                if sys.platform == "win32":
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(idx)
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        self.camera_found.emit(idx)
                else:
                    try:
                        cap.release()
                    except Exception:
                        pass
            except Exception:
                continue
        self.finished_scan.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Safety Monitor")
        self.resize(1200, 700)

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        add_action = QAction("Add Camera", self)
        add_action.triggered.connect(self.add_camera_dialog)
        toolbar.addAction(add_action)

        remove_action = QAction("Remove Camera", self)
        remove_action.triggered.connect(self.remove_selected_camera)
        toolbar.addAction(remove_action)

        connect_action = QAction("Connect Selected", self)
        connect_action.triggered.connect(self.connect_selected)
        toolbar.addAction(connect_action)

        disconnect_action = QAction("Disconnect Selected", self)
        disconnect_action.triggered.connect(self.disconnect_selected)
        toolbar.addAction(disconnect_action)

        connect_all_action = QAction("Connect All", self)
        connect_all_action.triggered.connect(self.connect_all)
        toolbar.addAction(connect_all_action)

        disconnect_all_action = QAction("Disconnect All", self)
        disconnect_all_action.triggered.connect(self.disconnect_all)
        toolbar.addAction(disconnect_all_action)

        focus_action = QAction("Focus Selected", self)
        focus_action.triggered.connect(self.focus_selected)
        toolbar.addAction(focus_action)

        zone_action = QAction("Draw Restricted Zone", self)
        zone_action.triggered.connect(self.draw_zone_dialog)
        toolbar.addAction(zone_action)

        toolbar.addSeparator()

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["1x1", "2x2", "3x3", "4x4"])
        self.layout_combo.setCurrentIndex(1)
        self.layout_combo.currentIndexChanged.connect(self.on_layout_changed)
        toolbar.addWidget(self.layout_combo)

        central = QWidget()
        main_layout = QHBoxLayout()

        # Left camera list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_layout.addWidget(QLabel("Cameras"))
        self.camera_list = QListWidget()
        left_layout.addWidget(self.camera_list)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_cameras)
        left_layout.addWidget(refresh_btn)

        # Center grid
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_panel.setLayout(center_layout)
        center_layout.addWidget(QLabel("Preview"))
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_widget.setLayout(self.grid_layout)
        center_layout.addWidget(self.grid_widget)

        # initial tiles for 2x2
        self.current_rows, self.current_cols = 2, 2
        self.tiles: List[CameraTile] = []
        self._create_tiles(self.current_rows, self.current_cols)

        # Right alert panel
        right_panel = AlertPanel()
        self.alert_panel = right_panel

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(center_panel, 3)
        main_layout.addWidget(right_panel, 1)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Ready")


        self._workers: dict[str, CameraWorker] = {}
        self._camera_tile_map: dict[str, CameraTile] = {}
        self._camera_config_cache: dict[str, dict] = {}
        self._latest_detections: dict[str, list] = {}
        self._last_frame_display: dict[str, float] = {}
        self._last_annotation_display: dict[str, float] = {}

        # Inference manager: load default model if available
        model_path = resolve_model_path(base_dir=BASE_DIR, models_dir=MODELS_DIR)

        from config import DEFAULT_AI_FPS
        self.inference = InferenceManager(model_path=model_path, ai_fps=DEFAULT_AI_FPS, demo_mode=(model_path is None))
        self.inference.detection_ready.connect(self.on_detections)
        self.inference.status_updated.connect(lambda s: self.statusBar().showMessage(s))
        self.inference.start_manager()

        # Alert manager
        self.alerts = AlertManager()

        self.refresh_cameras()
        # Discover cameras in background thread to avoid blocking UI
        self._discovery = CameraDiscoveryWorker()
        self._discovery.camera_found.connect(self._on_camera_discovered)
        self._discovery.finished_scan.connect(lambda: self.statusBar().showMessage("Camera scan complete"))
        QTimer.singleShot(500, self._discovery.start)

    def add_camera_dialog(self) -> None:
        dlg = CameraDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_cameras()

    def refresh_cameras(self) -> None:
        self.camera_list.clear()
        cams = list_cameras()
        for cam in cams:
            text = f"{cam['camera_id']} — {cam.get('name') or cam.get('source')}"
            item = self.camera_list.addItem(text)
        # ensure items store camera_id in user role
        for idx in range(self.camera_list.count()):
            item = self.camera_list.item(idx)
            text = item.text()
            camera_id = text.split(" — ")[0]
            item.setData(Qt.UserRole, camera_id)


    def draw_zone_dialog(self) -> None:
        item = self.camera_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a camera from the list on the left to draw a zone.")
            return
        selected_id = item.data(Qt.UserRole)

        tile = self._camera_tile_map.get(selected_id)
        if not tile or not tile.preview.pixmap() or tile.preview.pixmap().isNull():
            QMessageBox.warning(self, "No Feed", "Please connect the camera and wait for a frame before drawing a zone.")
            return

        from ui.zone_dialog import ZoneDialog
        import json
        from core.camera_db import update_camera

        dialog = ZoneDialog(selected_id, tile.preview.pixmap(), self)
        if dialog.exec() == QDialog.Accepted:
            zone_data = dialog.get_zone_data()
            if zone_data:
                zone_json = json.dumps(zone_data)
                try:
                    update_camera(selected_id, {"zone_config": zone_json})
                    if selected_id in self._camera_config_cache:
                        self._camera_config_cache[selected_id]["zone_config"] = zone_json
                    QMessageBox.information(self, "Success", "Restricted zone saved successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save zone: {e}")

    def connect_selected(self) -> None:
        item = self.camera_list.currentItem()
        if not item:
            QMessageBox.information(self, "Connect", "Select a camera first.")
            return
        camera_id = item.data(Qt.UserRole)
        cam = get_camera(camera_id)
        if not cam:
            QMessageBox.warning(self, "Connect", "Camera record not found.")
            return

        source = cam.get("source")
        if camera_id in self._workers:
            QMessageBox.information(self, "Connect", "Camera already connected.")
            return

        # Cache camera config to avoid per-frame DB queries
        self._camera_config_cache[camera_id] = cam

        worker = CameraWorker(camera_id=camera_id, source=source)
        worker.frame_received.connect(self.on_frame)
        worker.status_updated.connect(self.on_status)
        self._workers[camera_id] = worker
        worker.start()
        self.statusBar().showMessage(f"Connecting {camera_id}...")

        # assign a free tile
        free_tile = self._find_free_tile()
        if free_tile:
            self._camera_tile_map[camera_id] = free_tile
            free_tile.update_info(f"{camera_id}: Connecting")
        # ensure analytics enabled for live inference when connected
        try:
            update_camera(camera_id, {"analytics_enabled": 1})
            self._camera_config_cache[camera_id]["analytics_enabled"] = 1
        except Exception:
            pass

    def on_frame(self, camera_id: str, frame) -> None:
        analytics_enabled = False
        # submit frame for inference if manager running and analytics enabled (cached)
        if hasattr(self, "inference") and self.inference is not None:
            cam = self._camera_config_cache.get(camera_id)
            if cam and cam.get("analytics_enabled", 0):
                analytics_enabled = True
                
                # Extract and parse zone config if available
                zone_config = None
                zone_json = cam.get("zone_config")
                if zone_json:
                    import json
                    try:
                        zone_config = json.loads(zone_json)
                    except Exception:
                        pass
                        
                self.inference.submit_frame(camera_id, frame, zone_config=zone_config)

        if not analytics_enabled:
            now = time.time()
            tile = self._camera_tile_map.get(camera_id)
            if tile:
                last_display = self._last_frame_display.get(camera_id, 0.0)
                if now - last_display >= 0.03:
                    self._last_frame_display[camera_id] = now
                    tile.show_frame(frame)

    def on_detections(self, camera_id: str, detections: object, annotated_frame: object) -> None:
        tile = self._camera_tile_map.get(camera_id)
        if not tile:
            return

        # perfectly sync the display frame with the exact detections (no trailing lag or blinking)
        if annotated_frame is not None:
            now = time.time()
            last_display = self._last_annotation_display.get(camera_id, 0.0)
            if now - last_display >= 0.03:
                self._last_annotation_display[camera_id] = now
                tile.show_frame(annotated_frame)

        # Update summary info
        tile = self._camera_tile_map.get(camera_id)
        if not tile:
            return

        if not detections:
            tile.update_info(f"{camera_id}: No detections")
            return

        labels = [d.get("label") for d in detections[:3]]
        tile.update_info(f"{camera_id}: {', '.join(labels)}")

        # Active Alerts: flash red for critical incidents
        from rules import severity_for_event
        for d in detections:
            if severity_for_event(d.get("label", "")) == "critical":
                tile.set_alert_state(True)
                break

        # Process detections into alerts and DB entries (using cached config)
        try:
            cam = self._camera_config_cache.get(camera_id)
            cam_name = cam.get("name") if cam else camera_id
            logged = self.alerts.process_detections(camera_id, cam_name, detections, annotated_frame)
            for a in logged:
                self.alert_panel.add_alert(a)
        except Exception:
            pass

    def on_status(self, camera_id: str, status: str) -> None:
        tile = self._camera_tile_map.get(camera_id)
        if tile:
            tile.update_info(f"{camera_id}: {status}")
        self.statusBar().showMessage(f"{camera_id} — {status}")

    def disconnect_selected(self) -> None:
        item = self.camera_list.currentItem()
        if not item:
            QMessageBox.information(self, "Disconnect", "Select a camera first.")
            return
        camera_id = item.data(Qt.UserRole)
        worker = self._workers.get(camera_id)
        if not worker:
            QMessageBox.information(self, "Disconnect", "Camera is not connected.")
            return
        try:
            worker.stop()
            # wait briefly for thread to finish
            worker.wait(3000)
        except Exception:
            pass
        # only remove mapping if thread is not running
        try:
            if not worker.isRunning():
                if camera_id in self._workers:
                    del self._workers[camera_id]
            else:
                QMessageBox.warning(self, "Disconnect", "Failed to stop thread cleanly; try again.")
                return
        except Exception:
            pass
        tile = self._camera_tile_map.pop(camera_id, None)
        if tile:
            tile.preview.clear()
            tile.update_info(f"{camera_id}: Disconnected")

    def connect_all(self) -> None:
        cams = list_cameras()
        for cam in cams:
            camera_id = cam["camera_id"]
            # select item in list
            for idx in range(self.camera_list.count()):
                item = self.camera_list.item(idx)
                if item.data(Qt.UserRole) == camera_id:
                    self.camera_list.setCurrentItem(item)
                    self.connect_selected()
                    break

    def disconnect_all(self) -> None:
        for camera_id, worker in list(self._workers.items()):
            try:
                worker.stop()
                worker.wait(3000)
            except Exception:
                pass
            try:
                if not worker.isRunning() and camera_id in self._workers:
                    del self._workers[camera_id]
            except Exception:
                pass
            tile = self._camera_tile_map.pop(camera_id, None)
            if tile:
                tile.preview.clear()
                tile.update_info(f"{camera_id}: Disconnected")

    def on_layout_changed(self, index: int) -> None:
        mapping = {0: (1, 1), 1: (2, 2), 2: (3, 3), 3: (4, 4)}
        rows, cols = mapping.get(index, (2, 2))
        self._create_tiles(rows, cols)

    def _create_tiles(self, rows: int, cols: int) -> None:
        # remove existing widgets
        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                self.grid_layout.removeWidget(w)
                w.setParent(None)
        # preserve currently assigned camera ids in order
        existing_map = getattr(self, "_camera_tile_map", {})
        assigned_camera_ids = list(existing_map.keys())
        self.tiles = []
        self._camera_tile_map = {}
        self.current_rows, self.current_cols = rows, cols
        for r in range(rows):
            for c in range(cols):
                tile = CameraTile()
                tile.double_clicked.connect(lambda t=tile: self._toggle_maximise(t))
                self.grid_layout.addWidget(tile, r, c)
                self.tiles.append(tile)
        # reassign cameras to tiles in order
        for idx, cam_id in enumerate(assigned_camera_ids):
            if idx < len(self.tiles):
                self._camera_tile_map[cam_id] = self.tiles[idx]
                self.tiles[idx].update_info(f"{cam_id}: Restored")

    def _find_free_tile(self) -> CameraTile | None:
        assigned = set(self._camera_tile_map.values())
        for t in self.tiles:
            if t not in assigned:
                return t
        return None

    def _toggle_maximise(self, tile: CameraTile) -> None:
        # simple maximise: if tile is full size, restore; otherwise show only that tile
        if tile.maximumHeight() > 0 and tile.maximumHeight() > 300:
            # already maximised? restore grid
            self.on_layout_changed(self.layout_combo.currentIndex())
            return
        # clear grid and show single tile
        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                self.grid_layout.removeWidget(w)
                w.setParent(None)
        self.grid_layout.addWidget(tile, 0, 0)
        tile.setMaximumHeight(9999)

    def remove_selected_camera(self) -> None:
        item = self.camera_list.currentItem()
        if not item:
            QMessageBox.information(self, "Remove", "Select a camera first.")
            return
        camera_id = item.data(Qt.UserRole)
        # stop worker if running
        worker = self._workers.get(camera_id)
        if worker:
            try:
                worker.stop()
            except Exception:
                pass
            try:
                if camera_id in self._workers:
                    del self._workers[camera_id]
            except Exception:
                pass
        # remove DB record
        try:
            delete_camera(camera_id)
        except Exception as exc:
            QMessageBox.warning(self, "Remove", f"Failed to remove camera: {exc}")
            return
        # remove mapping, cache, and refresh UI
        self._camera_config_cache.pop(camera_id, None)
        tile = self._camera_tile_map.pop(camera_id, None)
        if tile:
            tile.preview.clear()
            tile.update_info(f"{camera_id}: Removed")
        self.refresh_cameras()

    def focus_selected(self) -> None:
        item = self.camera_list.currentItem()
        if not item:
            QMessageBox.information(self, "Focus", "Select a camera first.")
            return
        camera_id = item.data(Qt.UserRole)
        tile = self._camera_tile_map.get(camera_id)
        if not tile:
            QMessageBox.information(self, "Focus", "Camera is not connected or not in the grid.")
            return
        self._toggle_maximise(tile)

    def _on_camera_discovered(self, idx: int) -> None:
        """Called from CameraDiscoveryWorker (on main thread via signal) when a USB camera is found."""
        camera_id = f"CAM-USB-{idx}"
        existing = list_cameras()
        found = None
        for cam in existing:
            if str(cam.get("source")) == str(idx) or cam.get("camera_id") == camera_id:
                found = cam
                break

        if not found:
            cam_data = {
                "camera_id": camera_id,
                "name": f"USB Camera {idx}",
                "location": "",
                "source_type": "USB",
                "source": str(idx),
                "username": None,
                "enabled": True,
                "analytics_enabled": True,
                "recording_enabled": False,
                "expected_resolution": None,
                "expected_fps": None,
            }
            try:
                add_camera(cam_data)
            except Exception:
                return
            self.refresh_cameras()
        else:
            camera_id = found.get("camera_id")

        # select and connect
        for i in range(self.camera_list.count()):
            item = self.camera_list.item(i)
            if item.data(Qt.UserRole) == camera_id:
                self.camera_list.setCurrentItem(item)
                self.connect_selected()
                break

    def closeEvent(self, event) -> None:
        # Disconnect all cameras first, then stop inference manager
        try:
            self.disconnect_all()
        except Exception:
            pass

        try:
            if hasattr(self, "inference") and self.inference is not None:
                self.inference.stop_manager()
        except Exception:
            pass

        super().closeEvent(event)
