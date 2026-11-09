from __future__ import annotations

from pathlib import Path


def create_shortcut(root: Path) -> Path:
    from win32com.client import Dispatch

    location = root / 'JarvisAI.lnk'
    shortcut = Dispatch('WScript.Shell').CreateShortcut(str(location))
    shortcut.TargetPath = str(root / 'venv' / 'Scripts' / 'pythonw.exe')
    shortcut.Arguments = f'"{root / "main.py"}" --desktop --require-wake-word'
    shortcut.WorkingDirectory = str(root)
    shortcut.IconLocation = f'{root / "app" / "ui" / "neural.ico"},0'
    shortcut.Description = 'JarvisAI · NEURAL OS'
    shortcut.Save()
    return location
