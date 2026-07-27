import json
from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QPixmap, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QMessageBox
)

class DrawableLabel(QLabel):
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
        pen = QPen(QColor(255, 0, 0, 200), 3, Qt.SolidLine)
        painter.setPen(pen)

        if self.drawing:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)
        elif not self.final_rect.isNull():
            painter.drawRect(self.final_rect)
            
            # Draw semi-transparent fill
            painter.fillRect(self.final_rect, QColor(255, 0, 0, 50))


class ZoneDialog(QDialog):
    def __init__(self, camera_id: str, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.setWindowTitle(f"Draw Restricted Zone: {camera_id}")
        self.setModal(True)

        layout = QVBoxLayout(self)

        info_label = QLabel("Click and drag to draw a restricted area. Any person detected inside will trigger a critical alert.")
        layout.addWidget(info_label)

        self.image_label = DrawableLabel()
        
        # Scale pixmap to fit reasonably on screen if it's too large
        if pixmap.width() > 800 or pixmap.height() > 600:
            pixmap = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        layout.addWidget(self.image_label)
        
        self.pixmap_size = pixmap.size()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_zone_data(self) -> dict | None:
        rect = self.image_label.final_rect
        if rect.isNull() or rect.width() < 10 or rect.height() < 10:
            return None

        return {
            "x1": rect.left(),
            "y1": rect.top(),
            "x2": rect.right(),
            "y2": rect.bottom(),
            "ref_width": self.pixmap_size.width(),
            "ref_height": self.pixmap_size.height(),
            "name": "Restricted Zone"
        }
