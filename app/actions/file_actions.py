from __future__ import annotations

import os
import subprocess
from pathlib import Path


def open_path(target: str) -> str:
    if not target:
        return "No hay una ruta configurada para ese comando. Revisa data/aliases.json o app/config.py."

    path = Path(target)
    if not path.exists():
        return f"La ruta configurada no existe: {path}"

    try:
        if path.is_dir():
            subprocess.Popen(["explorer", str(path)])
        else:
            os.startfile(str(path))
        return f"Abriendo {path}."
    except OSError as exc:
        return f"No pude abrir la ruta configurada: {path}. Detalle: {exc}"
