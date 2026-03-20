from __future__ import annotations

from app.brain.parser import CommandParser
from app.brain.router import CommandRouter
from app.config import AppConfig
from app.memory.memory_manager import MemoryManager
from app.state import AssistantState
from app.utils.logger import build_logger


class JarvisAssistant:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.state = AssistantState()
        self.logger = build_logger(config)

        memory_manager = MemoryManager(config.aliases_path)
        aliases = memory_manager.load_aliases()

        self.parser = CommandParser(
            custom_paths=aliases["custom_paths"],
            custom_apps=aliases["custom_apps"],
        )
        self.router = CommandRouter(config=config, logger=self.logger)

    @classmethod
    def from_env(cls) -> "JarvisAssistant":
        config = AppConfig.load()
        config.ensure_runtime_paths()
        return cls(config=config)

    def run(self) -> None:
        self.logger.info("Starting %s in %s mode", self.config.app_name, self.config.input_mode)
        self._print_banner()

        if self.config.input_mode != "text":
            print("Voice mode is reserved for the next step. Use text mode for now.")
            return

        self._run_text_loop()

    def _run_text_loop(self) -> None:
        while True:
            self.state.status = "listening"
            raw_text = input("Tu comando > ").strip()

            if not raw_text:
                continue

            self.state.last_command = raw_text
            self.state.status = "processing"

            parsed = self.parser.parse(raw_text)
            response = self.router.handle(parsed)

            self.state.last_response = response
            self.state.status = "idle"
            print(response)

            if parsed.intent.value == "exit":
                break

    def _print_banner(self) -> None:
        print(f"{self.config.app_name} listo.")
        print("Modo actual: texto")
        print("Prueba comandos como: hora, fecha, documentos, abre chrome, salir")
