from __future__ import annotations

import logging

from app.actions.app_actions import open_application
from app.actions.file_actions import open_path
from app.actions.system_actions import get_current_date, get_current_time
from app.brain.intents import Intent, ParsedCommand
from app.config import AppConfig


class CommandRouter:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger

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
        elif command.intent is Intent.EXIT:
            response = "Cerrando JarvisAI."
        else:
            response = self._build_unknown_response()

        self.logger.info("Assistant response: %s", response)
        return response

    def _build_unknown_response(self) -> str:
        examples = "hora, fecha, documentos, abre chrome, salir"
        return f"No entendi ese comando todavia. Prueba con: {examples}."
