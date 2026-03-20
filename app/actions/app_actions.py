from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def open_application(target: str) -> str:
    if not target:
        return "No hay una aplicacion configurada para ese comando. Revisa data/aliases.json o app/config.py."

    candidate = Path(target)
    if candidate.exists():
        os.startfile(str(candidate))
        return f"Abriendo {candidate.name}."

    resolved = shutil.which(target)
    if resolved:
        subprocess.Popen([resolved])
        return f"Abriendo {target}."

    for command in _build_fallback_commands(target):
        try:
            subprocess.Popen(command, shell=isinstance(command, str))
            return f"Abriendo {target}."
        except OSError:
            continue

    return f"No pude abrir la aplicacion configurada: {target}."


def _build_fallback_commands(target: str) -> list[str | list[str]]:
    fallbacks: dict[str, list[str | list[str]]] = {
        "chrome": [
            ["cmd", "/c", "start", "", "chrome"],
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "https://www.google.com",
        ],
        "vscode": [
            ["cmd", "/c", "start", "", "code"],
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        ],
        "excel": [
            ["cmd", "/c", "start", "", "excel"],
        ],
        "power_bi": [
            ["cmd", "/c", "start", "", "pbidesktop"],
        ],
        "whatsapp": [
            ["cmd", "/c", "start", "", "whatsapp:"],
            ["cmd", "/c", "start", "", "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"],
        ],
    }

    commands = fallbacks.get(target, [["cmd", "/c", "start", "", target]])
    expanded_commands: list[str | list[str]] = []
    for command in commands:
        if isinstance(command, str):
            expanded_commands.append(os.path.expandvars(command))
        else:
            expanded_commands.append([os.path.expandvars(part) for part in command])
    return expanded_commands
