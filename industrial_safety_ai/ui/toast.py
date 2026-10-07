from __future__ import annotations

import os
import subprocess
from typing import Any, Optional

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    Signal,
    QPoint,
    QParallelAnimationGroup,
)
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
    """
    Ultra-modern, glassmorphic floating toast notification with fluid spring slide
    and fade animations for real-time safety breaches.
    """

    dismissed = Signal(object)              # self
    view_snapshot_requested = Signal(dict) # alert dict
    resolve_requested = Signal(dict)       # alert dict

    THEMES = {
        "critical": {
            "border": "#EF4444",
            "border_glow": "rgba(239, 68, 68, 0.40)",
            "bg": "#120D12",
            "pill_bg": "#DC2626",
            "pill_text": "#FFFFFF",
            "title_color": "#FCA5A5",
            "bar_color": "#EF4444",
            "pulse_color": "#EF4444",
            "icon": "🚨",
            "badge": "CRITICAL THREAT",
        },
        "high": {
            "border": "#F97316",
            "border_glow": "rgba(249, 115, 22, 0.35)",
            "bg": "#130F0B",
            "pill_bg": "#EA580C",
            "pill_text": "#FFFFFF",
            "title_color": "#FDBA74",
            "bar_color": "#F97316",
            "pulse_color": "#FB923C",
            "icon": "⚠️",
            "badge": "HIGH WARNING",
        },
        "medium": {
            "border": "#F59E0B",
            "border_glow": "rgba(245, 158, 11, 0.30)",
            "bg": "#13110C",
            "pill_bg": "#D97706",
            "pill_text": "#000000",
            "title_color": "#FCD34D",
            "bar_color": "#F59E0B",
            "pulse_color": "#FBBF24",
            "icon": "⚡",
            "badge": "HAZARD ALERT",
        },
        "low": {
            "border": "#10B981",
            "border_glow": "rgba(16, 185, 129, 0.30)",
            "bg": "#0B1410",
            "pill_bg": "#059669",
            "pill_text": "#FFFFFF",
            "title_color": "#6EE7B7",
            "bar_color": "#10B981",
            "pulse_color": "#34D399",
            "icon": "🛡️",
            "badge": "NOTICE",
        },
    }

    def __init__(self, alert: dict[str, Any], parent: QWidget, duration_ms: int = 6500):
        super().__init__(parent)
        self.alert = alert
        self.duration_ms = duration_ms
        self.remaining_ms = duration_ms
        self.is_paused = False
        self.is_dismissing = False

        sev = str(alert.get("severity", "Medium")).lower()
        self.theme = self.THEMES.get(sev, self.THEMES["medium"])

        self.setFixedWidth(360)
        self.setAttribute(Qt.WA_Hover, True)
        self.setObjectName("ToastFrame")

        # Opacity effect for smooth fade animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Pulse timer for live dot indicator
        self._pulse_state = True

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame#ToastFrame {{
                background-color: {self.theme['bg']};
                border: 1px solid {self.theme['border']};
                border-left: 4px solid {self.theme['border']};
                border-radius: 10px;
            }}
            QFrame#ToastFrame:hover {{
                border-color: {self.theme['title_color']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 8)
        layout.setSpacing(8)

        # ---------------------------------------------------------
        # Row 1: Pulsing Dot + Badge + Timestamp + Close Button
        # ---------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        # Pulsing Live Dot
        self.dot_lbl = QLabel("●")
        self.dot_lbl.setFont(QFont("Arial", 9, QFont.Bold))
        self.dot_lbl.setStyleSheet(f"color: {self.theme['pulse_color']};")
        header_row.addWidget(self.dot_lbl)

        # Threat Badge
        badge_lbl = QLabel(f" {self.theme['icon']} {self.theme['badge']} ")
        badge_lbl.setFont(QFont("Arial", 8, QFont.Bold))
        badge_lbl.setStyleSheet(f"""
            background: {self.theme['pill_bg']};
            color: {self.theme['pill_text']};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        header_row.addWidget(badge_lbl)

        # Timestamp
        time_str = self.alert.get("timestamp") or "Just now"
        time_lbl = QLabel(time_str)
        time_lbl.setFont(QFont("Arial", 8))
        time_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        header_row.addWidget(time_lbl)

        header_row.addStretch()

        # Elegant Close Button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 11px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background: rgba(239, 68, 68, 0.8);
                border-color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.dismiss)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # ---------------------------------------------------------
        # Row 2: Event Title (Large, Clear Typography)
        # ---------------------------------------------------------
        raw_event = str(self.alert.get("event_type", "Threat Detected")).replace("_", " ").title()
        title_lbl = QLabel(raw_event)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {self.theme['title_color']}; margin-top: 1px;")
        layout.addWidget(title_lbl)

        # ---------------------------------------------------------
        # Row 3: Metadata Micro-Chips (Camera, Zone, Confidence)
        # ---------------------------------------------------------
        cam_name = self.alert.get("camera_name") or self.alert.get("camera_id") or "Camera"
        zone_name = self.alert.get("zone") or "Restricted Zone"
        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)

        cam_chip = QLabel(f"📹 {cam_name}")
        cam_chip.setStyleSheet("""
            background: #181E2C;
            color: #CBD5E1;
            border: 1px solid #232B3E;
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 500;
        """)
        chips_row.addWidget(cam_chip)

        zone_chip = QLabel(f"📍 {zone_name}")
        zone_chip.setStyleSheet("""
            background: #181E2C;
            color: #CBD5E1;
            border: 1px solid #232B3E;
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 500;
        """)
        chips_row.addWidget(zone_chip)

        conf_val = float(self.alert.get("confidence", 0.0))
        if conf_val > 0:
            conf_chip = QLabel(f"🎯 {int(conf_val * 100)}%")
            conf_chip.setStyleSheet("""
                background: #181E2C;
                color: #93C5FD;
                border: 1px solid #232B3E;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
            chips_row.addWidget(conf_chip)

        chips_row.addStretch()
        layout.addLayout(chips_row)

        # ---------------------------------------------------------
        # Row 4: Actionable Guidance Callout
        # ---------------------------------------------------------
        rec = self.alert.get("recommendation")
        if rec:
            rec_lbl = QLabel(f"⚡ {rec}")
            rec_lbl.setWordWrap(True)
            rec_lbl.setStyleSheet("""
                color: #E2E8F0;
                font-size: 10px;
                background: rgba(0, 0, 0, 0.35);
                border-left: 2px solid #F59E0B;
                border-radius: 3px;
                padding: 4px 8px;
            """)
            layout.addWidget(rec_lbl)

        # ---------------------------------------------------------
        # Row 5: Action Buttons (Snapshot + Quick Resolve)
        # ---------------------------------------------------------
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        if self.alert.get("evidence"):
            snap_btn = QPushButton("📷 View Evidence")
            snap_btn.setCursor(QCursor(Qt.PointingHandCursor))
            snap_btn.setFixedHeight(26)
            snap_btn.setStyleSheet("""
                QPushButton {
                    background: #1E2638;
                    color: #E2E8F0;
                    border: 1px solid #2F3B54;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 10px;
                }
                QPushButton:hover {
                    background: #2D3A54;
                    color: #FFFFFF;
                    border-color: #4B5E86;
                }
            """)
            snap_btn.clicked.connect(self._on_view_snapshot)
            act_row.addWidget(snap_btn)

        act_row.addStretch()

        res_btn = QPushButton("✔ Resolve")
        res_btn.setCursor(QCursor(Qt.PointingHandCursor))
        res_btn.setFixedHeight(26)
        res_btn.setStyleSheet("""
            QPushButton {
                background: #064E3B;
                color: #6EE7B7;
                border: 1px solid #059669;
                border-radius: 5px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 12px;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
                border-color: #10B981;
            }
        """)
        res_btn.clicked.connect(self._on_resolve)
        act_row.addWidget(res_btn)

        layout.addLayout(act_row)

        # ---------------------------------------------------------
        # Row 6: Ultra-thin Animated Countdown Line
        # ---------------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, self.duration_ms)
        self.progress_bar.setValue(self.duration_ms)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.08);
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
        self.tick_timer.setInterval(40)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

        # Dot pulse timer (blinks every 600ms)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(600)
        self.pulse_timer.timeout.connect(self._on_pulse)
        self.pulse_timer.start()

    def _on_pulse(self):
        self._pulse_state = not self._pulse_state
        alpha = "1.0" if self._pulse_state else "0.3"
        self.dot_lbl.setStyleSheet(f"color: {self.theme['pulse_color']}; opacity: {alpha};")

    def _on_tick(self):
        if self.is_paused or self.is_dismissing:
            return
        self.remaining_ms -= 40
        self.progress_bar.setValue(max(0, self.remaining_ms))
        if self.remaining_ms <= 0:
            self.tick_timer.stop()
            self.pulse_timer.stop()
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
        """Initiate smooth slide-out and fade dismissal animation."""
        if self.is_dismissing:
            return
        self.is_dismissing = True
        self.tick_timer.stop()
        self.pulse_timer.stop()
        self.dismissed.emit(self)


