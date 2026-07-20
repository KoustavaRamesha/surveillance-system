from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULTS = {
    "app_name": "Industrial Safety Monitor",
    "theme": "dark",
    "auto_connect_on_startup": False,
}


class SettingsManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).resolve().parent.parent / "settings.json"
        if not self.path.exists():
            self._write(DEFAULTS)

    def _read(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, data: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        data = self._read()
        return data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)
