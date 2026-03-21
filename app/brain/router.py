from __future__ import annotations

import logging

from app.actions.app_actions import open_application
from app.actions.file_actions import open_path
from app.actions.system_actions import get_current_date, get_current_time, restart_computer, shutdown_computer
from app.brain.intents import Intent, ParsedCommand
from app.config import AppConfig
from app.memory.memory_manager import MemoryManager


class CommandRouter:
    def __init__(self, config: AppConfig, logger: logging.Logger, memory_manager: MemoryManager) -> None:
        self.config = config
        self.logger = logger
        self.memory_manager = memory_manager

    def handle(self, command: ParsedCommand) -> str:
        self.logger.info("Received command: %s", command.raw_text)

        if command.intent is Intent.OPEN_PATH:
            target = command.metadata.get("target") or self.config.path_aliases.get(command.entity, "")
            response = open_path(target)
        elif command.intent is Intent.OPEN_APP:
            target = command.metadata.get("target") or self.config.app_targets.get(command.entity, "")
            response = open_application(target)
        elif command.intent is Intent.GET_TIME:
            response = get_current_time()
        elif command.intent is Intent.GET_DATE:
            response = get_current_date()
        elif command.intent is Intent.LIST_COMMANDS:
            response = self.memory_manager.render_command_summary()
        elif command.intent is Intent.SHOW_METRICS:
            response = self.memory_manager.render_metrics_summary()
        elif command.intent is Intent.LEARN_ALIAS:
            response = self.memory_manager.save_alias(
                alias_kind=command.metadata["alias_kind"],
                label=command.metadata["label"],
                target=command.metadata["target"],
                replace=False,
            )["message"]
        elif command.intent is Intent.REPLACE_ALIAS:
            response = self.memory_manager.save_alias(
                alias_kind=command.metadata["alias_kind"],
                label=command.metadata["label"],
                target=command.metadata["target"],
                replace=True,
            )["message"]
        elif command.intent is Intent.RESTART_COMPUTER:
            response = restart_computer(self.config.safe_mode)
        elif command.intent is Intent.SHUTDOWN_COMPUTER:
            response = shutdown_computer(self.config.safe_mode)
        elif command.intent is Intent.EXIT:
            response = "Cerrando JarvisAI."
        else:
            response = self._build_unknown_response()

        self.logger.info("Assistant response: %s", response)
        return response

    def _build_unknown_response(self) -> str:
        examples = "hora, fecha, documentos, editor, comandos, metricas, salir"
        return f"No entendi ese comando todavia. Prueba con: {examples}."
