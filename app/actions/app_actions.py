from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


CONSOLE_TARGETS = {'cmd'}
FRIENDLY_TARGET_LABELS = {
    'chrome': 'Chrome',
    'chatgpt': 'ChatGPT',
    'youtube': 'YouTube',
    'gmail': 'Gmail',
    'github': 'GitHub',
    'facebook': 'Facebook',
    'instagram': 'Instagram',
    'tiktok': 'TikTok',
    'x': 'X',
    'linkedin': 'LinkedIn',
    'drive': 'Google Drive',
    'maps': 'Google Maps',
    'translate': 'Google Translate',
    'netflix': 'Netflix',
    'spotify': 'Spotify',
    'discord': 'Discord',
    'telegram': 'Telegram',
    'notion': 'Notion',
    'canva': 'Canva',
    'calendar': 'Google Calendar',
    'meet': 'Google Meet',
    'claude': 'Claude',
    'gemini': 'Gemini',
    'copilot': 'Copilot',
    'perplexity': 'Perplexity',
    'stackoverflow': 'Stack Overflow',
    'reddit': 'Reddit',
    'amazon': 'Amazon',
    'mercadolibre': 'Mercado Libre',
    'brave': 'Brave',
    'vscode': 'Visual Studio Code',
    'cmd': 'CMD',
    'notepad': 'Bloc de notas',
    'calculator': 'Calculadora',
    'paint': 'Paint',
    'task_manager': 'Administrador de tareas',
    'control_panel': 'Panel de control',
    'settings': 'Configuracion',
    'excel': 'Excel',
    'power_bi': 'Power BI',
    'whatsapp': 'WhatsApp',
    'https://chatgpt.com': 'ChatGPT',
    'https://www.youtube.com': 'YouTube',
    'https://mail.google.com': 'Gmail',
    'https://github.com': 'GitHub',
    'https://web.whatsapp.com': 'WhatsApp Web',
    'https://www.facebook.com': 'Facebook',
    'https://www.instagram.com': 'Instagram',
    'https://www.tiktok.com': 'TikTok',
    'https://x.com': 'X',
    'https://www.linkedin.com': 'LinkedIn',
    'https://drive.google.com': 'Google Drive',
    'https://maps.google.com': 'Google Maps',
    'https://translate.google.com': 'Google Translate',
    'https://www.netflix.com': 'Netflix',
    'https://open.spotify.com': 'Spotify',
    'https://discord.com/app': 'Discord',
    'https://web.telegram.org': 'Telegram Web',
    'https://www.notion.so': 'Notion',
    'https://www.canva.com': 'Canva',
    'https://calendar.google.com': 'Google Calendar',
    'https://meet.google.com': 'Google Meet',
    'https://claude.ai': 'Claude',
    'https://gemini.google.com': 'Gemini',
    'https://copilot.microsoft.com': 'Copilot',
    'https://www.perplexity.ai': 'Perplexity',
    'https://stackoverflow.com': 'Stack Overflow',
    'https://www.reddit.com': 'Reddit',
    'https://www.amazon.com': 'Amazon',
    'https://www.mercadolibre.com': 'Mercado Libre',
}


def open_application(
    target: str,
    display_name: str = '',
    fallback_target: str = '',
    fallback_display_name: str = '',
    allow_generic_start: bool = True,
) -> str:
    """Abre una aplicacion usando la mejor estrategia disponible.

    Primero intentamos rutas explicitas, luego ejecutables resolubles y al
    final caemos a comandos de Windows mas especificos para cada app.
    """
    if not target and fallback_target:
        fallback_name = _friendly_target_name(fallback_target, fallback_display_name)
        if _try_open_target(fallback_target):
            return f'Abriendo {fallback_name}.'
        return f'No pude abrir {fallback_name.lower()}.'

    if not target:
        return 'No hay una aplicacion configurada para ese comando. Revisa tus alias o app/config.py.'

    friendly_name = _friendly_target_name(target, display_name)
    if _try_open_target(target, allow_generic_start=allow_generic_start):
        return f'Abriendo {friendly_name}.'

    if fallback_target:
        fallback_name = _friendly_target_name(fallback_target, fallback_display_name)
        if _try_open_target(fallback_target):
            return f'No encontre la app de escritorio de {friendly_name}. Abriendo {fallback_name}.'

    return f'No pude abrir {friendly_name.lower()}.'


