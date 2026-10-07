from __future__ import annotations

import cv2
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFrame


class CameraTile(QFrame):
    """High-tech surveillance terminal tile with HUD overlay and threat-level border glow."""

    double_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CameraTile")
        self.setMinimumSize(320, 240)

        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(self._clear_alert)

        self._setup_ui()
        self._clear_alert()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header HUD
        self.hud_header = QHBoxLayout()
        self.hud_header.setSpacing(6)

        self.cam_badge = QLabel("CAM --")
        self.cam_badge.setFont(QFont("Arial", 8, QFont.Bold))
        self.cam_badge.setStyleSheet("""
            background: #1A2130;
            color: #93C5FD;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 10px;
        """)
        self.hud_header.addWidget(self.cam_badge)

        self.live_indicator = QLabel("● STANDBY")
        self.live_indicator.setFont(QFont("Arial", 8, QFont.Bold))
        self.live_indicator.setStyleSheet("color: #64748B; font-size: 9px;")
        self.hud_header.addWidget(self.live_indicator)

        self.hud_header.addStretch()

        self.zone_badge = QLabel("")
        self.zone_badge.setFont(QFont("Arial", 8))
        self.zone_badge.setStyleSheet("""
            background: #2D1A35;
            color: #E879F9;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 9px;
        """)
        self.zone_badge.setVisible(False)
        self.hud_header.addWidget(self.zone_badge)

        layout.addLayout(self.hud_header)

        # Video preview canvas
        self.preview = QLabel("No Signal\nDouble click or connect camera")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("""
            background: #07090E;
            color: #475569;
            font-size: 11px;
            border-radius: 4px;
        """)
        layout.addWidget(self.preview, 1)

        # Bottom info bar
        self.info = QLabel("Ready")
        self.info.setFont(QFont("Arial", 8))
        self.info.setStyleSheet("color: #94A3B8; padding: 2px 4px; font-size: 10px;")
        layout.addWidget(self.info)

    def set_camera_label(self, label: str, zone_name: str | None = None):
        self.cam_badge.setText(label)
        if zone_name:
            self.zone_badge.setText(f"📍 {zone_name}")
            self.zone_badge.setVisible(True)
        else:
            self.zone_badge.setVisible(False)

    def set_live_status(self, is_live: bool):
        if is_live:
            self.live_indicator.setText("● LIVE")
            self.live_indicator.setStyleSheet("color: #10B981; font-weight: bold; font-size: 9px;")
        else:
            self.live_indicator.setText("● OFFLINE")
            self.live_indicator.setStyleSheet("color: #64748B; font-size: 9px;")

    def set_alert_state(self, active: bool, severity: str = "critical", duration_ms: int = 3000) -> None:
        if active:
            sev = str(severity).lower()
            if sev == "critical":
                border_color = "#EF4444"
                bg_color = "rgba(239, 68, 68, 0.20)"
            elif sev == "high":
                border_color = "#F97316"
                bg_color = "rgba(249, 115, 22, 0.16)"
            elif sev == "medium":
                border_color = "#F59E0B"
                bg_color = "rgba(245, 158, 11, 0.12)"
            elif sev == "low":
                border_color = "#06B6D4"
                bg_color = "rgba(6, 182, 212, 0.10)"
            else:
                border_color = "#10B981"
                bg_color = "rgba(16, 185, 129, 0.08)"

            self.setStyleSheet(f"""
                QFrame#CameraTile {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            self._alert_timer.start(duration_ms)
        else:
            self._clear_alert()

    def _clear_alert(self) -> None:
        self.setStyleSheet("""
            QFrame#CameraTile {{
                background-color: #0E121B;
                border: 1px solid #1E2638;
                border-radius: 8px;
            }}
            QFrame#CameraTile:hover {{
                border-color: #2D3A54;
            }}
        """)

    def update_info(self, text: str) -> None:
        self.info.setText(text)

    def show_frame(self, frame) -> None:
        try:
            target_w = self.preview.width()
            target_h = self.preview.height()
            h, w = frame.shape[:2]
            if w > 0 and h > 0 and target_w > 0 and target_h > 0:
                scale = min(target_w / w, target_h / h)
                if scale < 1.0:
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.preview.setPixmap(QPixmap.fromImage(qimg))
            self.set_live_status(True)
        except Exception:
            self.preview.setText("Unable to display frame")

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
