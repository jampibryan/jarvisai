from __future__ import annotations

"""Tipos de intencion que el parser puede devolver al resto del asistente."""

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    # Apertura de rutas o aplicaciones conocidas.
    OPEN_PATH = 'open_path'
    OPEN_APP = 'open_app'
    OPEN_URL = 'open_url'
    FILE_SELECTION = 'file_selection'
    WEB_SEARCH = 'web_search'
    SEARCH_FILE = 'search_file'
    OPEN_SEARCH_RESULT = 'open_search_result'
    CREATE_NOTE = 'create_note'
    SET_TIMER = 'set_timer'
    YOUTUBE = 'youtube'
    YOUTUBE_CONTROL = 'youtube_control'
    IMPORTANT_EMAIL = 'important_email'
    CONNECT_GMAIL = 'connect_gmail'
    CLARIFY_COMMAND = 'clarify_command'
    LIST_WINDOWS = 'list_windows'
    CLOSE_WINDOW = 'close_window'

    # Consultas simples del sistema.
    GET_TIME = 'get_time'
    GET_DATE = 'get_date'
    LIST_COMMANDS = 'list_commands'
    SHOW_METRICS = 'show_metrics'
    SHOW_STATUS = 'show_status'

    # Aprendizaje y mantenimiento de alias personalizados.
    LEARN_ALIAS = 'learn_alias'
    REPLACE_ALIAS = 'replace_alias'

    # Acciones sensibles que pueden requerir confirmacion.
    RESTART_COMPUTER = 'restart_computer'
    SHUTDOWN_COMPUTER = 'shutdown_computer'
    CONFIRM = 'confirm'
    CANCEL = 'cancel'

    # Control general del asistente.
    EXIT = 'exit'
    UNKNOWN = 'unknown'


@dataclass(slots=True)
class ParsedCommand:
    """Resultado del parser.

    raw_text:
        Texto original que dijo o escribio el usuario.
    normalized_text:
        Version normalizada usada para comparar reglas.
    intent:
        Intencion detectada.
    entity:
        Entidad principal, por ejemplo `documents` o `chrome`.
    metadata:
        Datos extra para alias, destinos resueltos o contexto adicional.
    """

    raw_text: str
    normalized_text: str
    intent: Intent
    entity: str = ''
    metadata: dict[str, str] = field(default_factory=dict)

