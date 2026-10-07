"""Enhanced alert panel with animations, clear messaging, and better visual hierarchy."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QProgressBar,
    QMessageBox,
)

from rules import severity_for_event, recommendation_for_event


class AlertItemWidget(QFrame):
    """Single alert item with severity-coded styling, message, and action buttons."""

    acknowledge_clicked = Signal(int)  # incident_id
    resolve_clicked = Signal(int)  # incident_id

    SEVERITY_COLORS = {
        "Critical": "#ff4444",  # bright red
        "High": "#ff8c00",      # orange
        "Medium": "#ffaa00",    # amber
        "Low": "#88dd00",       # lime green
    }

    SEVERITY_ICONS = {
        "Critical": "🚨",
        "High": "⚠️",
        "Medium": "⚡",
        "Low": "ℹ️",
    }

    def __init__(self, incident_dict: dict, parent=None):
        super().__init__(parent)
        self.incident_id = incident_dict.get("id")
        self.severity = incident_dict.get("severity", "Medium")
        self.event_type = incident_dict.get("event_type", "unknown")
        self.zone = incident_dict.get("zone", "Unknown Zone")
        self.confidence = incident_dict.get("confidence", 0.0)
        self.timestamp = incident_dict.get("timestamp", "")
        self.recommendation = incident_dict.get("recommendation", "")
        self.status = incident_dict.get("status", "Open")

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet(self._get_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: icon + event + timestamp + status badge
        header_layout = QHBoxLayout()
        icon_label = QLabel(self.SEVERITY_ICONS.get(self.severity, "❓"))
        icon_label.setFont(QFont("Arial", 16))
        header_layout.addWidget(icon_label)

        event_label = QLabel(self._format_event_title())
        event_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(event_label)

        time_label = QLabel(self.timestamp.split()[-1] if self.timestamp else "")  # HH:MM:SS
        time_label.setFont(QFont("Courier", 9))
        time_label.setStyleSheet("color: #888;")
        header_layout.addWidget(time_label)

        status_label = QLabel(f"[{self.status}]")
        status_font = QFont("Arial", 9, QFont.Bold)
        status_label.setFont(status_font)
        status_label.setStyleSheet(f"color: {self._get_status_color()};")
        header_layout.addStretch()
        header_layout.addWidget(status_label)

        layout.addLayout(header_layout)

        # Zone + confidence bar
        zone_layout = QHBoxLayout()
        zone_label = QLabel(f"Zone: {self.zone}")
        zone_label.setFont(QFont("Arial", 9))
        zone_label.setStyleSheet("color: #555;")
        zone_layout.addWidget(zone_label)

        conf_bar = QProgressBar()
        conf_bar.setValue(int(self.confidence * 100))
        conf_bar.setMaximumHeight(8)
        conf_bar.setMaximumWidth(80)
        conf_bar.setStyleSheet(self._get_progress_stylesheet())
        zone_layout.addStretch()
        zone_layout.addWidget(QLabel("Confidence:"))
        zone_layout.addWidget(conf_bar)

        layout.addLayout(zone_layout)

        # Recommendation (if available)
        if self.recommendation:
            rec_label = QLabel(f"✓ {self.recommendation}")
            rec_label.setFont(QFont("Arial", 9))
            rec_label.setStyleSheet(f"color: {self.SEVERITY_COLORS[self.severity]}; font-weight: bold;")
            rec_label.setWordWrap(True)
            layout.addWidget(rec_label)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.status != "Resolved":
            if self.status == "Open":
                ack_btn = QPushButton("Acknowledge")
                ack_btn.setMaximumWidth(100)
                ack_btn.setStyleSheet(self._get_button_stylesheet("#0066cc"))
                ack_btn.clicked.connect(lambda: self.acknowledge_clicked.emit(self.incident_id))
                button_layout.addWidget(ack_btn)

            resolve_btn = QPushButton("Resolve")
            resolve_btn.setMaximumWidth(80)
            resolve_btn.setStyleSheet(self._get_button_stylesheet("#00aa00"))
            resolve_btn.clicked.connect(lambda: self.resolve_clicked.emit(self.incident_id))
            button_layout.addWidget(resolve_btn)

        layout.addLayout(button_layout)

    def _format_event_title(self) -> str:
        """Format event type to human-readable title."""
        words = self.event_type.replace("_", " ").split()
        return " ".join(w.capitalize() for w in words)

    def _get_stylesheet(self) -> str:
        """Return stylesheet with severity-based border color."""
        color = self.SEVERITY_COLORS.get(self.severity, "#cccccc")
        return f"""
            AlertItemWidget {{
                border-left: 4px solid {color};
                border-radius: 4px;
                background-color: #f9f9f9;
                margin-bottom: 4px;
            }}
            AlertItemWidget:hover {{
                background-color: #efefef;
            }}
        """

    def _get_status_color(self) -> str:
        """Return color for status badge."""
        status_map = {
            "Open": "#ff4444",
            "Acknowledged": "#ffaa00",
            "Resolved": "#00aa00",
        }
        return status_map.get(self.status, "#888888")

    def _get_button_stylesheet(self, color: str) -> str:
        """Return stylesheet for action buttons."""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color)};
            }}
        """

    @staticmethod
    def _lighten_color(color_hex: str) -> str:
        """Lighten a hex color by 20%."""
        try:
            c = QColor(color_hex)
            h, s, v, a = c.getHsv()
            v = min(int(v * 1.15), 255)
            c.setHsv(h, max(int(s * 0.9), 0), v, a)
            return c.name()
        except Exception:
            return color_hex

    @staticmethod
    def _darken_color(color_hex: str) -> str:
        """Darken a hex color by 20%."""
        try:
            c = QColor(color_hex)
            h, s, v, a = c.getHsv()
            v = int(v * 0.85)
            c.setHsv(h, min(int(s * 1.1), 255), v, a)
            return c.name()
        except Exception:
            return color_hex

    def _get_progress_stylesheet(self) -> str:
        """Return stylesheet for confidence progress bar."""
        color = self.SEVERITY_COLORS.get(self.severity, "#0066cc")
        return f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """


class EnhancedAlertPanel(QWidget):
    """Main alert panel with real-time incident list, animations, and summary stats."""

    acknowledge_incident = Signal(int)  # incident_id
    resolve_incident = Signal(int)  # incident_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.incident_widgets: dict[int, AlertItemWidget] = {}
        self.last_alert_time: Optional[datetime] = None

        self.setWindowTitle("Active Alerts")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Summary bar (open/acknowledged/resolved counts)
        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(8, 8, 8, 8)

        self.open_label = QLabel("Open: 0")
        self.open_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.open_label.setStyleSheet("color: #ff4444;")
        summary_layout.addWidget(self.open_label)

        self.ack_label = QLabel("Acked: 0")
        self.ack_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.ack_label.setStyleSheet("color: #ffaa00;")
        summary_layout.addWidget(self.ack_label)

        self.resolved_label = QLabel("Resolved: 0")
        self.resolved_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.resolved_label.setStyleSheet("color: #00aa00;")
        summary_layout.addWidget(self.resolved_label)

        summary_layout.addStretch()
        summary_frame = QFrame()
        summary_frame.setLayout(summary_layout)
        summary_frame.setStyleSheet("background-color: #f0f0f0; border-bottom: 1px solid #ddd;")
        layout.addWidget(summary_frame)

        # Scrollable alert list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: white; }")

        self.alerts_container = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_container)
        self.alerts_layout.setContentsMargins(4, 4, 4, 4)
        self.alerts_layout.setSpacing(2)
        self.alerts_layout.addStretch()

        scroll_area.setWidget(self.alerts_container)
        layout.addWidget(scroll_area)

        # Idle message
        self.idle_label = QLabel("No active incidents")
        self.idle_label.setAlignment(Qt.AlignCenter)
        self.idle_label.setFont(QFont("Arial", 10))
        self.idle_label.setStyleSheet("color: #888; padding: 20px;")
        self.alerts_layout.insertWidget(0, self.idle_label)

    def add_incident(self, incident_dict: dict) -> None:
        """Add or update an incident in the panel with animation."""
        incident_id = incident_dict.get("id")
        if not incident_id:
            return

        # Remove existing widget if present
        if incident_id in self.incident_widgets:
            old_widget = self.incident_widgets.pop(incident_id)
            self.alerts_layout.removeWidget(old_widget)
            old_widget.deleteLater()

        # Create new alert item
        alert_item = AlertItemWidget(incident_dict)
        alert_item.acknowledge_clicked.connect(self.acknowledge_incident.emit)
        alert_item.resolve_clicked.connect(self.resolve_incident.emit)

        # Insert at top of list (before stretch)
        self.alerts_layout.insertWidget(1, alert_item)
        self.incident_widgets[incident_id] = alert_item

        # Animate in
        self._animate_item_in(alert_item)

        # Update summary
        self._update_summary()

        # Hide idle message
        self.idle_label.hide()

    def update_incident_status(self, incident_id: int, status: str) -> None:
        """Update the status of an incident widget."""
        if incident_id not in self.incident_widgets:
            return

        widget = self.incident_widgets[incident_id]
        widget.status = status
        # Update label styling
        widget.setStyleSheet(widget._get_stylesheet())
        self._update_summary()

    def _animate_item_in(self, widget: AlertItemWidget) -> None:
        """Animate alert item in from the top."""
        widget.setMaximumHeight(0)
        widget.setVisible(False)

        def start_animation():
            widget.setVisible(True)
            anim = QPropertyAnimation(widget, b"minimumHeight")
            anim.setDuration(300)
            anim.setStartValue(0)
            anim.setEndValue(120)  # approximate height
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            widget._animation = anim

        # Schedule animation start
        QTimer.singleShot(50, start_animation)

    def _update_summary(self) -> None:
        """Update the summary bar with current incident counts."""
        open_count = sum(1 for w in self.incident_widgets.values() if w.status == "Open")
        ack_count = sum(1 for w in self.incident_widgets.values() if w.status == "Acknowledged")
        resolved_count = sum(1 for w in self.incident_widgets.values() if w.status == "Resolved")

        self.open_label.setText(f"Open: {open_count}")
        self.ack_label.setText(f"Acked: {ack_count}")
        self.resolved_label.setText(f"Resolved: {resolved_count}")

        # Show/hide idle message
        if not self.incident_widgets:
            self.idle_label.show()
        else:
            self.idle_label.hide()

    def clear_all(self) -> None:
        """Clear all alerts from the panel."""
        for widget in self.incident_widgets.values():
            self.alerts_layout.removeWidget(widget)
            widget.deleteLater()
        self.incident_widgets.clear()
        self._update_summary()
        self.idle_label.show()