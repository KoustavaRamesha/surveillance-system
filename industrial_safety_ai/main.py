from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def ensure_project_dirs() -> None:
    # Ensure existing config.py created directories are present
    from config import MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR

    for d in (MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Industrial Safety Monitor")
    ensure_project_dirs()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
