from __future__ import annotations

import logging
from collections.abc import Callable

from app.actions.app_actions import open_application
from app.actions.file_actions import open_path
from app.actions.system_actions import get_current_date, get_current_time, restart_computer, shutdown_computer
from app.brain.command_catalog import UNKNOWN_COMMAND_SUGGESTIONS
from app.brain.intents import Intent, ParsedCommand
from app.config import AppConfig
from app.memory.memory_manager import MemoryManager


class CommandRouter:
    """Conecta una intencion ya entendida con la accion concreta a ejecutar."""

    def __init__(self, config: AppConfig, logger: logging.Logger, memory_manager: MemoryManager) -> None:
        self.config = config
        self.logger = logger
        self.memory_manager = memory_manager

        # Usamos un mapa de handlers para que la relacion intent -> accion
        # sea facil de leer y de extender.
        self._handlers: dict[Intent, Callable[[ParsedCommand], str]] = {
            Intent.OPEN_PATH: self._handle_open_path,
            Intent.OPEN_APP: self._handle_open_app,
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
        self.logger.info('Received command: %s', command.raw_text)
        handler = self._handlers.get(command.intent, self._handle_unknown)
        response = handler(command)
        self.logger.info('Assistant response: %s', response)
        return response

    def _handle_open_path(self, command: ParsedCommand) -> str:
        target = command.metadata.get('target') or self.config.path_aliases.get(command.entity, '')
        return open_path(target)

    def _handle_open_app(self, command: ParsedCommand) -> str:
        target = command.metadata.get('target') or self.config.app_targets.get(command.entity, '')
        return open_application(target)

    def _handle_get_time(self, _: ParsedCommand) -> str:
        return get_current_time()

    def _handle_get_date(self, _: ParsedCommand) -> str:
        return get_current_date()

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

    def _handle_unknown(self, _: ParsedCommand) -> str:
        examples = ', '.join(UNKNOWN_COMMAND_SUGGESTIONS)
        return f'No entendi ese comando todavia. Prueba con: {examples}.'
