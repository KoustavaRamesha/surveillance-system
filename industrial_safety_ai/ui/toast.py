from __future__ import annotations

import os
import subprocess
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QPoint
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QGraphicsOpacityEffect,
    QSizePolicy,
)


class ToastNotification(QFrame):
    """Floating interactive toast notification for real-time safety breaches."""

    dismissed = Signal(object)              # self
    view_snapshot_requested = Signal(dict) # alert
    resolve_requested = Signal(dict)       # alert

    THEMES = {
        "critical": {
            "border": "#EF4444",
            "bg": "#1C1114",
            "pill_bg": "#DC2626",
            "pill_text": "#FFFFFF",
            "title_color": "#FCA5A5",
            "bar_color": "#EF4444",
            "icon": "🚨",
            "badge": "CRITICAL THREAT",
        },
        "high": {
            "border": "#F97316",
            "bg": "#1C140E",
            "pill_bg": "#EA580C",
            "pill_text": "#FFFFFF",
            "title_color": "#FDBA74",
            "bar_color": "#F97316",
            "icon": "⚠️",
            "badge": "HIGH WARNING",
        },
        "medium": {
            "border": "#F59E0B",
            "bg": "#1B170E",
            "pill_bg": "#D97706",
            "pill_text": "#000000",
            "title_color": "#FCD34D",
            "bar_color": "#F59E0B",
            "icon": "⚡",
            "badge": "MEDIUM RISK",
        },
        "low": {
            "border": "#10B981",
            "bg": "#0E1A14",
            "pill_bg": "#059669",
            "pill_text": "#FFFFFF",
            "title_color": "#6EE7B7",
            "bar_color": "#10B981",
            "icon": "🛡️",
            "badge": "NOTICE",
        },
    }

    def __init__(self, alert: dict[str, Any], parent: QWidget, duration_ms: int = 6000):
        super().__init__(parent)
        self.alert = alert
        self.duration_ms = duration_ms
        self.remaining_ms = duration_ms
        self.is_paused = False

        sev = str(alert.get("severity", "Medium")).lower()
        self.theme = self.THEMES.get(sev, self.THEMES["medium"])

        self.setFixedWidth(340)
        self.setAttribute(Qt.WA_Hover, True)
        self.setObjectName("ToastFrame")

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame#ToastFrame {{
                background-color: {self.theme['bg']};
                border: 1px solid {self.theme['border']};
                border-left: 5px solid {self.theme['border']};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 6)
        layout.setSpacing(6)

        # Header: Icon + Badge + Event + Close
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        badge_lbl = QLabel(f" {self.theme['icon']} {self.theme['badge']} ")
        badge_lbl.setFont(QFont("Arial", 8, QFont.Bold))
        badge_lbl.setStyleSheet(f"""
            background: {self.theme['pill_bg']};
            color: {self.theme['pill_text']};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        header_row.addWidget(badge_lbl)

        time_str = self.alert.get("timestamp") or "Just now"
        time_lbl = QLabel(time_str)
        time_lbl.setFont(QFont("Arial", 8))
        time_lbl.setStyleSheet("color: #94A3B8;")
        header_row.addWidget(time_lbl)

        header_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)
        close_btn.clicked.connect(self.dismiss)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # Title
        raw_event = str(self.alert.get("event_type", "Violation")).replace("_", " ").title()
        title_lbl = QLabel(raw_event)
        title_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {self.theme['title_color']};")
        layout.addWidget(title_lbl)

        # Location details (Camera & Zone)
        cam_name = self.alert.get("camera_name") or self.alert.get("camera_id") or "Camera"
        zone_name = self.alert.get("zone") or "Global"
        loc_row = QHBoxLayout()
        loc_row.setSpacing(6)

        cam_chip = QLabel(f"📹 {cam_name}")
        cam_chip.setStyleSheet("background: #222634; color: #CBD5E1; border-radius: 3px; padding: 2px 5px; font-size: 10px;")
        loc_row.addWidget(cam_chip)

        zone_chip = QLabel(f"📍 {zone_name}")
        zone_chip.setStyleSheet("background: #222634; color: #CBD5E1; border-radius: 3px; padding: 2px 5px; font-size: 10px;")
        loc_row.addWidget(zone_chip)

        conf_val = float(self.alert.get("confidence", 0.0))
        if conf_val > 0:
            conf_chip = QLabel(f"🎯 {int(conf_val * 100)}%")
            conf_chip.setStyleSheet("background: #222634; color: #93C5FD; border-radius: 3px; padding: 2px 5px; font-size: 10px; font-weight: bold;")
            loc_row.addWidget(conf_chip)

        loc_row.addStretch()
        layout.addLayout(loc_row)

        # Recommendation callout if present
        rec = self.alert.get("recommendation")
        if rec:
            rec_lbl = QLabel(f"⚡ {rec}")
            rec_lbl.setWordWrap(True)
            rec_lbl.setStyleSheet("color: #FCD34D; font-size: 10px; background: rgba(0,0,0,0.25); border-radius: 4px; padding: 3px 6px;")
            layout.addWidget(rec_lbl)

        # Action Buttons
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        if self.alert.get("evidence"):
            snap_btn = QPushButton("📷 View Snapshot")
            snap_btn.setCursor(QCursor(Qt.PointingHandCursor))
            snap_btn.setFixedHeight(24)
            snap_btn.setStyleSheet("""
                QPushButton {
                    background: #222634;
                    color: #E2E8F0;
                    border: 1px solid #3B4252;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: #3B4252;
                    color: #FFFFFF;
                }
            """)
            snap_btn.clicked.connect(self._on_view_snapshot)
            act_row.addWidget(snap_btn)

        act_row.addStretch()

        res_btn = QPushButton("✔ Resolve")
        res_btn.setCursor(QCursor(Qt.PointingHandCursor))
        res_btn.setFixedHeight(24)
        res_btn.setStyleSheet("""
            QPushButton {
                background: #064E3B;
                color: #6EE7B7;
                border: 1px solid #059669;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
            }
        """)
        res_btn.clicked.connect(self._on_resolve)
        act_row.addWidget(res_btn)

        layout.addLayout(act_row)

        # Progress bar showing auto-dismiss countdown
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, self.duration_ms)
        self.progress_bar.setValue(self.duration_ms)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: {self.theme['bar_color']};
                border-radius: 1px;
            }}
        """)
        layout.addWidget(self.progress_bar)

    def _setup_timer(self):
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(50)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

    def _on_tick(self):
        if self.is_paused:
            return
        self.remaining_ms -= 50
        self.progress_bar.setValue(max(0, self.remaining_ms))
        if self.remaining_ms <= 0:
            self.tick_timer.stop()
            self.dismiss()

    def enterEvent(self, event):
        self.is_paused = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_paused = False
        super().leaveEvent(event)

    def _on_view_snapshot(self):
        self.view_snapshot_requested.emit(self.alert)

    def _on_resolve(self):
        self.resolve_requested.emit(self.alert)
        self.dismiss()

    def dismiss(self):
        self.tick_timer.stop()
        self.dismissed.emit(self)


