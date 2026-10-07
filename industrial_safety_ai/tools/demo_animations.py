"""
Interactive Animation & Notification Tester.
Demonstrates:
  1. Fluid spring slide-in & fade-in toast notifications (bottom-right).
  2. Smooth vertical card stack repositioning when toasts are added or dismissed.
  3. Sinusoidal pulsating threat border & HUD threat banner on CameraTiles.
  4. Animated fade-in alert cards in the Alert Panel.
  5. Clean, professional OS audio chimes.

Run with:
    python tools/demo_animations.py
"""

from __future__ import annotations

import sys
import numpy as np
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from ui.camera_tile import CameraTile
from ui.alert_panel import AlertPanel
from ui.toast import ToastNotificationManager


class AnimationShowcaseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Safety AI — Animation & Notification Showcase")
        self.resize(1180, 720)
        self.setStyleSheet("background-color: #0A0D14; color: #E2E8F0;")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # Left Side: Controls & Video Grid
        # -------------------------------------------------------------
        left_side = QVBoxLayout()
        left_side.setSpacing(10)

        # Header title
        title_box = QFrame()
        title_box.setStyleSheet("background: #111624; border: 1px solid #1D263B; border-radius: 8px; padding: 6px 12px;")
        tb_layout = QHBoxLayout(title_box)
        title_lbl = QLabel("🎥 Live Surveillance Monitoring & Threat Terminal")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_lbl.setStyleSheet("color: #F8FAFC;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        left_side.addWidget(title_box)

        # Camera Grid (2 tiles)
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(10)

        self.tile1 = CameraTile()
        self.tile1.set_camera_label("CAM-01 (Warehouse)", "Restricted Zone")
        self.tile1.set_live_status(True)

        self.tile2 = CameraTile()
        self.tile2.set_camera_label("CAM-02 (Assembly Line)", "Heavy Machinery")
        self.tile2.set_live_status(True)

        grid_layout.addWidget(self.tile1, 0, 0)
        grid_layout.addWidget(self.tile2, 0, 1)
        left_side.addWidget(grid_widget, 1)

        # Synthetic camera frame generator (synthetic dark gradient with timestamp)
        self._feed_timer = QTimer(self)
        self._feed_timer.setInterval(66)  # ~15 FPS synthetic feed
        self._feed_timer.timeout.connect(self._generate_synthetic_frames)
        self._feed_timer.start()

        # Control Panel Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: #111624; border: 1px solid #1E273C; border-radius: 8px; padding: 10px;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setSpacing(8)

        btn_intrusion = QPushButton("🚨 Trigger Intrusion Alert (High)")
        btn_intrusion.setStyleSheet("""
            QPushButton {
                background: #C2410C;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #EA580C;
            }
            QPushButton:hover { background: #EA580C; }
        """)
        btn_intrusion.clicked.connect(self._trigger_intrusion)
        btn_layout.addWidget(btn_intrusion)

        btn_fire = QPushButton("🔥 Trigger Critical Fire (Critical)")
        btn_fire.setStyleSheet("""
            QPushButton {
                background: #B91C1C;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #EF4444;
            }
            QPushButton:hover { background: #DC2626; }
        """)
        btn_fire.clicked.connect(self._trigger_fire)
        btn_layout.addWidget(btn_fire)

        btn_stack = QPushButton("⚡ Trigger 3 Rapid Stack Alerts")
        btn_stack.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                color: #93C5FD;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #3B82F6;
            }
            QPushButton:hover { background: #2563EB; color: #FFFFFF; }
        """)
        btn_stack.clicked.connect(self._trigger_rapid_stack)
        btn_layout.addWidget(btn_stack)

        left_side.addWidget(btn_frame)
        main_layout.addLayout(left_side, 2)

        # -------------------------------------------------------------
        # Right Side: Enhanced Alert Panel
        # -------------------------------------------------------------
        self.alert_panel = AlertPanel()
        self.alert_panel.setMinimumWidth(380)
        self.alert_panel.focus_camera_requested.connect(self._on_focus_camera)
        main_layout.addWidget(self.alert_panel, 1)

        # Floating Toast Notification Overlay
        self.toast_manager = ToastNotificationManager(self)
        self.toast_manager.view_snapshot_requested.connect(self.alert_panel._open_evidence_dialog)
        self.toast_manager.resolve_requested.connect(lambda a: self.alert_panel._resolve_by_db_id(a.get("db_id")))
        self.alert_panel.sound_toggled.connect(self.toast_manager.set_sound_enabled)

        self._alert_seq = 1

    def _generate_synthetic_frames(self):
        """Generate subtle animated synthetic frames to demonstrate live video."""
        import cv2
        t = time.time()
        
        # Frame 1: Navy tech grid
        f1 = np.zeros((240, 320, 3), dtype=np.uint8)
        f1[:, :] = (20, 24, 35)
        # grid lines
        for y in range(0, 240, 40):
            cv2.line(f1, (0, y), (320, y), (28, 36, 52), 1)
        for x in range(0, 320, 40):
            cv2.line(f1, (x, 0), (x, 240), (28, 36, 52), 1)
        # Animated sweep line
        sweep_x = int((t * 60) % 320)
        cv2.line(f1, (sweep_x, 0), (sweep_x, 240), (45, 65, 95), 2)
        cv2.putText(f1, "CAM-01 [WAREHOUSE DOOR]", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)
        self.tile1.show_frame(f1)

        # Frame 2
        f2 = np.zeros((240, 320, 3), dtype=np.uint8)
        f2[:, :] = (18, 20, 30)
        cv2.putText(f2, "CAM-02 [RESTRICTED PERIMETER]", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)
        self.tile2.show_frame(f2)

    def _trigger_intrusion(self):
        self._alert_seq += 1
        alert = {
            "db_id": self._alert_seq,
            "camera_id": "CAM-01",
            "camera_name": "Warehouse Cam",
            "event_type": "restricted_area_intrusion",
            "severity": "High",
            "confidence": 0.94,
            "zone": "Restricted Zone",
            "recommendation": "Warn the person, notify security, and verify area authorization immediately.",
            "timestamp": time.strftime("%H:%M:%S"),
            "status": "Open",
        }
        # Trigger pulsing glow and threat banner on tile 1
        self.tile1.set_alert_state(True, severity="high", duration_ms=4500)
        # Add to alert panel
        self.alert_panel.add_alert(alert)
        # Smoothly slide in toast
        self.toast_manager.show_alert_toast(alert)

    def _trigger_fire(self):
        self._alert_seq += 1
        alert = {
            "db_id": self._alert_seq,
            "camera_id": "CAM-02",
            "camera_name": "Assembly Line",
            "event_type": "fire",
            "severity": "Critical",
            "confidence": 0.98,
            "zone": "Heavy Machinery",
            "recommendation": "EVACUATE AREA IMMEDIATELY. Sound alarm and notify emergency response team.",
            "timestamp": time.strftime("%H:%M:%S"),
            "status": "Open",
        }
        # Trigger pulsing glow and threat banner on tile 2
        self.tile2.set_alert_state(True, severity="critical", duration_ms=5000)
        # Add to alert panel
        self.alert_panel.add_alert(alert)
        # Smoothly slide in toast
        self.toast_manager.show_alert_toast(alert)

    def _trigger_rapid_stack(self):
        """Trigger multiple alerts in quick succession to demonstrate stacking slide physics."""
        self._trigger_intrusion()
        QTimer.singleShot(400, self._trigger_fire)
        QTimer.singleShot(800, self._trigger_helmet)

    def _trigger_helmet(self):
        self._alert_seq += 1
        alert = {
            "db_id": self._alert_seq,
            "camera_id": "CAM-01",
            "camera_name": "Warehouse Cam",
            "event_type": "no_helmet",
            "severity": "Medium",
            "confidence": 0.88,
            "zone": "Loading Bay",
            "recommendation": "Direct worker to don mandatory hard hat before entering active work area.",
            "timestamp": time.strftime("%H:%M:%S"),
            "status": "Open",
        }
        self.tile1.set_alert_state(True, severity="medium", duration_ms=3500)
        self.alert_panel.add_alert(alert)
        self.toast_manager.show_alert_toast(alert)

    def _on_focus_camera(self, camera_id: str):
        if "01" in camera_id:
            self.tile1.set_alert_state(True, severity="low", duration_ms=2000)
        elif "02" in camera_id:
            self.tile2.set_alert_state(True, severity="low", duration_ms=2000)


def main():
    import time
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = AnimationShowcaseWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    import time
    sys.exit(main())
