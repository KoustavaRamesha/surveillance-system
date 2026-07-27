from __future__ import annotations

from typing import Optional

import cv2
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CameraTile(QWidget):
    double_clicked = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview = QLabel("No feed")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(320, 240)

        self.info = QLabel("")

        layout = QVBoxLayout()
        layout.addWidget(self.preview)
        layout.addWidget(self.info)
        self.setLayout(layout)

        # For visual alerts
        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(self._clear_alert)

    def set_alert_state(self, active: bool, duration_ms: int = 3000) -> None:
        if active:
            self.setStyleSheet("CameraTile { border: 4px solid red; background-color: rgba(255,0,0,30); }")
            self._alert_timer.start(duration_ms)
        else:
            self._clear_alert()

    def _clear_alert(self) -> None:
        self.setStyleSheet("")

    def update_info(self, text: str) -> None:
        self.info.setText(text)

    def show_frame(self, frame) -> None:
        # Convert BGR (OpenCV) frame to RGB QImage
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(self.preview.width(), self.preview.height(), Qt.KeepAspectRatio)
            self.preview.setPixmap(pix)
        except Exception:
            # Fallback: show text
            self.preview.setText("Unable to display frame")

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
