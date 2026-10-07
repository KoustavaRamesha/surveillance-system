"""
Standalone demo of the enhanced alert panel.
Shows what the new dashboard looks like with sample incidents.

Run with: python demo_enhanced_dashboard.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from ui.enhanced_alert_panel import EnhancedAlertPanel


class DemoDashboard(QMainWindow):
    """Demo window showing the enhanced alert panel with sample incidents."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Safety Dashboard — Demo")
        self.setGeometry(100, 100, 900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Title
        title = QLabel("Industrial Safety Surveillance Dashboard")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #333; padding: 10px;")
        layout.addWidget(title)

        # Alert panel
        self.alert_panel = EnhancedAlertPanel()
        self.alert_panel.acknowledge_incident.connect(self._on_acknowledge)
        self.alert_panel.resolve_incident.connect(self._on_resolve)
        layout.addWidget(self.alert_panel)

        # Control buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(8, 8, 8, 8)

        btn_add_fire = QPushButton("Add Fire Alert (Critical)")
        btn_add_fire.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold; padding: 8px;")
        btn_add_fire.clicked.connect(self._add_fire_incident)
        button_layout.addWidget(btn_add_fire)

        btn_add_intrusion = QPushButton("Add Intrusion Alert (High)")
        btn_add_intrusion.setStyleSheet("background-color: #ff8c00; color: white; font-weight: bold; padding: 8px;")
        btn_add_intrusion.clicked.connect(self._add_intrusion_incident)
        button_layout.addWidget(btn_add_intrusion)

        btn_add_helmet = QPushButton("Add No-Helmet Alert (Medium)")
        btn_add_helmet.setStyleSheet("background-color: #ffaa00; color: white; font-weight: bold; padding: 8px;")
        btn_add_helmet.clicked.connect(self._add_helmet_incident)
        button_layout.addWidget(btn_add_helmet)

        btn_add_vest = QPushButton("Add No-Vest Alert (Low)")
        btn_add_vest.setStyleSheet("background-color: #88dd00; color: black; font-weight: bold; padding: 8px;")
        btn_add_vest.clicked.connect(self._add_vest_incident)
        button_layout.addWidget(btn_add_vest)

        btn_clear = QPushButton("Clear All Alerts")
        btn_clear.setStyleSheet("background-color: #666; color: white; font-weight: bold; padding: 8px;")
        btn_clear.clicked.connect(self.alert_panel.clear_all)
        button_layout.addWidget(btn_clear)

        info_label = QLabel(
            "Demo Instructions:\n"
            "1. Click the buttons above to add sample incidents\n"
            "2. Watch the alerts animate into the panel\n"
            "3. Click 'Acknowledge' or 'Resolve' to see status changes\n"
            "4. Notice the summary bar updates in real-time\n"
            "5. Hover over alerts to see the hover effect\n"
            "6. Check the confidence bars and recommendations"
        )
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ddd; border-radius: 4px;")
        info_label.setWordWrap(True)
        button_layout.addWidget(info_label)

        buttons_frame = QWidget()
        buttons_frame.setLayout(button_layout)
        buttons_frame.setStyleSheet("background-color: #f9f9f9; border-top: 1px solid #ddd;")
        layout.addWidget(buttons_frame)

        self.incident_counter = 0
        self.demo_incidents = {}

    def _get_timestamp(self) -> str:
        """Get current timestamp formatted."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _add_fire_incident(self):
        """Add a fire detection incident."""
        self.incident_counter += 1
        incident_id = self.incident_counter

        incident = {
            "id": incident_id,
            "event_type": "fire",
            "severity": "Critical",
            "zone": "Production Floor A",
            "confidence": 0.98,
            "timestamp": self._get_timestamp(),
            "recommendation": "Evacuate immediately, call emergency services",
            "status": "Open",
        }
        self.demo_incidents[incident_id] = incident
        self.alert_panel.add_incident(incident)

    def _add_intrusion_incident(self):
        """Add a restricted area intrusion incident."""
        self.incident_counter += 1
        incident_id = self.incident_counter

        incident = {
            "id": incident_id,
            "event_type": "restricted_area_intrusion",
            "severity": "High",
            "zone": "Server Room (Restricted)",
            "confidence": 0.87,
            "timestamp": self._get_timestamp(),
            "recommendation": "Alert security, review access logs, check for data breaches",
            "status": "Open",
        }
        self.demo_incidents[incident_id] = incident
        self.alert_panel.add_incident(incident)

    def _add_helmet_incident(self):
        """Add a no-helmet detection incident."""
        self.incident_counter += 1
        incident_id = self.incident_counter

        incident = {
            "id": incident_id,
            "event_type": "no_helmet",
            "severity": "Medium",
            "zone": "Assembly Line B",
            "confidence": 0.76,
            "timestamp": self._get_timestamp(),
            "recommendation": "Stop work, provide PPE, conduct safety briefing",
            "status": "Open",
        }
        self.demo_incidents[incident_id] = incident
        self.alert_panel.add_incident(incident)

    def _add_vest_incident(self):
        """Add a no-safety-vest detection incident."""
        self.incident_counter += 1
        incident_id = self.incident_counter

        incident = {
            "id": incident_id,
            "event_type": "no_vest",
            "severity": "Low",
            "zone": "Warehouse Loading Dock",
            "confidence": 0.62,
            "timestamp": self._get_timestamp(),
            "recommendation": "Issue safety vest, remind of PPE policy",
            "status": "Open",
        }
        self.demo_incidents[incident_id] = incident
        self.alert_panel.add_incident(incident)

    def _on_acknowledge(self, incident_id: int):
        """Handle acknowledge button click."""
        if incident_id in self.demo_incidents:
            self.demo_incidents[incident_id]["status"] = "Acknowledged"
            self.alert_panel.update_incident_status(incident_id, "Acknowledged")

    def _on_resolve(self, incident_id: int):
        """Handle resolve button click."""
        if incident_id in self.demo_incidents:
            self.demo_incidents[incident_id]["status"] = "Resolved"
            self.alert_panel.update_incident_status(incident_id, "Resolved")


def main():
    """Run the demo."""
    app = QApplication(sys.argv)

    # Set application-wide stylesheet for modern look
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow {
            background-color: #ffffff;
        }
        QLabel {
            color: #333;
        }
        QPushButton {
            border-radius: 4px;
            border: none;
        }
        QPushButton:hover {
            opacity: 0.9;
        }
    """)

    demo = DemoDashboard()
    demo.show()

    # Auto-populate some sample incidents on start
    QTimer.singleShot(500, demo._add_fire_incident)
    QTimer.singleShot(1000, demo._add_intrusion_incident)
    QTimer.singleShot(1500, demo._add_helmet_incident)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()