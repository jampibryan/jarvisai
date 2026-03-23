from __future__ import annotations

import subprocess
from datetime import datetime

COUNTDOWN_SECONDS = 3


def get_current_time() -> str:
    return f'Son las {datetime.now():%H:%M}.'


def get_current_date() -> str:
    return f'Hoy es {datetime.now():%Y-%m-%d}.'


def restart_computer(safe_mode: bool) -> str:
    if safe_mode:
        return f'Modo seguro activo: se habria reiniciado el equipo en {COUNTDOWN_SECONDS}, 2, 1.'

    try:
        subprocess.Popen(['shutdown.exe', '/r', '/t', str(COUNTDOWN_SECONDS)])
        return f'Reiniciando el equipo en {COUNTDOWN_SECONDS}, 2, 1.'
    except OSError as exc:
        return f'No pude reiniciar el equipo. Detalle: {exc}'


def shutdown_computer(safe_mode: bool) -> str:
    if safe_mode:
        return f'Modo seguro activo: se habria apagado el equipo en {COUNTDOWN_SECONDS}, 2, 1.'

    try:
        subprocess.Popen(['shutdown.exe', '/s', '/t', str(COUNTDOWN_SECONDS)])
        return f'Apagando el equipo en {COUNTDOWN_SECONDS}, 2, 1.'
    except OSError as exc:
        return f'No pude apagar el equipo. Detalle: {exc}'


def build_confirmation_prompt(action: str, heard_text: str = '', safe_mode: bool = True) -> str:
    action_label = {
        'restart': 'reiniciar el equipo',
        'shutdown': 'apagar el equipo',
    }.get(action, 'ejecutar una accion sensible')

    execution_mode = 'solo se simulara' if safe_mode else 'se ejecutara de verdad'
    if heard_text:
        return (
            f"Entendi: '{heard_text}'. Esta accion es sensible: {action_label}. "
            f"En este modo {execution_mode}. Responde si o no."
        )

    return f'Esta accion es sensible: {action_label}. En este modo {execution_mode}. Responde si o no.'