def _try_open_target(target: str, allow_generic_start: bool = True) -> bool:
    if target.lower().startswith(('http://', 'https://')):
        try:
            if urlsplit(target).hostname:
                os.startfile(target)
                return True
        except (OSError, ValueError):
            pass
        return False

    try:
        candidate = Path(target)
        if candidate.is_file() and candidate.suffix.lower() in {'.exe', '.com', '.lnk'}:
            if candidate.suffix.lower() == '.lnk':
                os.startfile(str(candidate.resolve()))
            else:
                _launch_process([str(candidate.resolve())], target=target)
            return True

        if re.fullmatch(r'[a-zA-Z0-9_-]+(?:\.(?:exe|com))?', target, flags=re.IGNORECASE):
            resolved = shutil.which(target)
            if resolved and Path(resolved).suffix.lower() in {'.exe', '.com'}:
                _launch_process([resolved], target=target)
                return True
    except OSError:
        pass

    for command in _build_fallback_commands(target, allow_generic_start=allow_generic_start):
        try:
            if _try_open_explicit_path(command):
                return True
            if isinstance(command, list):
                _launch_process(command, target=target)
            elif command.startswith(('https://', 'shell:', 'ms-settings:', 'spotify:', 'whatsapp:', 'discord:', 'tg:')) or re.fullmatch(r'[a-zA-Z0-9_-]+\.exe', command, flags=re.IGNORECASE):
                os.startfile(command)
            else:
                continue
            return True
        except OSError:
            continue

    return False


def _try_open_explicit_path(command: str | list[str]) -> bool:
    if not isinstance(command, str):
        return False

    for resolved_path in _resolve_explicit_path_candidates(command):
        candidate = Path(resolved_path)
        if not candidate.exists():
            continue

        _launch_process([str(candidate.resolve())], target=str(candidate))
        return True

    return False


def _resolve_explicit_path_candidates(command: str) -> list[str]:
    if not any(token in command for token in ('*', '?', '[')):
        return [command]

    return sorted(glob.glob(command))


def _launch_process(command: list[str], target: str = '') -> None:
    creationflags = _creation_flags_for_target(target, command)
    popen_kwargs: dict[str, object] = {
        'shell': False,
        'creationflags': creationflags,
    }

    if _should_silence_process_output(target, command):
        popen_kwargs['stdin'] = subprocess.DEVNULL
        popen_kwargs['stdout'] = subprocess.DEVNULL
        popen_kwargs['stderr'] = subprocess.DEVNULL

    subprocess.Popen(command, **popen_kwargs)


def _creation_flags_for_target(target: str, command: str | list[str]) -> int:
    create_new_console = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)
    create_no_window = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    detached_process = getattr(subprocess, 'DETACHED_PROCESS', 0)
    normalized_target = target.strip().lower()

    if normalized_target in CONSOLE_TARGETS:
        return create_new_console

    if isinstance(command, list) and command:
        executable = Path(command[0]).name.lower()
        if executable in {'cmd', 'cmd.exe'}:
            return create_new_console

    return detached_process | create_no_window


def _should_silence_process_output(target: str, command: str | list[str]) -> bool:
    normalized_target = target.strip().lower()
    if normalized_target in CONSOLE_TARGETS:
        return False

    if isinstance(command, list) and command:
        executable = Path(command[0]).name.lower()
        if executable in {'cmd', 'cmd.exe'}:
            return False

    return True


