from pathlib import Path

from core.model_utils import resolve_model_path


def test_prefers_model_file_in_models_directory(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "yolov8n.pt").write_bytes(b"model")
    (tmp_path / "fallback.pt").write_bytes(b"fallback")

    resolved = resolve_model_path(base_dir=tmp_path, models_dir=models_dir)

    assert resolved == str(models_dir / "yolov8n.pt")


def test_falls_back_to_project_root_when_models_dir_is_empty(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (tmp_path / "root_model.pt").write_bytes(b"model")

    resolved = resolve_model_path(base_dir=tmp_path, models_dir=models_dir)

    assert resolved == str(tmp_path / "root_model.pt")


def test_returns_none_when_no_model_file_exists(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    resolved = resolve_model_path(base_dir=tmp_path, models_dir=models_dir)

    assert resolved is None
