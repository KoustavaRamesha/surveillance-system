from __future__ import annotations

import json
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QPen, QPixmap, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QMessageBox,
)


class DrawableLabel(QLabel):
    """Interactive canvas that allows drawing and previewing a rectangular zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.final_rect = QRect()
        self.setCursor(Qt.CrossCursor)
        self.original_pixmap = None

    def setPixmap(self, pixmap: QPixmap) -> None:
        super().setPixmap(pixmap)
        self.original_pixmap = pixmap

    def set_initial_rect(self, rect: QRect) -> None:
        self.final_rect = rect
        self.update()

    def clear_rect(self) -> None:
        self.final_rect = QRect()
        self.drawing = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.LeftButton:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_point = event.position().toPoint()
            self.final_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.original_pixmap:
            return

        painter = QPainter(self)
        # Smooth rendering
        painter.setRenderHint(QPainter.Antialiasing)

        # Active drawing: bright orange dashed line
        pen_draw = QPen(QColor(249, 115, 22, 230), 2, Qt.DashLine)
        # Final set zone: high-visibility red-orange with solid border
        pen_final = QPen(QColor(239, 68, 68, 240), 2, Qt.SolidLine)

        if self.drawing:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(pen_draw)
            painter.drawRect(rect)
            painter.fillRect(rect, QColor(249, 115, 22, 50))
        elif not self.final_rect.isNull() and self.final_rect.width() > 5 and self.final_rect.height() > 5:
            painter.setPen(pen_final)
            painter.drawRect(self.final_rect)
            # Semi-transparent fill
            painter.fillRect(self.final_rect, QColor(239, 68, 68, 55))

            # Banner label above rect
            tag = "RESTRICTED AREA"
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(239, 68, 68, 220))
            tag_rect = QRect(self.final_rect.left(), max(0, self.final_rect.top() - 20), 120, 20)
            painter.drawRoundedRect(tag_rect, 3, 3)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(tag_rect, Qt.AlignCenter, tag)


class ZoneDialog(QDialog):
    """Dialog to draw, name, edit, or clear restricted zones for a specific camera."""

    def __init__(self, camera_id: str, pixmap: QPixmap, current_zone: dict | None = None, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.current_zone = current_zone or {}
        self.is_cleared = False

        self.setWindowTitle(f"Draw Restricted Zone — {camera_id}")
        self.setModal(True)
        self.resize(840, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #121316;
                color: #E2E8F0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel {
                color: #CBD5E1;
            }
            QLineEdit {
                background: #18181B;
                color: #F8FAFC;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #F97316;
            }
            QPushButton {
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header Info Banner
        header = QHBoxLayout()
        title_lbl = QLabel(f"📍 Configure Zone for <b>{camera_id}</b>")
        title_lbl.setFont(QFont("Arial", 12))
        title_lbl.setTextFormat(Qt.RichText)
        header.addWidget(title_lbl)
        header.addStretch()

        help_lbl = QLabel("Click & drag on the feed below to define the zone")
        help_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header.addWidget(help_lbl)
        layout.addLayout(header)

        # Interactive Canvas
        self.image_label = DrawableLabel()

        # Scale pixmap reasonably to fit dialog without distorting aspect ratio
        target_max_w = 800
        target_max_h = 520
        if pixmap.width() > target_max_w or pixmap.height() > target_max_h:
            pixmap = pixmap.scaled(target_max_w, target_max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        self.image_label.setStyleSheet("border: 1px solid #27272A; border-radius: 6px;")
        self.pixmap_size = pixmap.size()

        # Load existing zone if configured for this camera
        if self.current_zone and "x1" in self.current_zone and "x2" in self.current_zone:
            try:
                ref_w = max(1, self.current_zone.get("ref_width", self.pixmap_size.width()))
                ref_h = max(1, self.current_zone.get("ref_height", self.pixmap_size.height()))
                rx = self.pixmap_size.width() / ref_w
                ry = self.pixmap_size.height() / ref_h

                x1 = int(self.current_zone["x1"] * rx)
                y1 = int(self.current_zone["y1"] * ry)
                x2 = int(self.current_zone["x2"] * rx)
                y2 = int(self.current_zone["y2"] * ry)
                self.image_label.set_initial_rect(QRect(QPoint(x1, y1), QPoint(x2, y2)).normalized())
            except Exception:
                pass

        canvas_frame = QFrame()
        canvas_layout = QHBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        layout.addWidget(canvas_frame)

        # Zone Name & Controls Row
        name_row = QHBoxLayout()
        name_row.setSpacing(10)

        name_lbl = QLabel("Zone Name:")
        name_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        name_row.addWidget(name_lbl)

        default_name = self.current_zone.get("name") if self.current_zone else f"Restricted Area ({camera_id})"
        self.name_input = QLineEdit(default_name or f"Restricted Area ({camera_id})")
        self.name_input.setPlaceholderText("e.g. Danger Zone, Forklift Corridor, No-Entry Bay")
        name_row.addWidget(self.name_input, 1)

        clear_btn = QPushButton("🗑️ Clear Zone")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #27272A;
                color: #EF4444;
                border: 1px solid #3F3F46;
            }
            QPushButton:hover {
                background: #3F1D1D;
                border-color: #EF4444;
                color: #FFFFFF;
            }
        """)
        clear_btn.clicked.connect(self._on_clear_clicked)
        name_row.addWidget(clear_btn)

        layout.addLayout(name_row)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        self.status_lbl = QLabel("Draw a box by clicking and dragging on the camera snapshot above.")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        btn_bar.addWidget(self.status_lbl)
        btn_bar.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #18181B;
                color: #A1A1AA;
                border: 1px solid #27272A;
            }
            QPushButton:hover {
                background: #27272A;
                color: #FFFFFF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Zone")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #EA580C;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background: #F97316;
            }
        """)
        save_btn.clicked.connect(self._on_save_clicked)
        btn_bar.addWidget(save_btn)

        layout.addLayout(btn_bar)

    def _on_clear_clicked(self) -> None:
        self.image_label.clear_rect()
        self.is_cleared = True
        self.status_lbl.setText("Zone cleared. Click 'Save Zone' to remove the restricted area for this camera.")

    def _on_save_clicked(self) -> None:
        rect = self.image_label.final_rect
        if self.is_cleared or rect.isNull() or rect.width() < 10 or rect.height() < 10:
            # Confirm clearing
            if self.is_cleared or (self.current_zone and rect.isNull()):
                self.is_cleared = True
                self.accept()
                return
            else:
                QMessageBox.warning(self, "No Zone Drawn", "Please click and drag on the camera feed to draw a restricted area, or click Cancel.")
                return

        self.is_cleared = False
        self.accept()

    def get_zone_data(self) -> dict | None:
        if self.is_cleared:
            return None

        rect = self.image_label.final_rect
        if rect.isNull() or rect.width() < 10 or rect.height() < 10:
            return None

        zone_name = self.name_input.text().strip() or f"Restricted Area ({self.camera_id})"

        return {
            "x1": rect.left(),
            "y1": rect.top(),
            "x2": rect.right(),
            "y2": rect.bottom(),
            "ref_width": self.pixmap_size.width(),
            "ref_height": self.pixmap_size.height(),
            "name": zone_name,
        }
