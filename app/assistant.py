from __future__ import annotations

from time import perf_counter

from app.actions.system_actions import build_confirmation_prompt
from app.brain.intents import Intent, ParsedCommand
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
        self.memory_manager = MemoryManager(config.aliases_path, config.history_path)
        self.memory_manager.ensure_database()
        self._refresh_runtime_state()

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

            if self.state.pending_confirmation is not None:
                should_break = self._handle_pending_confirmation(raw_text)
                if should_break:
                    break
                continue

            parsed = self.parser.parse(raw_text)

            if parsed.intent in {Intent.RESTART_COMPUTER, Intent.SHUTDOWN_COMPUTER}:
                self.state.pending_confirmation = parsed
                action = "restart" if parsed.intent is Intent.RESTART_COMPUTER else "shutdown"
                response = build_confirmation_prompt(action)
                self.state.last_response = response
                self.state.status = "waiting_confirmation"
                print(response)
                continue

            response, duration_ms = self._execute_command(parsed)
            print(response)

            if parsed.intent in {Intent.LEARN_ALIAS, Intent.REPLACE_ALIAS}:
                self._refresh_runtime_state()

            if parsed.intent is Intent.EXIT:
                break

    def _handle_pending_confirmation(self, raw_text: str) -> bool:
        decision = self.parser.parse(raw_text)
        pending = self.state.pending_confirmation
        assert pending is not None

        if decision.intent is Intent.CONFIRM:
            response, duration_ms = self._execute_command(pending)
            print(response)
            self.state.pending_confirmation = None
            return False

        if decision.intent in {Intent.CANCEL, Intent.EXIT}:
            response = "Accion cancelada por el usuario."
            self.memory_manager.record_history(
                raw_text=pending.raw_text,
                normalized_text=pending.normalized_text,
                intent=pending.intent.value,
                entity=pending.entity,
                source=pending.metadata.get("source", "system"),
                response=response,
                duration_ms=0,
            )
            self.state.last_response = response
            self.state.status = "idle"
            self.state.pending_confirmation = None
            print(response)
            return False

        response = "Tienes una accion sensible pendiente. Responde si o no."
        self.state.last_response = response
        self.state.status = "waiting_confirmation"
        print(response)
        return False

    def _execute_command(self, parsed: ParsedCommand) -> tuple[str, int]:
        started_at = perf_counter()
        response = self.router.handle(parsed)
        duration_ms = int((perf_counter() - started_at) * 1000)
        self.memory_manager.record_history(
            raw_text=parsed.raw_text,
            normalized_text=parsed.normalized_text,
            intent=parsed.intent.value,
            entity=parsed.entity,
            source=parsed.metadata.get("source", self._infer_source(parsed)),
            response=response,
            duration_ms=duration_ms,
        )
        self.state.last_response = response
        self.state.status = "idle"
        return response, duration_ms

    def _refresh_runtime_state(self) -> None:
        aliases = self.memory_manager.load_aliases()
        self.memory_manager.sync_command_catalog(self.config.path_aliases, self.config.app_targets, aliases)
        self.parser = CommandParser(
            custom_paths=aliases["custom_paths"],
            custom_apps=aliases["custom_apps"],
        )
        self.router = CommandRouter(config=self.config, logger=self.logger, memory_manager=self.memory_manager)

    def _infer_source(self, parsed: ParsedCommand) -> str:
        if parsed.intent in {Intent.GET_TIME, Intent.GET_DATE, Intent.LIST_COMMANDS, Intent.SHOW_METRICS, Intent.EXIT}:
            return "system"
        if parsed.intent in {Intent.LEARN_ALIAS, Intent.REPLACE_ALIAS}:
            return "alias_management"
        if parsed.intent in {Intent.RESTART_COMPUTER, Intent.SHUTDOWN_COMPUTER}:
            return "dangerous"
        if parsed.intent is Intent.OPEN_PATH:
            return "builtin_path"
        if parsed.intent is Intent.OPEN_APP:
            return "builtin_app"
        return "unknown"

    def _print_banner(self) -> None:
        print(f"{self.config.app_name} listo.")
        print("Modo actual: texto")
        print("Prueba frases como: jarvis, hora | jarvis abre documentos | jarvis aprende que reportes abre D:\\Reportes")
