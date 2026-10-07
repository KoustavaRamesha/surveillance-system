from __future__ import annotations

import os
import subprocess
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPixmap, QCursor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)


class EvidencePreviewDialog(QDialog):
    """Modern modal dialog displaying the captured evidence snapshot with violation details."""

    resolve_requested = Signal(int)  # db_id

    def __init__(self, alert_data: dict[str, Any], parent=None):
        super().__init__(parent)
        self.alert_data = alert_data
        self._db_id = alert_data.get("db_id")

        self.setWindowTitle(f"Evidence Snapshot — {alert_data.get('event_type', 'Incident')}")
        self.resize(780, 580)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1017;
                color: #E2E8F0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel {
                color: #CBD5E1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        sev = str(alert_data.get("severity", "Low")).upper()
        sev_label = QLabel(f"  {sev}  ")
        sev_label.setFont(QFont("Arial", 10, QFont.Bold))
        sev_label.setStyleSheet(self._badge_style(sev))
        header.addWidget(sev_label)

        title = QLabel(f"{str(alert_data.get('event_type', '')).replace('_', ' ').title()}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        header.addWidget(title)

        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1E2330;
                color: #94A3B8;
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #2D3748;
            }
            QPushButton:hover {
                background: #2D3748;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Image preview
        image_label = QLabel("Loading snapshot...")
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("background: #06080C; border: 1px solid #1E2330; border-radius: 8px;")
        image_label.setMinimumSize(660, 370)

        ev_path = alert_data.get("evidence")
        if ev_path and os.path.exists(ev_path):
            pix = QPixmap(ev_path)
            if not pix.isNull():
                image_label.setPixmap(pix.scaled(740, 390, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                image_label.setText("Corrupted or unreadable snapshot file.")
        else:
            image_label.setText("No snapshot image available.")
        layout.addWidget(image_label)

        # Metadata Row
        meta_frame = QFrame()
        meta_frame.setStyleSheet("background: #131722; border: 1px solid #202738; border-radius: 6px; padding: 4px;")
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(14, 8, 14, 8)
        meta_layout.setSpacing(16)

        cam_text = f"📹 <b>Camera:</b> {alert_data.get('camera_name', alert_data.get('camera_id', 'Unknown'))}"
        zone_text = f"📍 <b>Zone:</b> {alert_data.get('zone', 'Global')}"
        time_text = f"🕒 <b>Time:</b> {alert_data.get('timestamp', '--:--:--')}"
        conf_val = float(alert_data.get("confidence", 0.0))
        conf_text = f"🎯 <b>Confidence:</b> {int(conf_val * 100)}%"

        for t in [cam_text, zone_text, time_text, conf_text]:
            lbl = QLabel(t)
            lbl.setTextFormat(Qt.RichText)
            meta_layout.addWidget(lbl)
        meta_layout.addStretch()
        layout.addWidget(meta_frame)

        # Recommendation Banner
        rec = alert_data.get("recommendation")
        if rec:
            rec_frame = QFrame()
            rec_frame.setStyleSheet("background: #231B0D; border: 1px solid #78350F; border-radius: 6px; padding: 6px 12px;")
            rec_layout = QHBoxLayout(rec_frame)
            rec_layout.setContentsMargins(10, 4, 10, 4)
            rec_lbl = QLabel(f"⚡ <b>Action Recommendation:</b> {rec}")
            rec_lbl.setTextFormat(Qt.RichText)
            rec_lbl.setStyleSheet("color: #FCD34D; font-size: 11px;")
            rec_layout.addWidget(rec_lbl)
            layout.addWidget(rec_frame)

        # Footer Actions
        footer = QHBoxLayout()
        footer.setSpacing(10)

        # Open in Explorer / folder
        if ev_path and os.path.exists(ev_path):
            open_folder_btn = QPushButton("📁 Show in File Explorer")
            open_folder_btn.setCursor(QCursor(Qt.PointingHandCursor))
            open_folder_btn.setStyleSheet("""
                QPushButton {
                    background: #1E2330;
                    color: #94A3B8;
                    border: 1px solid #2D3748;
                    border-radius: 5px;
                    padding: 6px 14px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #2D3748;
                    color: #FFFFFF;
                }
            """)
            open_folder_btn.clicked.connect(self._open_file_in_explorer)
            footer.addWidget(open_folder_btn)

        footer.addStretch()

        # Resolve button directly in dialog
        status = str(alert_data.get("status", "Open")).lower()
        if status != "resolved":
            resolve_btn = QPushButton("✔ Resolve Incident")
            resolve_btn.setCursor(QCursor(Qt.PointingHandCursor))
            resolve_btn.setStyleSheet("""
                QPushButton {
                    background: #064E3B;
                    color: #6EE7B7;
                    border: 1px solid #059669;
                    border-radius: 5px;
                    padding: 6px 16px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #059669;
                    color: #FFFFFF;
                }
            """)
            resolve_btn.clicked.connect(self._resolve_incident)
            footer.addWidget(resolve_btn)

        dialog_close_btn = QPushButton("Close")
        dialog_close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        dialog_close_btn.setStyleSheet("""
            QPushButton {
                background: #1E2330;
                color: #CBD5E1;
                border: 1px solid #2D3748;
                border-radius: 5px;
                padding: 6px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #2D3748;
                color: #FFFFFF;
            }
        """)
        dialog_close_btn.clicked.connect(self.close)
        footer.addWidget(dialog_close_btn)

        layout.addLayout(footer)

    def _badge_style(self, sev: str) -> str:
        s = sev.lower()
        if s == "critical":
            return "background: #DC2626; color: #FFFFFF; border-radius: 4px; padding: 4px 10px; font-weight: bold;"
        elif s == "high":
            return "background: #EA580C; color: #FFFFFF; border-radius: 4px; padding: 4px 10px; font-weight: bold;"
        elif s == "medium":
            return "background: #D97706; color: #000000; border-radius: 4px; padding: 4px 10px; font-weight: bold;"
        return "background: #059669; color: #FFFFFF; border-radius: 4px; padding: 4px 10px; font-weight: bold;"

    def _open_file_in_explorer(self):
        ev_path = self.alert_data.get("evidence")
        if ev_path and os.path.exists(ev_path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(ev_path)}"')
            except Exception:
                pass

    def _resolve_incident(self):
        if self._db_id is not None:
            self.resolve_requested.emit(self._db_id)
        self.close()


class AlertCardWidget(QFrame):
    """Spacious, rich interactive alert card with non-clipping action buttons and distinct threat hierarchy."""

    status_changed = Signal(int, str)       # db_id, new_status
    view_snapshot_requested = Signal(dict)  # alert
    focus_camera_requested = Signal(str)    # camera_id

    def __init__(self, alert: dict[str, Any], parent=None):
        super().__init__(parent)
        self.alert = alert
        self._db_id = alert.get("db_id")
        self._severity = str(alert.get("severity", "Low")).lower()
        self._status = alert.get("status", "Open")

        self.setObjectName("AlertCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(132)
        self._setup_ui()
        self.update_style()

    def sizeHint(self) -> QSize:
        return QSize(330, 134)

    def _get_theme(self) -> dict[str, str]:
        if self._severity == "critical":
            return {
                "border": "#EF4444",
                "pill_bg": "#DC2626",
                "pill_text": "#FFFFFF",
                "icon": "🔥",
                "title_color": "#FCA5A5",
                "bg": "#1C1215",
                "chip_bg": "#2B161B",
                "chip_text": "#F87171",
            }
        elif self._severity == "high":
            return {
                "border": "#F97316",
                "pill_bg": "#EA580C",
                "pill_text": "#FFFFFF",
                "icon": "🚷",
                "title_color": "#FDBA74",
                "bg": "#1C1510",
                "chip_bg": "#2B1B14",
                "chip_text": "#FB923C",
            }
        elif self._severity == "medium":
            event = str(self.alert.get("event_type", "")).lower()
            icon = "⛑️" if "helmet" in event else ("🦺" if "vest" in event else "⚠️")
            return {
                "border": "#F59E0B",
                "pill_bg": "#D97706",
                "pill_text": "#000000",
                "icon": icon,
                "title_color": "#FCD34D",
                "bg": "#1B1710",
                "chip_bg": "#292113",
                "chip_text": "#FBBF24",
            }
        else:
            return {
                "border": "#10B981",
                "pill_bg": "#059669",
                "pill_text": "#FFFFFF",
                "icon": "🛡️",
                "title_color": "#6EE7B7",
                "bg": "#101814",
                "chip_bg": "#14241D",
                "chip_text": "#34D399",
            }

    def _setup_ui(self):
        theme = self._get_theme()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # Row 1: Severity Badge + Event Name + Timestamp
        # -------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.sev_badge = QLabel(f" {self.alert.get('severity', 'LOW').upper()} ")
        self.sev_badge.setFont(QFont("Arial", 8, QFont.Bold))
        self.sev_badge.setStyleSheet(f"""
            background: {theme['pill_bg']};
            color: {theme['pill_text']};
            border-radius: 3px;
            padding: 2px 6px;
            font-weight: bold;
        """)
        top_row.addWidget(self.sev_badge)

        event_name = str(self.alert.get("event_type", "Threat Detected")).replace("_", " ").title()
        self.title_lbl = QLabel(f"{theme['icon']} {event_name}")
        self.title_lbl.setFont(QFont("Arial", 10, QFont.Bold))
        self.title_lbl.setStyleSheet(f"color: {theme['title_color']};")
        top_row.addWidget(self.title_lbl)

        top_row.addStretch()

        time_str = self.alert.get("timestamp") or "--:--:--"
        self.time_lbl = QLabel(time_str)
        self.time_lbl.setFont(QFont("Arial", 8))
        self.time_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        top_row.addWidget(self.time_lbl)

        main_layout.addLayout(top_row)

        # -------------------------------------------------------------
        # Row 2: Location Chips (Camera, Zone, Confidence)
        # -------------------------------------------------------------
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        cam_name = self.alert.get("camera_name") or self.alert.get("camera_id") or "Camera"
        cam_chip = QLabel(f"📹 {cam_name}")
        cam_chip.setStyleSheet("""
            background: #202534;
            color: #CBD5E1;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 10px;
        """)
        meta_row.addWidget(cam_chip)

        zone_name = self.alert.get("zone") or "Global"
        zone_chip = QLabel(f"📍 {zone_name}")
        zone_chip.setStyleSheet("""
            background: #202534;
            color: #CBD5E1;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 10px;
        """)
        meta_row.addWidget(zone_chip)

        conf_val = float(self.alert.get("confidence", 0.0))
        if conf_val > 0:
            conf_chip = QLabel(f"{int(conf_val * 100)}%")
            conf_chip.setStyleSheet(f"""
                background: {theme['chip_bg']};
                color: {theme['chip_text']};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
            meta_row.addWidget(conf_chip)

        meta_row.addStretch()
        main_layout.addLayout(meta_row)

        # Recommendation line if exists
        rec = self.alert.get("recommendation")
        if rec:
            rec_lbl = QLabel(f"⚡ {rec}")
            rec_lbl.setStyleSheet("color: #FCD34D; font-size: 10px; background: rgba(0,0,0,0.22); border-radius: 3px; padding: 2px 6px;")
            main_layout.addWidget(rec_lbl)

        # -------------------------------------------------------------
        # Row 3: Status Indicator + High-Clickability Action Buttons
        # -------------------------------------------------------------
        bot_row = QHBoxLayout()
        bot_row.setSpacing(6)

        self.status_lbl = QLabel()
        self.status_lbl.setFont(QFont("Arial", 8, QFont.Bold))
        bot_row.addWidget(self.status_lbl)

        bot_row.addStretch()

        # Focus Camera Button
        cam_id = self.alert.get("camera_id")
        if cam_id:
            self.focus_btn = QPushButton("📹 Focus")
            self.focus_btn.setToolTip("Focus camera feed in grid")
            self.focus_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.focus_btn.setFixedHeight(24)
            self.focus_btn.setStyleSheet("""
                QPushButton {
                    background: #1A2130;
                    color: #93C5FD;
                    border: 1px solid #2B3A54;
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background: #2B3A54;
                    color: #FFFFFF;
                }
            """)
            self.focus_btn.clicked.connect(lambda: self.focus_camera_requested.emit(str(cam_id)))
            bot_row.addWidget(self.focus_btn)

        # Snapshot Button
        if self.alert.get("evidence"):
            self.view_btn = QPushButton("📷 View")
            self.view_btn.setToolTip("Inspect snapshot")
            self.view_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.view_btn.setFixedHeight(24)
            self.view_btn.setStyleSheet("""
                QPushButton {
                    background: #202534;
                    color: #E2E8F0;
                    border: 1px solid #33394D;
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background: #33394D;
                    color: #FFFFFF;
                }
            """)
            self.view_btn.clicked.connect(lambda: self.view_snapshot_requested.emit(self.alert))
            bot_row.addWidget(self.view_btn)

        # Acknowledge Button
        self.ack_btn = QPushButton("✓ Ack")
        self.ack_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ack_btn.setFixedHeight(24)
        self.ack_btn.setStyleSheet("""
            QPushButton {
                background: #3B200A;
                color: #FCD34D;
                border: 1px solid #B45309;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: #B45309;
                color: #000000;
            }
        """)
        self.ack_btn.clicked.connect(self._on_ack_clicked)
        bot_row.addWidget(self.ack_btn)

        # Resolve Button (Generous width, crisp click)
        self.res_btn = QPushButton("✔ Resolve")
        self.res_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.res_btn.setFixedHeight(24)
        self.res_btn.setStyleSheet("""
            QPushButton {
                background: #064E3B;
                color: #6EE7B7;
                border: 1px solid #059669;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
            }
        """)
        self.res_btn.clicked.connect(self._on_resolve_clicked)
        bot_row.addWidget(self.res_btn)

        main_layout.addLayout(bot_row)
        self._update_status_display()

    def _update_status_display(self):
        s = self._status.lower()
        if s == "acknowledged":
            self.status_lbl.setText("● ACK")
            self.status_lbl.setStyleSheet("color: #60A5FA; font-weight: bold;")
            if hasattr(self, "ack_btn"):
                self.ack_btn.setEnabled(False)
                self.ack_btn.setStyleSheet("background: #171B26; color: #475569; border: 1px solid #222634; border-radius: 4px; font-size: 10px;")
        elif s == "resolved":
            self.status_lbl.setText("✔ RESOLVED")
            self.status_lbl.setStyleSheet("color: #34D399; font-weight: bold;")
            if hasattr(self, "ack_btn"):
                self.ack_btn.setEnabled(False)
                self.ack_btn.setStyleSheet("background: #171B26; color: #475569; border: 1px solid #222634; border-radius: 4px; font-size: 10px;")
            if hasattr(self, "res_btn"):
                self.res_btn.setEnabled(False)
                self.res_btn.setStyleSheet("background: #171B26; color: #475569; border: 1px solid #222634; border-radius: 4px; font-size: 10px;")
        else:
            self.status_lbl.setText("● ACTIVE")
            self.status_lbl.setStyleSheet("color: #EF4444; font-weight: bold;")

    def set_status(self, new_status: str):
        self._status = new_status
        self.alert["status"] = new_status
        self._update_status_display()
        self.update_style()

    def _on_ack_clicked(self):
        self.set_status("Acknowledged")
        if self._db_id is not None:
            self.status_changed.emit(self._db_id, "Acknowledged")

    def _on_resolve_clicked(self):
        self.set_status("Resolved")
        if self._db_id is not None:
            self.status_changed.emit(self._db_id, "Resolved")

    def update_style(self):
        theme = self._get_theme()
        is_resolved = self._status.lower() == "resolved"
        border_col = "#2B3242" if is_resolved else theme["border"]
        bg_col = "#11141C" if is_resolved else theme["bg"]

        self.setStyleSheet(f"""
            QFrame#AlertCard {{
                background-color: {bg_col};
                border: 1px solid #202636;
                border-left: 5px solid {border_col};
                border-radius: 6px;
            }}
            QFrame#AlertCard:hover {{
                border-color: #384259;
                border-left-color: {border_col};
            }}
        """)


class AlertPanel(QWidget):
    """Modern Industrial Safety Alert Panel with live stream monitoring, interactive filters, search, and sound controls."""

    focus_camera_requested = Signal(str)   # camera_id
    sound_toggled = Signal(bool)           # enabled

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self._alerts: list[dict[str, Any]] = []
        self._card_widgets: list[AlertCardWidget] = []
        self._current_filter: str = "ALL"  # ALL, CRITICAL, HIGH, MEDIUM, RESOLVED
        self._search_text: str = ""
        self._sound_enabled: bool = True

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Panel Styling
        self.setStyleSheet("""
            AlertPanel {
                background-color: #0C0F17;
                border-left: 1px solid #1A202C;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 3px 1px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)

        # -------------------------------------------------------------
        # 1. Header Bar: Real-time Indicator + Title + Sound Toggle
        # -------------------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(6)

        title_icon = QLabel("🚨")
        title_icon.setFont(QFont("Arial", 12))
        header.addWidget(title_icon)

        title_text = QLabel("Live Threat Stream")
        title_text.setFont(QFont("Arial", 11, QFont.Bold))
        title_text.setStyleSheet("color: #F8FAFC;")
        header.addWidget(title_text)

        header.addStretch()

        # Sound Mute/Unmute Toggle
        self.sound_btn = QPushButton("🔊")
        self.sound_btn.setToolTip("Toggle alert audio chimes")
        self.sound_btn.setFixedSize(28, 26)
        self.sound_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sound_btn.setStyleSheet("""
            QPushButton {
                background: #171D2B;
                color: #CBD5E1;
                border: 1px solid #263248;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #263248;
                color: #FFFFFF;
            }
        """)
        self.sound_btn.clicked.connect(self._toggle_sound)
        header.addWidget(self.sound_btn)

        # Active badge
        self.total_badge = QLabel("0 Active")
        self.total_badge.setFont(QFont("Arial", 8, QFont.Bold))
        self.total_badge.setStyleSheet("""
            background: #171D2B;
            color: #94A3B8;
            border-radius: 10px;
            padding: 3px 8px;
        """)
        header.addWidget(self.total_badge)
        layout.addLayout(header)

        # -------------------------------------------------------------
        # 2. Metric Counters Strip
        # -------------------------------------------------------------
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: #111622;
                border: 1px solid #1E273A;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(6, 4, 6, 4)
        stats_layout.setSpacing(8)

        self.crit_stat = QLabel("🔴 Crit: 0")
        self.crit_stat.setFont(QFont("Arial", 8, QFont.Bold))
        self.crit_stat.setStyleSheet("color: #EF4444;")

        self.high_stat = QLabel("🟠 High: 0")
        self.high_stat.setFont(QFont("Arial", 8, QFont.Bold))
        self.high_stat.setStyleSheet("color: #F97316;")

        self.med_stat = QLabel("🟡 Med: 0")
        self.med_stat.setFont(QFont("Arial", 8, QFont.Bold))
        self.med_stat.setStyleSheet("color: #F59E0B;")

        self.res_stat = QLabel("🟢 Resolved: 0")
        self.res_stat.setFont(QFont("Arial", 8, QFont.Bold))
        self.res_stat.setStyleSheet("color: #10B981;")

        stats_layout.addWidget(self.crit_stat)
        stats_layout.addWidget(self.high_stat)
        stats_layout.addWidget(self.med_stat)
        stats_layout.addWidget(self.res_stat)
        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # -------------------------------------------------------------
        # 3. Filter Segment Tabs
        # -------------------------------------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(4)

        self.filter_buttons = {}
        filters = [
            ("ALL", "All"),
            ("CRITICAL", "🔥 Crit"),
            ("HIGH", "⚠️ High"),
            ("MEDIUM", "🟡 Med"),
            ("RESOLVED", "✔ Done"),
        ]
        for key, label in filters:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, k=key: self._set_filter(k))
            filter_layout.addWidget(btn)
            self.filter_buttons[key] = btn

        layout.addLayout(filter_layout)
        self._update_filter_button_styles()

        # -------------------------------------------------------------
        # 4. Search Filter Bar
        # -------------------------------------------------------------
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search camera, zone, threat...")
        self.search_input.setFixedHeight(26)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #111622;
                color: #E2E8F0;
                border: 1px solid #1E273A;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)

        clear_search_btn = QPushButton("✕")
        clear_search_btn.setFixedSize(26, 26)
        clear_search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_search_btn.setStyleSheet("""
            QPushButton {
                background: #171D2B;
                color: #94A3B8;
                border: 1px solid #1E273A;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #263248;
                color: #FFFFFF;
            }
        """)
        clear_search_btn.clicked.connect(lambda: self.search_input.clear())
        search_layout.addWidget(clear_search_btn)
        layout.addLayout(search_layout)

        # -------------------------------------------------------------
        # 5. Main Alerts List Widget
        # -------------------------------------------------------------
        self.list = QListWidget()
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list)

        # Empty State Placeholder
        self.empty_label = QLabel("No active safety breaches.\nAll camera zones secure.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #475569; font-size: 11px; padding: 25px 0;")
        layout.addWidget(self.empty_label)

        # -------------------------------------------------------------
        # 6. Selection Action Bar (Resolve / Ack selected alert)
        # -------------------------------------------------------------
        sel_action_frame = QFrame()
        sel_action_frame.setStyleSheet("background: #111622; border: 1px solid #1E273A; border-radius: 6px; padding: 4px;")
        sel_action_layout = QHBoxLayout(sel_action_frame)
        sel_action_layout.setContentsMargins(6, 4, 6, 4)
        sel_action_layout.setSpacing(6)

        self.sel_ack_btn = QPushButton("✓ Ack Selected")
        self.sel_ack_btn.setEnabled(False)
        self.sel_ack_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sel_ack_btn.setStyleSheet("""
            QPushButton {
                background: #2D1A08;
                color: #FCD34D;
                border: 1px solid #B45309;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #B45309;
                color: #000000;
            }
            QPushButton:disabled {
                background: #11141C;
                color: #475569;
                border-color: #1E273A;
            }
        """)
        self.sel_ack_btn.clicked.connect(self._acknowledge_selected)
        sel_action_layout.addWidget(self.sel_ack_btn)

        self.sel_res_btn = QPushButton("✔ Resolve Selected")
        self.sel_res_btn.setEnabled(False)
        self.sel_res_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sel_res_btn.setStyleSheet("""
            QPushButton {
                background: #064E3B;
                color: #6EE7B7;
                border: 1px solid #059669;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background: #11141C;
                color: #475569;
                border-color: #1E273A;
            }
        """)
        self.sel_res_btn.clicked.connect(self._resolve_selected)
        sel_action_layout.addWidget(self.sel_res_btn)

        layout.addWidget(sel_action_frame)

        # -------------------------------------------------------------
        # 7. Global Bulk Actions
        # -------------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.ack_all_btn = QPushButton("Ack All")
        self.ack_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ack_all_btn.setStyleSheet("""
            QPushButton {
                background: #171D2B;
                color: #CBD5E1;
                border: 1px solid #263248;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #263248;
                color: #FFFFFF;
            }
        """)
        self.ack_all_btn.clicked.connect(self._acknowledge_all)
        btn_layout.addWidget(self.ack_all_btn)

        self.res_all_btn = QPushButton("Resolve All")
        self.res_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.res_all_btn.setStyleSheet("""
            QPushButton {
                background: #0C382B;
                color: #6EE7B7;
                border: 1px solid #059669;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
            }
        """)
        self.res_all_btn.clicked.connect(self._resolve_all)
        btn_layout.addWidget(self.res_all_btn)

        self.clear_resolved_btn = QPushButton("Clear Resolved")
        self.clear_resolved_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.clear_resolved_btn.setStyleSheet("""
            QPushButton {
                background: #111622;
                color: #94A3B8;
                border: 1px solid #1E273A;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #1E273A;
                color: #E2E8F0;
            }
        """)
        self.clear_resolved_btn.clicked.connect(self._clear_resolved)
        btn_layout.addWidget(self.clear_resolved_btn)

        layout.addLayout(btn_layout)

    def _toggle_sound(self):
        self._sound_enabled = not self._sound_enabled
        if self._sound_enabled:
            self.sound_btn.setText("🔊")
            self.sound_btn.setStyleSheet("""
                QPushButton {
                    background: #171D2B;
                    color: #CBD5E1;
                    border: 1px solid #263248;
                    border-radius: 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #263248;
                    color: #FFFFFF;
                }
            """)
        else:
            self.sound_btn.setText("🔇")
            self.sound_btn.setStyleSheet("""
                QPushButton {
                    background: #3B1B1F;
                    color: #F87171;
                    border: 1px solid #7F1D1D;
                    border-radius: 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #7F1D1D;
                    color: #FFFFFF;
                }
            """)
        self.sound_toggled.emit(self._sound_enabled)

    def _set_filter(self, filter_key: str):
        self._current_filter = filter_key
        self._update_filter_button_styles()
        self._apply_filtering()

    def _update_filter_button_styles(self):
        for key, btn in self.filter_buttons.items():
            if key == self._current_filter:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #3B82F6;
                        color: #FFFFFF;
                        border: 1px solid #60A5FA;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 6px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #111622;
                        color: #94A3B8;
                        border: 1px solid #1E273A;
                        border-radius: 3px;
                        font-size: 10px;
                        padding: 2px 6px;
                    }
                    QPushButton:hover {
                        background: #171D2B;
                        color: #CBD5E1;
                    }
                """)

    def _on_search_text_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._apply_filtering()

    def _apply_filtering(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            card = self._card_widgets[i]
            alert = card.alert

            # Filter by severity/status
            sev = str(alert.get("severity", "")).lower()
            status = str(alert.get("status", "")).lower()

            matches_filter = True
            if self._current_filter == "CRITICAL" and sev != "critical":
                matches_filter = False
            elif self._current_filter == "HIGH" and sev != "high":
                matches_filter = False
            elif self._current_filter == "MEDIUM" and sev not in ("medium", "low"):
                matches_filter = False
            elif self._current_filter == "RESOLVED" and status != "resolved":
                matches_filter = False

            # Filter by search text
            matches_search = True
            if self._search_text:
                cam = str(alert.get("camera_name", "") or alert.get("camera_id", "")).lower()
                zone = str(alert.get("zone", "")).lower()
                evt = str(alert.get("event_type", "")).lower()
                if self._search_text not in cam and self._search_text not in zone and self._search_text not in evt:
                    matches_search = False

            item.setHidden(not (matches_filter and matches_search))

        visible_count = sum(1 for i in range(self.list.count()) if not self.list.item(i).isHidden())
        self.empty_label.setVisible(visible_count == 0)

    def add_alert(self, alert: dict[str, Any]) -> None:
        """Add a rich alert card to the list without vertical clipping."""
        self._alerts.insert(0, alert)

        item = QListWidgetItem()
        card = AlertCardWidget(alert)
        card.status_changed.connect(self._on_card_status_changed)
        card.view_snapshot_requested.connect(self._open_evidence_dialog)
        card.focus_camera_requested.connect(self.focus_camera_requested.emit)

        # Explicitly assign generous size hint so card contents are NEVER clipped
        item.setSizeHint(QSize(320, 140))

        self.list.insertItem(0, item)
        self.list.setItemWidget(item, card)

        self._card_widgets.insert(0, card)
        self._update_counters()
        self._apply_filtering()

    def _update_counters(self):
        crit = sum(1 for a in self._alerts if str(a.get("severity")).lower() == "critical" and a.get("status") != "Resolved")
        high = sum(1 for a in self._alerts if str(a.get("severity")).lower() == "high" and a.get("status") != "Resolved")
        med = sum(1 for a in self._alerts if str(a.get("severity")).lower() in ("medium", "low") and a.get("status") != "Resolved")
        res = sum(1 for a in self._alerts if a.get("status") == "Resolved")
        active = sum(1 for a in self._alerts if a.get("status") != "Resolved")

        self.crit_stat.setText(f"🔴 Crit: {crit}")
        self.high_stat.setText(f"🟠 High: {high}")
        self.med_stat.setText(f"🟡 Med: {med}")
        self.res_stat.setText(f"🟢 Res: {res}")

        if active > 0:
            self.total_badge.setText(f"{active} Active")
            self.total_badge.setStyleSheet("background: #7F1D1D; color: #FCA5A5; border-radius: 10px; padding: 3px 8px; font-weight: bold;")
        else:
            self.total_badge.setText("0 Active")
            self.total_badge.setStyleSheet("background: #171D2B; color: #94A3B8; border-radius: 10px; padding: 3px 8px;")

    def _on_selection_changed(self):
        row = self.list.currentRow()
        has_sel = (0 <= row < len(self._card_widgets))
        if has_sel:
            is_open = self._card_widgets[row].alert.get("status") == "Open"
            is_resolved = self._card_widgets[row].alert.get("status") == "Resolved"
            self.sel_ack_btn.setEnabled(is_open)
            self.sel_res_btn.setEnabled(not is_resolved)
        else:
            self.sel_ack_btn.setEnabled(False)
            self.sel_res_btn.setEnabled(False)

    def _acknowledge_selected(self):
        row = self.list.currentRow()
        if 0 <= row < len(self._card_widgets):
            self._card_widgets[row]._on_ack_clicked()
            self._on_selection_changed()

    def _resolve_selected(self):
        row = self.list.currentRow()
        if 0 <= row < len(self._card_widgets):
            self._card_widgets[row]._on_resolve_clicked()
            self._on_selection_changed()

    def _on_card_status_changed(self, db_id: int, new_status: str):
        try:
            from database import update_incident_status
            update_incident_status(db_id, new_status)
        except Exception as e:
            print(f"Error updating incident status in DB: {e}")
        self._update_counters()
        self._on_selection_changed()

    def _open_evidence_dialog(self, alert: dict[str, Any]):
        dlg = EvidencePreviewDialog(alert, self)
        dlg.resolve_requested.connect(self._resolve_by_db_id)
        dlg.exec()

    def _resolve_by_db_id(self, db_id: int):
        for card in self._card_widgets:
            if card.alert.get("db_id") == db_id:
                card._on_resolve_clicked()
                break

    def _on_item_double_clicked(self, item: QListWidgetItem):
        row = self.list.row(item)
        if 0 <= row < len(self._alerts):
            self._open_evidence_dialog(self._alerts[row])

    def _acknowledge_all(self):
        for card in self._card_widgets:
            if card.alert.get("status") == "Open":
                card.set_status("Acknowledged")
                db_id = card.alert.get("db_id")
                if db_id is not None:
                    try:
                        from database import update_incident_status
                        update_incident_status(db_id, "Acknowledged")
                    except Exception:
                        pass
        self._update_counters()
        self._on_selection_changed()

    def _resolve_all(self):
        for card in self._card_widgets:
            if card.alert.get("status") != "Resolved":
                card.set_status("Resolved")
                db_id = card.alert.get("db_id")
                if db_id is not None:
                    try:
                        from database import update_incident_status
                        update_incident_status(db_id, "Resolved")
                    except Exception:
                        pass
        self._update_counters()
        self._on_selection_changed()

    def _clear_resolved(self):
        indices_to_remove = []
        for i in range(len(self._card_widgets) - 1, -1, -1):
            if self._card_widgets[i].alert.get("status") == "Resolved":
                indices_to_remove.append(i)

        for i in indices_to_remove:
            self.list.takeItem(i)
            del self._card_widgets[i]
            del self._alerts[i]

        self._update_counters()
        self._on_selection_changed()
        self._apply_filtering()
