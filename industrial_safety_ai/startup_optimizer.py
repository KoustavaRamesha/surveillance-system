"""Startup optimization utilities for faster app initialization."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt, QTimer

from config import BASE_DIR, MODELS_DIR, EVIDENCE_DIR, TEMP_DIR, TRAINING_RUNS_DIR, DATABASE_PATH

class StartupSplash:
    """Minimal splash screen for startup progress."""

    def __init__(self):
        """Create splash screen."""
        self.splash = None
        self._create_splash()

    def _create_splash(self) -> None:
        """Create and show splash screen."""
        # Create a minimal pixmap (white background with dark text)
        pixmap = QPixmap(500, 300)
        pixmap.fill(QColor(255, 255, 255))

        self.splash = QSplashScreen(pixmap)
        self.splash.setWindowFlags(self.splash.windowFlags() | Qt.FramelessWindowHint)

        # Draw title
        font = QFont("Arial", 16, QFont.Bold)
        self.splash.setFont(font)
        self.splash.showMessage(
            "🚨 Industrial Safety Surveillance System",
            Qt.AlignCenter | Qt.AlignTop,
            QColor(0, 0, 0),
        )

        self.splash.show()
        QApplication.processEvents()

    def update_status(self, message: str) -> None:
        """Update splash screen message."""
        if self.splash:
            font = QFont("Arial", 10)
            self.splash.setFont(font)
            self.splash.showMessage(
                message,
                Qt.AlignCenter | Qt.AlignBottom,
                QColor(80, 80, 80),
            )
            QApplication.processEvents()

    def close(self) -> None:
        """Close splash screen."""
        if self.splash:
            self.splash.close()


def ensure_project_structure() -> bool:
    """Ensure all project directories exist. Returns True if successful."""
    try:
        directories = [
            MODELS_DIR,
            DATASETS_DIR := BASE_DIR / "datasets",
            EVIDENCE_DIR,
            TEMP_DIR,
            TRAINING_RUNS_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        return True
    except Exception as e:
        print(f"❌ Failed to create project structure: {e}")
        return False


def initialize_databases() -> bool:
    """Initialize SQLite databases. Returns True if successful."""
    try:
        from database import create_incidents_table
        from core.camera_db import create_cameras_table

        create_incidents_table(DATABASE_PATH)
        create_cameras_table(DATABASE_PATH)

        return True
    except Exception as e:
        print(f"❌ Failed to initialize databases: {e}")
        return False


def optimize_model_loading() -> Optional[str]:
    """
    Pre-resolve model path for faster access later.
    Returns the resolved model path or None if not found.
    """
    try:
        from core.model_utils import resolve_model_path

        model_path = resolve_model_path(
            base_dir=BASE_DIR,
            models_dir=MODELS_DIR,
        )

        if model_path:
            return model_path
        else:
            print("⚠️ No trained model found. App will run in demo mode.")
            return None

    except Exception as e:
        print(f"⚠️ Model resolution failed: {e}. Defaulting to demo mode.")
        return None


def run_startup_sequence() -> tuple[bool, Optional[str]]:
    """
    Run complete startup sequence.

    Returns:
        (success: bool, model_path: Optional[str])
        success=True if all critical systems initialized
        model_path=resolved path or None for demo mode
    """
    splash = StartupSplash()

    try:
        # Step 1: Ensure directories
        splash.update_status("📁 Setting up project structure...")
        if not ensure_project_structure():
            splash.update_status("❌ Failed to create directories")
            return False, None

        # Step 2: Initialize databases
        splash.update_status("🗄️  Initializing database...")
        if not initialize_databases():
            splash.update_status("❌ Failed to initialize database")
            return False, None

        # Step 3: Resolve model path
        splash.update_status("🤖 Locating AI model...")
        model_path = optimize_model_loading()

        # Step 4: Final checks
        splash.update_status("✅ Startup complete!")

        splash.close()
        return True, model_path

    except Exception as e:
        splash.update_status(f"❌ Startup error: {str(e)[:50]}")
        splash.close()
        return False, None


def set_performance_hints() -> None:
    """Apply performance hints to Qt application."""
    try:
        import os

        # Suppress OpenCV logging
        os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

        # Optimize Qt rendering
        os.environ["QT_QPA_PLATFORM"] = "windows"

        # Setup GPU optimization if available
        try:
            from GPU_OPTIMIZATION_CONFIG import apply_all_gpu_optimizations
            apply_all_gpu_optimizations()
        except ImportError:
            pass  # GPU optimization module not needed

    except Exception:
        pass  # Non-critical


class LazyModelLoader:
    """
    Lazy loader for the YOLO model.
    Defers model loading until first use.
    """

    def __init__(self, model_path: Optional[str]):
        self.model_path = model_path
        self._model = None
        self._load_error = None

    def get_model(self):
        """Load and cache the model on first access."""
        if self._model is not None:
            return self._model

        if self._load_error is not None:
            raise self._load_error

        try:
            from detector import load_model

            if self.model_path is None:
                raise FileNotFoundError("No model path available")

            self._model = load_model(self.model_path)
            return self._model

        except Exception as e:
            self._load_error = e
            raise

    def is_loaded(self) -> bool:
        """Check if model is already loaded."""
        return self._model is not None

    def preload_async(self) -> None:
        """
        Schedule model loading on next event loop tick (non-blocking).
        Useful to warm up the model in background.
        """
        def _load():
            try:
                self.get_model()
            except Exception:
                pass  # Silently ignore preload errors

        QTimer.singleShot(500, _load)