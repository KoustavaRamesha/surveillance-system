from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from startup_optimizer import run_startup_sequence, set_performance_hints
from ui.main_window import MainWindow


def main() -> int:
    """Main entry point with optimized startup."""
    # Ensure process attaches to interactive user desktop if run from sandbox/subshell
    if sys.platform == "win32":
        try:
            import ctypes
            hdesk = ctypes.windll.user32.OpenDesktopA(b"Default", 0, False, 0x01FF)
            if hdesk:
                ctypes.windll.user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    # Set performance hints before creating QApplication
    set_performance_hints()

    app = QApplication(sys.argv)
    app.setApplicationName("Industrial Safety Monitor")

    # Run startup sequence with splash screen
    success, model_path = run_startup_sequence()

    if not success:
        QMessageBox.critical(
            None,
            "Startup Error",
            "Failed to initialize the application. Please check the console logs.",
        )
        return 1

    # Create and show main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())