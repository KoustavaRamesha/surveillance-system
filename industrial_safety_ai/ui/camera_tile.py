from __future__ import annotations

import math
import time
import cv2
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QGraphicsOpacityEffect


class CameraTile(QFrame):
    """
    High-tech surveillance terminal tile with animated threat HUD,
    sinusoidal pulsating threat glow, and tactical reticle overlays.
    """

    double_clicked = Signal()

    THREAT_COLORS = {
        "critical": {"border": "#EF4444", "glow_rgb": (239, 68, 68), "bg": "rgba(239, 68, 68, 0.12)", "text": "#FCA5A5"},
        "high":     {"border": "#F97316", "glow_rgb": (249, 115, 22), "bg": "rgba(249, 115, 22, 0.10)", "text": "#FDBA74"},
        "medium":   {"border": "#F59E0B", "glow_rgb": (245, 158, 11), "bg": "rgba(245, 158, 11, 0.08)", "text": "#FCD34D"},
        "low":      {"border": "#06B6D4", "glow_rgb": (6, 182, 212), "bg": "rgba(6, 182, 212, 0.06)", "text": "#67E8F9"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CameraTile")
        self.setMinimumSize(320, 240)

        self._alert_active = False
        self._alert_severity = "critical"
        self._glow_phase = 0.0
        self._last_set_style = ""

        # Alert auto-clear timer
        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(self._clear_alert)

        # Smooth pulsating glow animation timer (30 FPS)
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(33)
        self._glow_timer.timeout.connect(self._on_glow_pulse)

        self._setup_ui()
        self._clear_alert()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # -------------------------------------------------------------
        # 1. Header HUD Bar
        # -------------------------------------------------------------
        self.hud_header = QHBoxLayout()
        self.hud_header.setSpacing(6)

        # Camera Identifier Badge
        self.cam_badge = QLabel("CAM --")
        self.cam_badge.setFont(QFont("Arial", 8, QFont.Bold))
        self.cam_badge.setStyleSheet("""
            background: #182030;
            color: #93C5FD;
            border: 1px solid #2B3A55;
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 10px;
        """)
        self.hud_header.addWidget(self.cam_badge)

        # Pulsing Live Indicator
        self.live_indicator = QLabel("● STANDBY")
        self.live_indicator.setFont(QFont("Arial", 8, QFont.Bold))
        self.live_indicator.setStyleSheet("color: #64748B; font-size: 9px;")
        self.hud_header.addWidget(self.live_indicator)

        # Animated Threat Banner (shown only on active alert)
        self.threat_banner = QLabel("🚨 THREAT ACTIVE")
        self.threat_banner.setFont(QFont("Arial", 8, QFont.Bold))
        self.threat_banner.setStyleSheet("""
            background: #EF4444;
            color: #FFFFFF;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 9px;
            font-weight: bold;
        """)
        self.threat_banner.setVisible(False)
        self.hud_header.addWidget(self.threat_banner)

        self.hud_header.addStretch()

        # Restricted Zone Tag
        self.zone_badge = QLabel("")
        self.zone_badge.setFont(QFont("Arial", 8))
        self.zone_badge.setStyleSheet("""
            background: #271733;
            color: #E879F9;
            border: 1px solid #48235F;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 9px;
            font-weight: 500;
        """)
        self.zone_badge.setVisible(False)
        self.hud_header.addWidget(self.zone_badge)

        layout.addLayout(self.hud_header)

        # -------------------------------------------------------------
        # 2. Video Preview Canvas
        # -------------------------------------------------------------
        self.preview = QLabel("No Signal\nDouble click or connect camera feed")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("""
            background: #06090F;
            color: #475569;
            font-size: 11px;
            border-radius: 6px;
            border: 1px solid #131A29;
        """)
        layout.addWidget(self.preview, 1)

        # -------------------------------------------------------------
        # 3. Bottom Tactical Status Bar
        # -------------------------------------------------------------
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

    def set_alert_state(self, active: bool, severity: str = "critical", duration_ms: int = 3500) -> None:
        """
        Trigger smooth sinusoidal pulsating threat glow and high-tech HUD alert banner.
        Guards against redundant re-styling to keep video render frame rates buttery-smooth.
        """
        sev = str(severity).lower()
        if active:
            # If already active with the same severity, simply extend the timer without re-triggering
            if self._alert_active and self._alert_severity == sev:
                self._alert_timer.start(duration_ms)
                return

            self._alert_active = True
            self._alert_severity = sev
            self._glow_phase = 0.0

            threat_cfg = self.THREAT_COLORS.get(sev, self.THREAT_COLORS["critical"])
            self.threat_banner.setText(f"🚨 {sev.upper()} ALERT")
            self.threat_banner.setStyleSheet(f"""
                background: {threat_cfg['border']};
                color: #FFFFFF;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            """)
            self.threat_banner.setVisible(True)

            self._glow_timer.start()
            self._alert_timer.start(duration_ms)
            self._apply_glow_style(alpha=0.85)
        else:
            self._clear_alert()

    def _on_glow_pulse(self):
        """Oscillate border glow alpha smoothly using a sine wave."""
        if not self._alert_active:
            self._glow_timer.stop()
            return

        self._glow_phase += 0.18
        # Pulse between 0.30 and 0.95
        alpha = 0.30 + 0.65 * (0.5 + 0.5 * math.sin(self._glow_phase))
        self._apply_glow_style(alpha)

    def _apply_glow_style(self, alpha: float):
        sev_cfg = self.THREAT_COLORS.get(self._alert_severity, self.THREAT_COLORS["critical"])
        r, g, b = sev_cfg["glow_rgb"]
        border_rgba = f"rgba({r}, {g}, {b}, {alpha:.2f})"
        bg_rgba = f"rgba({r}, {g}, {b}, {alpha * 0.12:.2f})"

        style = f"""
            QFrame#CameraTile {{
                background-color: {bg_rgba};
                border: 2px solid {border_rgba};
                border-radius: 8px;
            }}
        """
        if style != self._last_set_style:
            self.setStyleSheet(style)
            self._last_set_style = style

    def _clear_alert(self) -> None:
        self._alert_active = False
        self._glow_timer.stop()
        self.threat_banner.setVisible(False)

        resting_style = """
            QFrame#CameraTile {{
                background-color: #0D111A;
                border: 1px solid #1E2638;
                border-radius: 8px;
            }}
            QFrame#CameraTile:hover {{
                border-color: #2F3D59;
            }}
        """
        if resting_style != self._last_set_style:
            self.setStyleSheet(resting_style)
            self._last_set_style = resting_style

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
