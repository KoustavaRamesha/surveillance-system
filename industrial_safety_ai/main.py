from __future__ import annotations

import os
import sys
from pathlib import Path

# Suppress OpenCV warnings from camera discovery before PySide/OpenCV load
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def ensure_project_dirs() -> None:
    # Ensure existing config.py created directories are present
    from config import MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR
    from database import create_incidents_table
    from core.camera_db import create_cameras_table

    for d in (MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)

    create_incidents_table()
    create_cameras_table()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Industrial Safety Monitor")
    ensure_project_dirs()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
