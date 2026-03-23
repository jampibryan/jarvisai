from __future__ import annotations

from time import perf_counter

from app.actions.system_actions import build_confirmation_prompt
from app.brain.command_catalog import HUMAN_COMMAND_GUIDE
from app.brain.intents import Intent, ParsedCommand
from app.brain.parser import CommandParser
from app.brain.router import CommandRouter
from app.config import AppConfig
from app.memory.memory_manager import MemoryManager
from app.state import AssistantState
from app.utils.logger import build_logger
from app.voice.listener import VoiceListener
from app.voice.recognizer import SpeechRecognizer
from app.voice.speaker import Speaker


class JarvisAssistant:
    """Coordina texto, voz, memoria y ejecucion de comandos."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.state = AssistantState()
        self.logger = build_logger(config)
        self.memory_manager = MemoryManager(config.aliases_path, config.history_path)
        self.memory_manager.ensure_database()
        self.listener = VoiceListener()
        self.speech_recognizer = SpeechRecognizer(language=config.language)
        self.speaker = Speaker(preferred_gender='male')
        self._refresh_runtime_state()

    @classmethod
    def from_env(cls) -> 'JarvisAssistant':
        config = AppConfig.load()
        config.ensure_runtime_paths()
        return cls(config=config)

    def run(self, mode: str | None = None) -> None:
        selected_mode = mode or self.config.input_mode
        self.state.current_mode = selected_mode
        self.logger.info('Starting %s in %s mode', self.config.app_name, selected_mode)
        self._print_banner(selected_mode)

        if selected_mode == 'voice':
            self._run_voice_loop()
            return

        self._run_text_loop()

    def _run_text_loop(self) -> None:
        while True:
            raw_text = input('Tu comando > ').strip()
            if not raw_text:
                continue
            should_exit = self._process_command(raw_text)
            if should_exit:
                break

    def _run_voice_loop(self) -> None:
        if not self.listener.available or not self.speech_recognizer.available:
            print('El modo voz necesita SpeechRecognition y PyAudio instalados en el entorno virtual.')
            return

        devices = self._get_microphone_names()
        if not devices:
            print('No encontre dispositivos de entrada de audio. Usa el modo texto por ahora.')
            return

        if not self.speaker.available:
            print('Aviso: la voz sintetizada no esta disponible en este entorno. Seguiremos mostrando texto.')

        while True:
            raw_entry = input('Enter para hablar | escribe un comando > ').strip()

            if raw_entry:
                should_exit = self._process_command(raw_entry, speak_response=True)
                if should_exit:
                    break
                continue

            try:
                print('Escuchando...')
                audio = self.listener.listen_once()
                transcript = self.speech_recognizer.transcribe(audio)
                print(f'Escuche: {transcript}')
            except Exception as exc:
                message = str(exc)
                lowered_message = message.lower()

                if 'wait time' in lowered_message or 'listening timed out' in lowered_message:
                    print('No detecte voz a tiempo. Intenta otra vez.')
                    continue
                if 'understand audio' in lowered_message or 'unknownvalueerror' in lowered_message:
                    print('No pude entender lo que dijiste. Intenta otra vez.')
                    continue
                if 'requesterror' in lowered_message or 'remote end closed connection' in lowered_message:
                    print(f'El servicio de reconocimiento no respondio: {message}')
                    continue

                print(f'No pude usar el microfono: {message}')
                continue

            should_exit = self._process_command(transcript, speak_response=True)
            if should_exit:
                break

    def _process_command(self, raw_text: str, speak_response: bool = False) -> bool:
        self.state.status = 'processing'
        self.state.last_command = raw_text

        if self.state.pending_confirmation is not None:
            return self._handle_pending_confirmation(raw_text, speak_response=speak_response)

        parsed = self.parser.parse(raw_text)

        # El estado del asistente se construye con informacion viva del runtime,
        # por eso lo resolvemos aqui y no en el router.
        if parsed.intent is Intent.SHOW_STATUS:
            response = self._build_runtime_status()
            self._record_response(parsed, response, duration_ms=0)
            self._emit_response(response, speak_response)
            return False

        if (
            parsed.intent in {Intent.RESTART_COMPUTER, Intent.SHUTDOWN_COMPUTER}
            and self.config.confirm_dangerous_actions
        ):
            self.state.pending_confirmation = parsed
            action = 'restart' if parsed.intent is Intent.RESTART_COMPUTER else 'shutdown'
            response = build_confirmation_prompt(action, heard_text=parsed.raw_text, safe_mode=self.config.safe_mode)
            self.state.last_response = response
            self.state.status = 'waiting_confirmation'
            self._emit_response(response, speak_response)
            return False

        response, _duration_ms = self._execute_command(parsed)
        self._emit_response(response, speak_response)

        if parsed.intent in {Intent.LEARN_ALIAS, Intent.REPLACE_ALIAS}:
            self._refresh_runtime_state()

        return parsed.intent is Intent.EXIT

    def _handle_pending_confirmation(self, raw_text: str, speak_response: bool = False) -> bool:
        decision = self.parser.parse(raw_text)
        pending = self.state.pending_confirmation
        assert pending is not None

        if decision.intent is Intent.CONFIRM:
            self.state.pending_confirmation = None
            response, _duration_ms = self._execute_command(pending)
            self._emit_response(response, speak_response)
            return False

        if decision.intent in {Intent.CANCEL, Intent.EXIT}:
            response = 'Accion cancelada por el usuario.'
            self.memory_manager.record_history(
                raw_text=pending.raw_text,
                normalized_text=pending.normalized_text,
                intent=pending.intent.value,
                entity=pending.entity,
                source=pending.metadata.get('source', 'system'),
                response=response,
                duration_ms=0,
            )
            self.state.last_response = response
            self.state.status = 'idle'
            self.state.pending_confirmation = None
            self._emit_response(response, speak_response)
            return False

        response = 'Tienes una accion sensible pendiente. Responde si o no.'
        self.state.last_response = response
        self.state.status = 'waiting_confirmation'
        self._emit_response(response, speak_response)
        return False

    def _execute_command(self, parsed: ParsedCommand) -> tuple[str, int]:
        started_at = perf_counter()
        response = self.router.handle(parsed)
        duration_ms = int((perf_counter() - started_at) * 1000)
        self._record_response(parsed, response, duration_ms)
        return response, duration_ms

    def _record_response(self, parsed: ParsedCommand, response: str, duration_ms: int) -> None:
        self.memory_manager.record_history(
            raw_text=parsed.raw_text,
            normalized_text=parsed.normalized_text,
            intent=parsed.intent.value,
            entity=parsed.entity,
            source=parsed.metadata.get('source', self._infer_source(parsed)),
            response=response,
            duration_ms=duration_ms,
        )
        self.state.last_response = response
        self.state.status = 'idle'

    def _emit_response(self, response: str, speak_response: bool) -> None:
        print(response)
        should_speak = self.config.enable_tts or speak_response
        if should_speak:
            self.speaker.speak(response)

    def _refresh_runtime_state(self) -> None:
        aliases = self.memory_manager.load_aliases()
        self.memory_manager.sync_command_catalog(self.config.path_aliases, self.config.app_targets, aliases)
        self.parser = CommandParser(
            custom_paths=aliases['custom_paths'],
            custom_apps=aliases['custom_apps'],
        )
        self.router = CommandRouter(config=self.config, logger=self.logger, memory_manager=self.memory_manager)

    def _infer_source(self, parsed: ParsedCommand) -> str:
        if parsed.intent in {
            Intent.GET_TIME,
            Intent.GET_DATE,
            Intent.LIST_COMMANDS,
            Intent.SHOW_METRICS,
            Intent.SHOW_STATUS,
            Intent.EXIT,
        }:
            return 'system'
        if parsed.intent in {Intent.LEARN_ALIAS, Intent.REPLACE_ALIAS}:
            return 'alias_management'
        if parsed.intent in {Intent.RESTART_COMPUTER, Intent.SHUTDOWN_COMPUTER}:
            return 'dangerous'
        if parsed.intent is Intent.OPEN_PATH:
            return 'builtin_path'
        if parsed.intent is Intent.OPEN_APP:
            return 'builtin_app'
        return 'unknown'

    def _get_microphone_names(self) -> list[str]:
        try:
            return self.listener.list_devices()
        except Exception:
            return []

    def _build_runtime_status(self) -> str:
        aliases = self.memory_manager.load_aliases()
        commands_count = len(self.memory_manager.list_commands())
        microphones = self._get_microphone_names()
        custom_aliases = len(aliases['custom_paths']) + len(aliases['custom_apps'])
        voice_gender = self.speaker.selected_voice_gender.upper() if self.speaker.selected_voice_gender else 'UNKNOWN'
        voice_name = self.speaker.selected_voice_name or 'predeterminada'

        lines = [
            'Estado actual de JarvisAI:',
            f'- Modo: {self.state.current_mode}',
            f"- Safe mode: {'ON' if self.config.safe_mode else 'OFF'}",
            f"- Confirmacion de acciones sensibles: {'ON' if self.config.confirm_dangerous_actions else 'OFF'}",
            f"- TTS habilitado: {'SI' if self.config.enable_tts else 'NO'}",
            f'- Comandos registrados: {commands_count}',
            f'- Alias personalizados: {custom_aliases}',
            f"- Voz disponible: {'SI' if self.listener.available and self.speech_recognizer.available else 'NO'}",
            f'- Microfonos detectados: {len(microphones)}',
            f"- TTS disponible: {'SI' if self.speaker.available else 'NO'}",
            f'- Voz TTS seleccionada: {voice_name} ({voice_gender})',
            '- Reconocimiento de voz actual: Google online',
        ]

        if self.state.current_mode == 'voice':
            lines.append('- Activacion por tecla: presiona Enter para escuchar una orden.')

        return '\n'.join(lines)

    def _print_banner(self, mode: str) -> None:
        microphones = self._get_microphone_names()
        commands_count = len(self.memory_manager.list_commands())
        examples = ' | '.join(HUMAN_COMMAND_GUIDE[:6])
        voice_gender = self.speaker.selected_voice_gender.upper() if self.speaker.selected_voice_gender else 'UNKNOWN'
        voice_name = self.speaker.selected_voice_name or 'predeterminada'

        print(f'{self.config.app_name} listo.')
        print(f'Modo actual: {mode}')
        print('Diagnostico inicial:')
        print(f"- Safe mode: {'ON' if self.config.safe_mode else 'OFF'}")
        print(f"- Confirmacion sensible: {'ON' if self.config.confirm_dangerous_actions else 'OFF'}")
        print(f"- TTS habilitado: {'SI' if self.config.enable_tts else 'NO'}")
        print(f'- Comandos disponibles: {commands_count}')
        print(f"- Voz disponible: {'SI' if self.listener.available and self.speech_recognizer.available else 'NO'}")
        print(f'- Microfonos detectados: {len(microphones)}')
        print(f"- TTS disponible: {'SI' if self.speaker.available else 'NO'}")
        print(f'- Voz TTS seleccionada: {voice_name} ({voice_gender})')
        if mode == 'voice':
            print('- Activacion por tecla: Enter para hablar.')
        print(f'Prueba frases como: {examples}')
