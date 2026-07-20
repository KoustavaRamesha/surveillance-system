from __future__ import annotations

from typing import List, Dict

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
        btn_layout.addWidget(self.ack_btn)
        btn_layout.addWidget(self.resolve_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def add_alert(self, alert: Dict[str, str]) -> None:
        text = f"[{alert.get('severity')}] {alert.get('camera_id')} - {alert.get('event_type')}"
        self.list.addItem(text)