class ToastNotificationManager(QWidget):
    """
    Manages fluid physics-based stacking, entry slide-in, dismissal, and
    gentle audio cues for floating surveillance alerts.
    """

    view_snapshot_requested = Signal(dict)
    resolve_requested = Signal(dict)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.toasts: list[ToastNotification] = []
        self.sound_enabled: bool = True
        self.max_toasts: int = 4
        self._active_animations: list[Any] = []

        if parent:
            parent.installEventFilter(self)

    def set_sound_enabled(self, enabled: bool):
        self.sound_enabled = enabled

    def show_alert_toast(self, alert: dict[str, Any]):
        """Create, smoothly animate in, and stack a new toast notification."""
        parent_widget = self.parentWidget()
        if not parent_widget:
            return

        # Play smooth system audio chime
        if self.sound_enabled:
            self._play_alert_chime(str(alert.get("severity", "")).lower())

        # If queue exceeds capacity, dismiss oldest with animation
        if len(self.toasts) >= self.max_toasts:
            oldest = self.toasts[0]
            self._animate_dismiss(oldest)

        toast = ToastNotification(alert, parent_widget)
        toast.dismissed.connect(self._animate_dismiss)
        toast.view_snapshot_requested.connect(self.view_snapshot_requested.emit)
        toast.resolve_requested.connect(self.resolve_requested.emit)

        self.toasts.append(toast)
        toast.show()
        toast.raise_()

        # Compute target position at bottom-right
        target_x, target_y = self._calculate_target_pos(toast, len(self.toasts) - 1)

        # Start position: off-screen right
        start_x = parent_widget.width() + 20
        toast.move(start_x, target_y)

        # Smooth slide-in + fade-in animation group
        anim_group = QParallelAnimationGroup(toast)

        pos_anim = QPropertyAnimation(toast, b"pos")
        pos_anim.setDuration(320)
        pos_anim.setStartValue(QPoint(start_x, target_y))
        pos_anim.setEndValue(QPoint(target_x, target_y))
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        anim_group.addAnimation(pos_anim)

        opacity_anim = QPropertyAnimation(toast.opacity_effect, b"opacity")
        opacity_anim.setDuration(260)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        anim_group.addAnimation(opacity_anim)

        anim_group.start()
        self._active_animations.append(anim_group)
        anim_group.finished.connect(lambda: self._cleanup_anim(anim_group))

        # Smoothly reposition existing toasts to their new heights
        self._animate_reposition()

    def _animate_dismiss(self, toast: ToastNotification):
        """Smoothly slide-out and fade-out before removing."""
        if toast not in self.toasts:
            return
        self.toasts.remove(toast)

        curr_pos = toast.pos()
        target_pos = QPoint(curr_pos.x() + 90, curr_pos.y())

        anim_group = QParallelAnimationGroup(toast)

        pos_anim = QPropertyAnimation(toast, b"pos")
        pos_anim.setDuration(220)
        pos_anim.setStartValue(curr_pos)
        pos_anim.setEndValue(target_pos)
        pos_anim.setEasingCurve(QEasingCurve.InCubic)
        anim_group.addAnimation(pos_anim)

        opacity_anim = QPropertyAnimation(toast.opacity_effect, b"opacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(toast.opacity_effect.opacity())
        opacity_anim.setEndValue(0.0)
        anim_group.addAnimation(opacity_anim)

        def _on_finish():
            toast.deleteLater()
            self._cleanup_anim(anim_group)
            self._animate_reposition()

        anim_group.finished.connect(_on_finish)
        anim_group.start()
        self._active_animations.append(anim_group)

    def _cleanup_anim(self, anim_group):
        if anim_group in self._active_animations:
            self._active_animations.remove(anim_group)

    def _calculate_target_pos(self, toast: ToastNotification, index: int) -> tuple[int, int]:
        """Calculate target bottom-right aligned coordinates for the toast stack."""
        parent = self.parentWidget()
        if not parent:
            return 0, 0

        parent_w = parent.width()
        parent_h = parent.height()

        margin_right = 24
        margin_bottom = 36
        spacing = 10

        curr_y = parent_h - margin_bottom
        t_w = toast.width()
        x = parent_w - t_w - margin_right

        # Walk through toasts from newest (at bottom) to oldest (stacked above)
        for i, t in enumerate(reversed(self.toasts)):
            t_h = t.height() or 130
            y = curr_y - t_h
            curr_y = y - spacing
            if t == toast:
                return x, y

        return x, curr_y

    def _animate_reposition(self):
        """Smoothly slide all existing toasts to their updated vertical slots."""
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
            t_h = toast.height() or 130
            target_x = parent_w - t_w - margin_right
            target_y = curr_y - t_h
            curr_y = target_y - spacing

            curr_pos = toast.pos()
            if curr_pos.x() != target_x or curr_pos.y() != target_y:
                anim = QPropertyAnimation(toast, b"pos", toast)
                anim.setDuration(240)
                anim.setStartValue(curr_pos)
                anim.setEndValue(QPoint(target_x, target_y))
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.start()
                self._active_animations.append(anim)
                anim.finished.connect(lambda a=anim: self._cleanup_anim(a))

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() == event.Type.Resize:
            self._animate_reposition()
        return super().eventFilter(watched, event)

    def _play_alert_chime(self, severity: str):
        """
        Play pleasant, professional Windows native notification sounds.
        Never uses harsh motherboard square-wave beeps.
        """
        try:
            import winsound
            # SystemAsterisk is the sleek, gentle Windows OS chime
            sound_alias = "SystemHand" if severity == "critical" else "SystemAsterisk"
            winsound.PlaySound(sound_alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            pass
