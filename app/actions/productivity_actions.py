from __future__ import annotations

import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from app.actions.file_search import find_files

_ACTIVE_TIMERS: list[threading.Timer] = []
FRIENDLY_URL_LABELS = {
    'chatgpt.com': 'ChatGPT',
    'www.youtube.com': 'YouTube',
    'youtube.com': 'YouTube',
    'mail.google.com': 'Gmail',
    'github.com': 'GitHub',
    'web.whatsapp.com': 'WhatsApp Web',
    'www.facebook.com': 'Facebook',
    'facebook.com': 'Facebook',
    'www.instagram.com': 'Instagram',
    'instagram.com': 'Instagram',
    'www.tiktok.com': 'TikTok',
    'tiktok.com': 'TikTok',
    'x.com': 'X',
    'www.linkedin.com': 'LinkedIn',
    'linkedin.com': 'LinkedIn',
    'drive.google.com': 'Google Drive',
    'maps.google.com': 'Google Maps',
    'translate.google.com': 'Google Translate',
    'www.netflix.com': 'Netflix',
    'netflix.com': 'Netflix',
    'open.spotify.com': 'Spotify',
    'discord.com': 'Discord',
    'discord.com/app': 'Discord',
    'web.telegram.org': 'Telegram Web',
    'www.notion.so': 'Notion',
    'notion.so': 'Notion',
    'www.canva.com': 'Canva',
    'canva.com': 'Canva',
    'calendar.google.com': 'Google Calendar',
    'meet.google.com': 'Google Meet',
    'claude.ai': 'Claude',
    'gemini.google.com': 'Gemini',
    'copilot.microsoft.com': 'Copilot',
    'www.perplexity.ai': 'Perplexity',
    'perplexity.ai': 'Perplexity',
    'stackoverflow.com': 'Stack Overflow',
    'www.reddit.com': 'Reddit',
    'reddit.com': 'Reddit',
    'www.amazon.com': 'Amazon',
    'amazon.com': 'Amazon',
    'www.mercadolibre.com': 'Mercado Libre',
    'mercadolibre.com': 'Mercado Libre',
    'openai.com': 'OpenAI',
    'www.openai.com': 'OpenAI',
}


def open_url(url: str) -> str:
    if not url:
        return 'No me dijiste que direccion web abrir.'

    friendly_name = _friendly_url_name(url)
    try:
        opened = webbrowser.open(url, new=2)
    except OSError as exc:
        return f'No pude abrir {friendly_name.lower()}. Detalle: {exc}'

    if not opened:
        return f'No pude abrir {friendly_name.lower()}.'

    return f'Abriendo {friendly_name}.'


def web_search(query: str) -> str:
    if not query:
        return 'No me dijiste que buscar en la web.'

    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.google.com/search?q={encoded_query}"
    try:
        opened = webbrowser.open(search_url, new=2)
    except OSError as exc:
        return f'No pude realizar la busqueda en la web. Detalle: {exc}'

    if not opened:
        return 'No pude abrir el navegador para la busqueda.'

    return f'Buscando "{query}" en Google.'


def create_quick_note(notes_dir: Path, content: str) -> str:
    clean_content = content.strip()
    if not clean_content:
        return 'No me dijiste que contenido guardar en la nota.'

    notes_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now()
    filename = f"{timestamp:%Y%m%d_%H%M%S}_{_slugify(clean_content)}.txt"
    note_path = notes_dir / filename
    note_path.write_text(clean_content + '\n', encoding='utf-8')
    return f'Nota guardada en {note_path}.'


def search_files(query: str, roots: list[Path], limit: int = 5) -> str:
    if not query.strip():
        return 'Debes decirme que archivo quieres buscar.'
    return find_files(query, roots, limit=limit).display()


def start_timer(duration_seconds: int, label: str = '') -> str:
    if duration_seconds <= 0:
        return 'El temporizador debe durar al menos 1 segundo.'

    timer = threading.Timer(duration_seconds, _timer_finished, kwargs={'duration_seconds': duration_seconds, 'label': label})
    timer.daemon = True
    _ACTIVE_TIMERS.append(timer)
    timer.start()

    label_suffix = f' para {label}' if label else ''
    return f'Temporizador iniciado por {_format_duration(duration_seconds)}{label_suffix}.'


def _timer_finished(duration_seconds: int, label: str = '') -> None:
    label_text = f' para {label}' if label else ''
    print(f'\nTemporizador completado despues de {_format_duration(duration_seconds)}{label_text}.\a')


def _format_duration(duration_seconds: int) -> str:
    if duration_seconds % 3600 == 0:
        hours = duration_seconds // 3600
        return f'{hours} hora' + ('s' if hours != 1 else '')
    if duration_seconds % 60 == 0:
        minutes = duration_seconds // 60
        return f'{minutes} minuto' + ('s' if minutes != 1 else '')
    return f'{duration_seconds} segundo' + ('s' if duration_seconds != 1 else '')


def _slugify(text: str) -> str:
    normalized = _normalize_text(text).replace(' ', '_').strip('_')
    return (normalized[:40] or 'nota').rstrip('_')


def _normalize_text(text: str) -> str:
    collapsed = ''.join(char.lower() if char.isalnum() else ' ' for char in text)
    return ' '.join(collapsed.split())


def _friendly_url_name(url: str) -> str:
    cleaned = url.strip().lower()
    cleaned = cleaned.removeprefix('https://').removeprefix('http://').rstrip('/')
    if cleaned in FRIENDLY_URL_LABELS:
        return FRIENDLY_URL_LABELS[cleaned]

    host = cleaned.split('/', 1)[0]
    if host in FRIENDLY_URL_LABELS:
        return FRIENDLY_URL_LABELS[host]

    if host.startswith('www.'):
        host = host[4:]

    name = host.split('.', 1)[0]
    return name.capitalize() if name else 'la pagina solicitada'
