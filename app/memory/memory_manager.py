from __future__ import annotations

import json
from pathlib import Path


class MemoryManager:
    def __init__(self, aliases_path: Path) -> None:
        self.aliases_path = aliases_path

    def location(self) -> str:
        return str(self.aliases_path)

    def load_aliases(self) -> dict[str, dict[str, str]]:
        default_aliases = {"custom_paths": {}, "custom_apps": {}}

        if not self.aliases_path.exists():
            return default_aliases

        try:
            data = json.loads(self.aliases_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return default_aliases

        custom_paths = data.get("custom_paths", {})
        custom_apps = data.get("custom_apps", {})

        if not isinstance(custom_paths, dict):
            custom_paths = {}
        if not isinstance(custom_apps, dict):
            custom_apps = {}

        return {
            "custom_paths": {str(key): str(value) for key, value in custom_paths.items()},
            "custom_apps": {str(key): str(value) for key, value in custom_apps.items()},
        }
