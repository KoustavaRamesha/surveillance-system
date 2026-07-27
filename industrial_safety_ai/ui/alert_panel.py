from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout


class AlertPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Active Alerts"))
        self.list = QListWidget()
        layout.addWidget(self.list)

        btn_layout = QHBoxLayout()
        self.ack_btn = QPushButton("Acknowledge")
        self.resolve_btn = QPushButton("Resolve")
        self.ack_btn.clicked.connect(self._acknowledge_selected)
        self.resolve_btn.clicked.connect(self._resolve_selected)
        btn_layout.addWidget(self.ack_btn)
        btn_layout.addWidget(self.resolve_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self._alerts: list[dict] = []

    def add_alert(self, alert: dict[str, str]) -> None:
        text = f"[{alert.get('severity')}] {alert.get('camera_id')} - {alert.get('event_type')}"
        self.list.addItem(text)
        self._alerts.append(alert)

    def _acknowledge_selected(self) -> None:
        row = self.list.currentRow()
        if row < 0 or row >= len(self._alerts):
            return
        db_id = self._alerts[row].get("db_id")
        if db_id is not None:
            from database import update_incident_status
            update_incident_status(db_id, "Acknowledged")
            self.list.item(row).setText(self.list.item(row).text() + " [ACK]")

    def _resolve_selected(self) -> None:
        row = self.list.currentRow()
        if row < 0 or row >= len(self._alerts):
            return
        db_id = self._alerts[row].get("db_id")
        if db_id is not None:
            from database import update_incident_status
            update_incident_status(db_id, "Resolved")
            self.list.item(row).setText(self.list.item(row).text() + " [RESOLVED]")
