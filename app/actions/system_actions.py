from __future__ import annotations

import subprocess
from datetime import datetime


def get_current_time() -> str:
    return f"Son las {datetime.now():%H:%M}."


def get_current_date() -> str:
    return f"Hoy es {datetime.now():%Y-%m-%d}."


def restart_computer(safe_mode: bool) -> str:
    if safe_mode:
        return "Modo seguro activo: se habria reiniciado el equipo."

    subprocess.Popen(["shutdown", "/r", "/t", "0"])
    return "Reiniciando el equipo."


def shutdown_computer(safe_mode: bool) -> str:
    if safe_mode:
        return "Modo seguro activo: se habria apagado el equipo."

    subprocess.Popen(["shutdown", "/s", "/t", "0"])
    return "Apagando el equipo."


def build_confirmation_prompt(action: str) -> str:
    prompts = {
        "restart": "Esta accion es sensible: reiniciar el equipo. Responde si o no.",
        "shutdown": "Esta accion es sensible: apagar el equipo. Responde si o no.",
    }
    return prompts.get(action, "Esta accion requiere confirmacion. Responde si o no.")