class ToastNotificationManager(QWidget):
    """Manages positioning, stacking, and audio alerts for floating safety toasts."""

    view_snapshot_requested = Signal(dict)
    resolve_requested = Signal(dict)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.toasts: list[ToastNotification] = []
        self.sound_enabled: bool = True
        self.max_toasts: int = 4

        # Follow parent resize
        if parent:
            parent.installEventFilter(self)

    def set_sound_enabled(self, enabled: bool):
        self.sound_enabled = enabled

    def show_alert_toast(self, alert: dict[str, Any]):
        """Create and stack a new toast notification."""
        parent_widget = self.parentWidget()
        if not parent_widget:
            return

        # Play sound if enabled
        if self.sound_enabled:
            self._play_alert_chime(str(alert.get("severity", "")).lower())

        # If too many toasts, dismiss oldest
        if len(self.toasts) >= self.max_toasts:
            oldest = self.toasts.pop(0)
            oldest.deleteLater()

        toast = ToastNotification(alert, parent_widget)
        toast.dismissed.connect(self._remove_toast)
        toast.view_snapshot_requested.connect(self.view_snapshot_requested.emit)
        toast.resolve_requested.connect(self.resolve_requested.emit)

        toast.show()
        toast.raise_()
        self.toasts.append(toast)
        self.reposition_toasts()

    def _remove_toast(self, toast: ToastNotification):
        if toast in self.toasts:
            self.toasts.remove(toast)
        toast.deleteLater()
        self.reposition_toasts()

    def reposition_toasts(self):
        """Align toasts to bottom-right corner of the parent widget."""
        parent = self.parentWidget()
        if not parent:
            return

        parent_w = parent.width()
        parent_h = parent.height()

        margin_right = 24
        margin_bottom = 36
        spacing = 10

        curr_y = parent_h - margin_bottom

        for toast in reversed(self.toasts):
            t_w = toast.width()
            t_h = toast.height()
            x = parent_w - t_w - margin_right
            y = curr_y - t_h
            toast.move(x, y)
            toast.raise_()
            curr_y = y - spacing

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() == event.Type.Resize:
            self.reposition_toasts()
        return super().eventFilter(watched, event)

    def _play_alert_chime(self, severity: str):
        """Play non-blocking subtle audio cue."""
        import threading
        def _beep():
            try:
                import winsound
                if severity == "critical":
                    winsound.Beep(1200, 180)
                    winsound.Beep(1600, 220)
                elif severity == "high":
                    winsound.Beep(950, 180)
                else:
                    winsound.Beep(700, 120)
            except Exception:
                pass

        threading.Thread(target=_beep, daemon=True).start()
