from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from app.actions.app_actions import FRIENDLY_TARGET_LABELS, open_application
from app.actions.file_actions import open_path
from app.actions.file_search import FileSearchResult, find_files
from app.actions.selected_files import FilePlan, plan_file_action
from app.actions.productivity_actions import create_quick_note, open_url, start_timer, web_search
from app.actions.system_actions import get_current_date, get_current_time, restart_computer, shutdown_computer
from app.actions.window_actions import list_windows
from app.integrations.chat import ChatError
from app.integrations.deepseek_client import DeepSeekClient
from app.integrations.gemini_client import GeminiClient
from app.integrations.gmail_client import GmailClient
from app.integrations.youtube_player import YouTubePlayer
from app.brain.command_catalog import BUILTIN_APP_COMMANDS, UNKNOWN_COMMAND_SUGGESTIONS
from app.brain.intents import Intent, ParsedCommand
from app.config import AppConfig
from app.memory.memory_manager import MemoryManager


class CommandRouter:
    """Conecta una intencion ya entendida con la accion concreta a ejecutar."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        memory_manager: MemoryManager,
        chat_history: list[dict[str, str]] | None = None,
        youtube: YouTubePlayer | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.memory_manager = memory_manager
        self._chat_history = chat_history if chat_history is not None else []
        self.youtube = youtube if youtube is not None else YouTubePlayer(config.aliases_path.parent / 'youtube-browser')
        self.gmail = GmailClient(config.google_credentials_path, config.google_gmail_token_path)
        self._chat_client: GeminiClient | DeepSeekClient | None = None
        if config.ai_provider == 'gemini' and config.gemini_api_key:
            self._chat_client = GeminiClient(config.gemini_api_key, config.gemini_model)
        elif config.ai_provider == 'deepseek' and config.deepseek_api_key:
            self._chat_client = DeepSeekClient(config.deepseek_api_key, config.deepseek_model)

        # Usamos un mapa de handlers para que la relacion intent -> accion
        # sea facil de leer y de extender.
        self._handlers: dict[Intent, Callable[[ParsedCommand], str]] = {
            Intent.OPEN_PATH: self._handle_open_path,
            Intent.OPEN_APP: self._handle_open_app,
            Intent.OPEN_URL: self._handle_open_url,
            Intent.WEB_SEARCH: self._handle_web_search,
            Intent.SEARCH_FILE: self._handle_search_file,
            Intent.CREATE_NOTE: self._handle_create_note,
            Intent.SET_TIMER: self._handle_set_timer,
            Intent.YOUTUBE: self._handle_youtube,
            Intent.YOUTUBE_CONTROL: self._handle_youtube_control,
            Intent.IMPORTANT_EMAIL: self._handle_important_email,
            Intent.CONNECT_GMAIL: self._handle_connect_gmail,
            Intent.LIST_WINDOWS: self._handle_list_windows,
            Intent.GET_TIME: self._handle_get_time,
            Intent.GET_DATE: self._handle_get_date,
            Intent.LIST_COMMANDS: self._handle_list_commands,
            Intent.SHOW_METRICS: self._handle_show_metrics,
            Intent.LEARN_ALIAS: self._handle_learn_alias,
            Intent.REPLACE_ALIAS: self._handle_replace_alias,
            Intent.RESTART_COMPUTER: self._handle_restart,
            Intent.SHUTDOWN_COMPUTER: self._handle_shutdown,
            Intent.EXIT: self._handle_exit,
        }

    def handle(self, command: ParsedCommand) -> str:
        self.logger.info('Intent: %s', command.intent.value)
        if command.intent in {Intent.CONFIRM, Intent.CANCEL}:
            return 'No hay una acción pendiente de confirmación.'
        if command.intent is Intent.FILE_SELECTION:
            return 'No hay una operación del Explorador preparada.'
        if command.intent is Intent.OPEN_SEARCH_RESULT:
            return 'No hay un resultado de búsqueda preparado.'
        if command.intent is Intent.CLOSE_WINDOW:
            return 'Primero debes confirmar la ventana que quieres cerrar.'
        return self._handlers.get(command.intent, self._handle_unknown)(command)

    def prepare_file_action(self, command: ParsedCommand) -> FilePlan:
        destination = command.metadata.get('destination') or self.config.path_aliases.get(
            command.metadata.get('folder_entity', ''), '',
        )
        return plan_file_action(
            command.entity, destination=destination, argument=command.metadata.get('argument', ''),
        )

    def _handle_open_path(self, command: ParsedCommand) -> str:
        target = command.metadata.get('target') or self.config.path_aliases.get(command.entity, '')
        return open_path(target)

    def _handle_open_app(self, command: ParsedCommand) -> str:
        if command.metadata.get('target'):
            return open_application(
                command.metadata.get('target', ''),
                display_name=command.metadata.get('label', ''),
            )

        display_name = self._app_display_name(command.entity)
        web_target = self.config.app_web_targets.get(command.entity, '')
        web_display_name = self._web_display_name(display_name)

        if command.metadata.get('open_mode') == 'web' and web_target:
            return open_application(web_target, display_name=web_display_name)

        target = self.config.app_targets.get(command.entity, '')
        return open_application(
            target,
            display_name=display_name,
            fallback_target=web_target,
            fallback_display_name=web_display_name,
            allow_generic_start=not bool(web_target),
        )

    def _handle_get_time(self, _: ParsedCommand) -> str:
        return get_current_time()

    def _handle_get_date(self, _: ParsedCommand) -> str:
        return get_current_date()

    def _handle_open_url(self, command: ParsedCommand) -> str:
        return open_url(command.metadata.get('url', ''))

    def _handle_search_file(self, command: ParsedCommand) -> str:
        return self.find_files(command.metadata.get('query', '')).display()

    def find_files(self, query: str) -> FileSearchResult:
        return find_files(query, self._build_search_roots())

    def _handle_create_note(self, command: ParsedCommand) -> str:
        return create_quick_note(self.config.notes_dir, command.metadata.get('content', ''))

    def _handle_set_timer(self, command: ParsedCommand) -> str:
        duration = int(command.metadata.get('duration_seconds', '0') or '0')
        return start_timer(duration, label=command.metadata.get('label', ''))

    def _handle_list_commands(self, _: ParsedCommand) -> str:
        return self.memory_manager.render_command_summary()

    def _handle_show_metrics(self, _: ParsedCommand) -> str:
        return self.memory_manager.render_metrics_summary()

    def _handle_learn_alias(self, command: ParsedCommand) -> str:
        return self.memory_manager.save_alias(
            alias_kind=command.metadata['alias_kind'],
            label=command.metadata['label'],
            target=command.metadata['target'],
            replace=False,
        )['message']

    def _handle_replace_alias(self, command: ParsedCommand) -> str:
        return self.memory_manager.save_alias(
            alias_kind=command.metadata['alias_kind'],
            label=command.metadata['label'],
            target=command.metadata['target'],
            replace=True,
        )['message']

    def _handle_restart(self, _: ParsedCommand) -> str:
        return restart_computer(self.config.safe_mode)

    def _handle_shutdown(self, _: ParsedCommand) -> str:
        return shutdown_computer(self.config.safe_mode)

    def _handle_exit(self, _: ParsedCommand) -> str:
        return 'Cerrando JarvisAI.'

    def _handle_web_search(self, command: ParsedCommand) -> str:
        return web_search(command.metadata.get('query', ''))

    def _handle_youtube(self, command: ParsedCommand) -> str:
        return self.youtube.search(command.metadata['query'], play=command.metadata['play'] == '1')

    def _handle_youtube_control(self, command: ParsedCommand) -> str:
        return self.youtube.control(command.entity)

    def _handle_important_email(self, command: ParsedCommand) -> str:
        return self.gmail.important(unread=command.metadata.get('unread') == '1')

    def _handle_connect_gmail(self, _: ParsedCommand) -> str:
        return self.gmail.connect()

    def _handle_list_windows(self, _: ParsedCommand) -> str:
        windows = list_windows()[:10]
        if not windows:
            return 'No encontré ventanas de otros programas.'
        return 'Ventanas abiertas:\n' + '\n'.join(f'• {window.title}' for window in windows)

    def _handle_unknown(self, command: ParsedCommand) -> str:
        if self._chat_client is not None:
            try:
                response = self._chat_client.ask(command.raw_text, history=self._chat_history[-10:])
            except ChatError as exc:
                self.logger.warning('Error de IA (%s): %s', self.config.ai_provider, exc)
                return f'No pude consultar la IA. {exc}'

            self._chat_history.extend([
                {'role': 'user', 'text': command.raw_text},
                {'role': 'model', 'text': response},
            ])
            del self._chat_history[:-10]
            return response

        suggestions = self.memory_manager.suggest_commands(command.raw_text)
        if suggestions:
            suggestions_text = ', '.join(suggestions)
            return f'No entendi ese comando todavia. Quizas quisiste decir: {suggestions_text}.'

        examples = ', '.join(UNKNOWN_COMMAND_SUGGESTIONS)
        return f'No entendi ese comando todavia. Prueba con: {examples}.'

    def _build_search_roots(self) -> list[Path]:
        home = Path.home()
        roots = [
            *(Path(value.strip()).expanduser() for value in os.environ.get('JARVIS_SEARCH_ROOTS', '').split(';') if value.strip()),
            *(home / folder for folder in ('Documents', 'Downloads', 'Desktop', 'Pictures', 'Videos')),
            *(Path(os.environ[key]) for key in ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial') if os.environ.get(key)),
            self.config.root_dir,
            *(Path(value) for value in self.config.path_aliases.values()),
            home,
        ]

        seen: set[Path] = set()
        unique_roots: list[Path] = []
        for root in roots:
            resolved = root.resolve(strict=False)
            if resolved in seen:
                continue
            seen.add(resolved)
            unique_roots.append(resolved)
        return unique_roots

    def _app_display_name(self, entity: str) -> str:
        primary_target = self.config.app_targets.get(entity, '')
        if primary_target and primary_target in FRIENDLY_TARGET_LABELS:
            return FRIENDLY_TARGET_LABELS[primary_target]

        web_target = self.config.app_web_targets.get(entity, '')
        if web_target and web_target in FRIENDLY_TARGET_LABELS:
            return FRIENDLY_TARGET_LABELS[web_target]

        builtin = BUILTIN_APP_COMMANDS.get(entity)
        if builtin is not None:
            return builtin.label
        return entity.replace('_', ' ').strip()

    def _web_display_name(self, display_name: str) -> str:
        base_name = display_name.strip()
        if not base_name:
            return 'sitio web'
        if base_name.lower().endswith(' web'):
            return base_name
        return f'{base_name} web'
