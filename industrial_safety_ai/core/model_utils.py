from __future__ import annotations

from pathlib import Path


def resolve_model_path(
    base_dir: Path | None = None,
    models_dir: Path | None = None,
) -> str | None:
    """Find the first .pt model file, preferring models_dir over base_dir.

    Returns the string path to the model, or None if no .pt file is found.
    """
    if models_dir is not None and models_dir.exists():
        pts = sorted(models_dir.glob("*.pt"))
        if pts:
            return str(pts[0])

    if base_dir is not None:
        pts = sorted(base_dir.glob("*.pt"))
        if pts:
            return str(pts[0])

    return None