def _build_fallback_commands(target: str, allow_generic_start: bool = True) -> list[str | list[str]]:
    fallbacks: dict[str, list[str | list[str]]] = {
        'chrome': [
            r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            'chrome.exe',
            'https://www.google.com',
        ],
        'brave': [
            r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe',
            r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
            r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
            'brave.exe',
        ],
        'vscode': [
            r'%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe',
            r'%ProgramFiles%\Microsoft VS Code\Code.exe',
            'code.exe',
        ],
        'excel': [
            'excel.exe',
        ],
        'power_bi': [
            'pbidesktop.exe',
        ],
        'whatsapp': [
            r'%LOCALAPPDATA%\WhatsApp\WhatsApp.exe',
            r'%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe',
            'whatsapp:',
            'shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App',
        ],
        'drive': [
            r'%ProgramFiles%\Google\Drive File Stream\GoogleDriveFS.exe',
            r'%ProgramFiles%\Google\Drive File Stream\*\GoogleDriveFS.exe',
            r'%ProgramFiles(x86)%\Google\Drive File Stream\GoogleDriveFS.exe',
            r'%ProgramFiles(x86)%\Google\Drive File Stream\*\GoogleDriveFS.exe',
            r'%LOCALAPPDATA%\Google\DriveFS\GoogleDriveFS.exe',
        ],
        'spotify': [
            r'%APPDATA%\Spotify\Spotify.exe',
            r'%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe',
            'spotify:',
            'shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify',
        ],
        'discord': [
            [r'%LOCALAPPDATA%\Discord\Update.exe', '--processStart', 'Discord.exe'],
            [r'%LOCALAPPDATA%\DiscordCanary\Update.exe', '--processStart', 'DiscordCanary.exe'],
            [r'%LOCALAPPDATA%\DiscordPTB\Update.exe', '--processStart', 'DiscordPTB.exe'],
            'discord:',
        ],
        'telegram': [
            r'%APPDATA%\Telegram Desktop\Telegram.exe',
            r'%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe',
            'tg://resolve',
        ],
        'notion': [
            r'%LOCALAPPDATA%\Programs\Notion\Notion.exe',
            r'%LOCALAPPDATA%\Notion\Notion.exe',
        ],
        'canva': [
            r'%LOCALAPPDATA%\Canva\Canva.exe',
            r'%LOCALAPPDATA%\Programs\Canva\Canva.exe',
        ],
        'cmd': [
            ['cmd.exe'],
        ],
        'notepad': [
            ['notepad.exe'],
        ],
        'calculator': [
            ['calc.exe'],
        ],
        'paint': [
            ['mspaint.exe'],
        ],
        'task_manager': [
            ['taskmgr.exe'],
        ],
        'control_panel': [
            ['control.exe'],
        ],
        'settings': [
            'ms-settings:',
        ],
    }

    commands = fallbacks.get(target)
    if commands is None:
        if allow_generic_start and re.fullmatch(r'[a-zA-Z0-9_-]+(?:\.exe)?', target, flags=re.IGNORECASE):
            commands = [target if target.lower().endswith('.exe') else f'{target}.exe']
        else:
            commands = []
    expanded_commands: list[str | list[str]] = []

    for command in commands:
        if isinstance(command, str):
            expanded_commands.append(os.path.expandvars(command))
            continue

        expanded_commands.append([os.path.expandvars(part) for part in command])

    return expanded_commands


def _friendly_target_name(target: str, display_name: str = '') -> str:
    cleaned_display_name = display_name.strip()
    if cleaned_display_name:
        return cleaned_display_name

    normalized_target = target.strip()
    if not normalized_target:
        return 'esa aplicacion'

    if normalized_target in FRIENDLY_TARGET_LABELS:
        return FRIENDLY_TARGET_LABELS[normalized_target]

    path_candidate = Path(normalized_target)
    if path_candidate.suffix:
        return path_candidate.stem

    return normalized_target
