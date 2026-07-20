from __future__ import annotations

from typing import Optional

import cv2
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.camera_db import add_camera


class CameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Camera")

        self.camera_id = QLineEdit()
        self.name = QLineEdit()
        self.location = QLineEdit()
        self.source_type = QComboBox()
        self.source_type.addItems(["USB", "File", "RTSP", "HTTP"])
        self.source = QLineEdit()
        self.username = QLineEdit()
        self.device_index = QSpinBox()
        self.device_index.setMinimum(0)

        self.enabled = QCheckBox()
        self.enabled.setChecked(True)
        self.analytics_enabled = QCheckBox()

        form = QFormLayout()
        form.addRow("Camera ID", self.camera_id)
        form.addRow("Name", self.name)
        form.addRow("Location", self.location)
        form.addRow("Source Type", self.source_type)
        form.addRow("Source (path or URL)", self.source)
        form.addRow("Device index (USB)", self.device_index)
        form.addRow("Username", self.username)
        form.addRow("Enabled", self.enabled)
        form.addRow("Analytics enabled", self.analytics_enabled)

        self.test_btn = QPushButton("Test Connection")
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")

        self.test_btn.clicked.connect(self.test_connection)
        self.save_btn.clicked.connect(self.save)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def test_connection(self) -> None:
        source_text = self.source.text().strip()
        source_type = self.source_type.currentText()
        cap = None
        try:
            if source_type == "USB":
                index = int(self.device_index.value())
                cap = cv2.VideoCapture(index)
            else:
                cap = cv2.VideoCapture(source_text)
            if not cap or not cap.isOpened():
                QMessageBox.warning(self, "Test Result", "Unable to open the specified source.")
                return
            ret, frame = cap.read()
            if not ret:
                QMessageBox.warning(self, "Test Result", "No frame received from the source.")
                return
            h, w = frame.shape[:2]
            QMessageBox.information(self, "Test Result", f"Connection OK — {w}x{h}")
        except Exception as exc:
            QMessageBox.critical(self, "Test Result", f"Test failed: {exc}")
        finally:
            if cap is not None and cap.isOpened():
                cap.release()

    def save(self) -> None:
        camera = {
            "camera_id": self.camera_id.text().strip() or f"CAM-{int(__import__('time').time())}",
            "name": self.name.text().strip(),
            "location": self.location.text().strip(),
            "source_type": self.source_type.currentText(),
            "source": self.source.text().strip() or str(self.device_index.value()),
            "username": self.username.text().strip(),
            "enabled": bool(self.enabled.isChecked()),
            "analytics_enabled": bool(self.analytics_enabled.isChecked()),
            "recording_enabled": False,
            "expected_resolution": None,
            "expected_fps": None,
        }
        try:
            add_camera(camera)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Unable to save camera: {exc}")
