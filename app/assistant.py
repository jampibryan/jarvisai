from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Event
from time import monotonic, perf_counter

from app.actions.file_actions import open_path
from app.actions.selected_files import FileActionError, FilePlan, execute_file_plan
from app.actions.system_actions import build_confirmation_prompt
from app.actions.window_actions import WindowActionError, execute_window_close, prepare_window_close
from app.brain.command_catalog import HUMAN_COMMAND_GUIDE
from app.brain.intents import Intent, ParsedCommand
from app.brain.parser import CommandParser
from app.brain.router import CommandRouter
from app.config import AppConfig
from app.integrations.youtube_player import YouTubePlayer
from app.memory.memory_manager import MemoryManager
from app.state import AssistantState
from app.utils.logger import build_logger
from app.voice.listener import VoiceCaptureInterrupted, VoiceListener
from app.voice.recognizer import SpeechRecognizer
from app.voice.speaker import Speaker


class JarvisAssistant:
    """Coordina texto, voz, memoria y ejecucion de comandos."""

    def __init__(
        self, config: AppConfig, *, on_event: Callable[[str, str], None] | None = None,
        stop_event: Event | None = None, microphone_changes: SimpleQueue[int | None] | None = None,
        voice_controls: SimpleQueue[tuple[str, str]] | None = None,
        microphone_paused: Event | None = None,
    ) -> None:
        self.config = config
        self._on_event = on_event
        self._speech_failed = False
        self._stop = stop_event if stop_event is not None else Event()
        self._microphone_changes = microphone_changes
        self._voice_controls = voice_controls
        self._microphone_paused = microphone_paused
        self.state = AssistantState()
        self.logger = build_logger(config)
        self.memory_manager = MemoryManager(config.aliases_path, config.history_path)
        self.memory_manager.ensure_database()
        self.listener = VoiceListener(
            timeout=config.voice_timeout,
            phrase_time_limit=config.voice_phrase_time_limit,
            ambient_duration=config.voice_ambient_duration,
            pause_threshold=config.voice_pause_threshold,
            non_speaking_duration=config.voice_non_speaking_duration,
            dynamic_energy_threshold=config.voice_dynamic_energy_threshold,
            energy_threshold=config.voice_energy_threshold,
        )
        self.speech_recognizer = SpeechRecognizer(
            language=config.language,
            enable_offline_fallback=config.voice_offline_fallback,
            engine=config.voice_engine,
            whisper_path=config.aliases_path.parent / 'whisper-base',
        )
        self.speaker = Speaker(preferred_gender='male', preferred_rate=config.voice_rate, preferred_language=config.language)
        if on_event is not None:
            self.speaker.on_word = lambda: self._notify('speech_pulse', '')
        self._chat_history: list[dict[str, str]] = []
        self.youtube = YouTubePlayer(config.aliases_path.parent / 'youtube-browser')
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

        try:
            if selected_mode == 'voice':
                self._run_voice_loop()
            else:
                self._run_text_loop()
        finally:
            self.youtube.close()

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
            self._report_voice_issue('El modo voz necesita SpeechRecognition y PyAudio.')
            if self._voice_controls is not None:
                while not self._stop.is_set() and not self._apply_voice_controls():
                    self._stop.wait(0.15)
            return

        if self.config.enable_tts and not self.speaker.available:
            print('Aviso: la voz sintetizada no esta disponible en este entorno. Seguiremos mostrando texto.')

        continuous = self.config.voice_continuous
        if continuous:
            wake_prefix = f'{self.config.voice_wake_word}, ' if self.config.voice_require_wake_word else ''
            print(f'Modo manos libres. Di «{wake_prefix}hora» para probar o «{wake_prefix}salir» para cerrar.')

        from app.voice.listener import sr
        assert sr is not None

        calibrated = False
        greeted = False
        microphone_unavailable = False
        recognition_unavailable = False
        while not self._stop.is_set():
            if self._apply_voice_controls():
                break
            if self._microphone_paused is not None and self._microphone_paused.is_set():
                self._notify('state', 'Micrófono en pausa')
                self._stop.wait(0.15)
                continue
            if self._microphone_changes is not None:
                try:
                    self.listener.device_index = self._microphone_changes.get_nowait()
                    calibrated = False
                    microphone_unavailable = False
                except Empty:
                    pass
            if not calibrated:
                try:
                    self._notify('state', 'Calibrando micrófono')
                    self.listener.calibrate()
                    calibrated = True
                except (OSError, RuntimeError, AttributeError, ValueError) as exc:
                    if not microphone_unavailable:
                        self.logger.warning('No pude inicializar el micrófono: %s', exc)
                        self._report_voice_issue('Micrófono no disponible. Reintentando…')
                    microphone_unavailable = True
                    self._stop.wait(2)
                    continue

            if continuous and not greeted:
                wake_word = self.config.voice_wake_word.capitalize()
                greeting = f'Hola, soy Jarvis. Di {wake_word} y cuéntame qué necesitas.' if self.config.voice_require_wake_word else 'Hola, soy Jarvis. Te escucho.'
                self._emit_response(greeting)
                greeted = True

            if not continuous:
                raw_entry = input('Enter para hablar | escribe un comando > ').strip()
                if raw_entry:
                    if self._process_command(raw_entry):
                        break
                    continue

            listening = 'Escuchando'
            if self.state.pending_confirmation is not None and monotonic() < self.state.confirmation_deadline:
                listening = 'Esperando confirmación'
            elif monotonic() < self.state.search_query_deadline:
                listening = 'Esperando el nombre del archivo'
            elif monotonic() < self.state.command_followup_deadline:
                listening = 'Esperando el resto de tu frase'
            self._notify('state', listening)
            try:
                # The microphone closes before transcription and speech synthesis.
                audio = self.listener.listen_once(
                    calibrate=False, interrupt=self._voice_control_pending,
                    on_level=self._report_microphone_level if self._on_event is not None else None,
                )
                microphone_unavailable = False
            except VoiceCaptureInterrupted:
                continue
            except sr.WaitTimeoutError:
                if not continuous:
                    print('No detecté voz a tiempo. Intenta otra vez.')
                continue
            except (OSError, RuntimeError, AttributeError, ValueError) as exc:
                if not microphone_unavailable:
                    self.logger.warning('No pude usar el micrófono: %s', exc)
                    self._report_voice_issue('Se interrumpió el micrófono. Reintentando…')
                microphone_unavailable = True
                calibrated = False
                self._stop.wait(2)
                continue

            if self._voice_control_pending():
                continue
            try:
                self._notify('state', 'Reconociendo tu voz')
                transcript = self.speech_recognizer.transcribe(audio)
                recognition_unavailable = False
            except sr.UnknownValueError:
                if not continuous:
                    print('No pude entender lo que dijiste. Intenta otra vez.')
                continue
            except (sr.RequestError, OSError, RuntimeError, ValueError) as exc:
                if not recognition_unavailable:
                    self.logger.warning('Transcripción temporalmente no disponible: %s', exc)
                    self._report_voice_issue('La transcripción falló. Reintentando…')
                recognition_unavailable = True
                self._stop.wait(1)
                continue

            voice_command, feedback = self._prepare_voice_command(transcript)
            if voice_command is None:
                if feedback and (not continuous or monotonic() < self.state.voice_activation_deadline):
                    self._emit_response(feedback)
                    if self.state.voice_activation_deadline:
                        self.state.voice_activation_deadline = monotonic() + 10
                continue

            if self._stop.is_set():
                break
            self._notify('command', voice_command)
            print(f'[Jarvis] Escuchado: {voice_command}')
            try:
                if self._process_command(voice_command):
                    break
            except Exception:
                self.logger.exception('Error al procesar un comando de voz')
                self.state.pending_confirmation = None
                self.state.pending_file_plan = None
                self.state.pending_window_plan = None
                self._emit_response('Hubo un problema con esa orden. Sigo escuchando.')

    def _notify(self, kind: str, message: str) -> None:
        if self._on_event is not None:
            self._on_event(kind, message)

    def _report_voice_issue(self, message: str) -> None:
        print(message)
        self._notify('state', message)

    def _report_microphone_level(self, level: float) -> None:
        self._notify('mic_level', f'{level:.3f}')

    def _voice_control_pending(self) -> bool:
        return (
            self._stop.is_set()
            or (self._voice_controls is not None and not self._voice_controls.empty())
            or (self._microphone_changes is not None and not self._microphone_changes.empty())
            or (self._microphone_paused is not None and self._microphone_paused.is_set())
        )

    def _apply_voice_controls(self) -> bool:
        if self._voice_controls is None:
            return False
        while not self._stop.is_set():
            try:
                action, value = self._voice_controls.get_nowait()
            except Empty:
                break
            try:
                if action == 'voice':
                    self.speaker.configure(voice_id=value)
                elif action == 'style':
                    self.speaker.configure(style=value)
                elif action == 'preview':
                    self._emit_response('Así suena mi voz con este estilo. ¿En qué te ayudo hoy?')
                elif action == 'command':
                    self._notify('command', value)
                    if self._process_command(value):
                        return True
                elif action in {'open_attachment', 'preview_attachment'}:
                    self._handle_attachment(Path(value), preview=action == 'preview_attachment')
            except Exception:
                self.logger.exception('Error al procesar un control de escritorio')
                self._emit_response('No pude completar ese cambio. Puedes intentarlo otra vez.')
        return False

    def _handle_attachment(self, path: Path, *, preview: bool) -> None:
        if not path.is_file():
            self._emit_response('Ese adjunto ya no está disponible.')
            return
        if preview:
            if path.suffix.lower() not in {'.txt', '.md', '.csv', '.json', '.log'}:
                self._emit_response('La vista previa local admite archivos de texto. Puedes abrir este adjunto en su aplicación.')
                return
            self._notify('state', 'Analizando documento')
            with path.open(encoding='utf-8-sig', errors='replace') as source:
                sample = source.read(1601)
            suffix = '\n\nVista previa limitada a los primeros 1600 caracteres.' if len(sample) > 1600 else ''
            self._emit_response(f'{path.name}\n\n{sample[:1600]}{suffix}', speech=f'Aquí tienes la vista previa de {path.name}.')
            return
        if path.suffix.lower() not in {'.txt', '.md', '.csv', '.json', '.log', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
                                       '.ppt', '.pptx', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp3', '.wav', '.mp4'}:
            self._emit_response('Este tipo de adjunto se puede abrir directamente desde el Explorador.')
            return
        response = open_path(str(path))
        self._emit_response(response, speech=f'Abriendo {path.name}.' if response.startswith('Abriendo') else response)

    def _process_command(self, raw_text: str) -> bool:
        self.state.status = 'processing'
        self._notify('state', 'Procesando')
        self.state.last_command = raw_text

        if self.state.pending_confirmation is not None:
            return self._handle_pending_confirmation(raw_text)

        if self._on_event is not None and monotonic() >= self.state.search_query_deadline:
            normalized = self.parser._normalize(self.parser._strip_assistant_prefix(raw_text)).strip('.')
            panel = next((name for name, phrases in {
                'agenda': {'agenda', 'mi agenda', 'muestra mi agenda'},
                'tasks': {'mis tareas', 'muestra mis tareas', 'mis notas'},
                'projects': {'mis proyectos', 'muestra mis proyectos'},
                'automations': {'automatizaciones', 'mis automatizaciones'},
            }.items() if normalized in phrases), None)
            if panel:
                self._notify('panel', panel)
                self.state.status = 'idle'
                return False

        parsed = self.parser.parse(raw_text)
        prefix = self.state.command_followup_prefix
        if prefix and monotonic() < self.state.command_followup_deadline and parsed.intent in {
            Intent.UNKNOWN, Intent.OPEN_APP, Intent.OPEN_PATH,
        }:
            normalized_reply = self.parser._normalize(self.parser._strip_assistant_prefix(raw_text))
            if not re.match(r'^(?:abre|pon|busca|reproduce)\b', normalized_reply):
                parsed = self.parser.parse(f'{prefix} {raw_text}')
        self.state.command_followup_prefix = ''
        self.state.command_followup_deadline = 0
        if parsed.intent is Intent.CLARIFY_COMMAND:
            is_open = parsed.entity == 'open'
            response = '¿Qué quieres que abra?' if is_open else '¿Qué canción o video quieres en YouTube?'
            self.state.last_response = response
            self._emit_response(response)
            self.state.status = 'idle'
            self.state.command_followup_prefix = 'abre' if is_open else 'reproduce'
            self.state.command_followup_deadline = monotonic() + 15
            return False
        awaiting_name = monotonic() < self.state.search_query_deadline if self.state.search_query_deadline else False
        self.state.search_query_deadline = 0
        if awaiting_name and parsed.intent is Intent.UNKNOWN:
            parsed = self.parser.parse(f'busca el archivo llamado {raw_text}')

        if parsed.intent is Intent.SEARCH_FILE:
            self._process_file_search(parsed)
            return False
        if parsed.intent is Intent.OPEN_SEARCH_RESULT:
            self._open_search_result(parsed)
            return False

        if parsed.intent is Intent.FILE_SELECTION:
            self._process_file_selection(parsed)
            return False
        if parsed.intent is Intent.CLOSE_WINDOW:
            self._process_window_close(parsed)
            return False

        # El estado del asistente se construye con informacion viva del runtime,
        # por eso lo resolvemos aqui y no en el router.
        if parsed.intent is Intent.SHOW_STATUS:
            response = self._build_runtime_status()
            self._record_response(parsed, response, duration_ms=0)
            self._emit_response(response)
            return False

        if (
            parsed.intent in {Intent.RESTART_COMPUTER, Intent.SHUTDOWN_COMPUTER}
            and self.config.confirm_dangerous_actions
        ):
            self.state.pending_confirmation = parsed
            action = 'restart' if parsed.intent is Intent.RESTART_COMPUTER else 'shutdown'
            prompt = build_confirmation_prompt(action, heard_text=parsed.raw_text, safe_mode=self.config.safe_mode)
            response = f'{prompt} {self._confirmation_instructions()} Tienes 30 segundos para confirmar.'
            self.state.last_response = response
            self.state.status = 'waiting_confirmation'
            self._emit_response(response)
            self.state.confirmation_deadline = monotonic() + 30
            return False

        response, _duration_ms = self._execute_command(parsed)
        self._emit_response(response)

        if parsed.intent in {Intent.YOUTUBE, Intent.YOUTUBE_CONTROL}:
            self.state.media_followup_deadline = monotonic() + 30
        elif parsed.intent is Intent.OPEN_APP and parsed.entity == 'youtube':
            self.state.media_followup_deadline = monotonic() + 15

        if parsed.intent in {Intent.LEARN_ALIAS, Intent.REPLACE_ALIAS}:
            self._refresh_runtime_state()

        return parsed.intent is Intent.EXIT

    def _process_window_close(self, command: ParsedCommand) -> None:
        try:
            plan = prepare_window_close(command.entity, tab=command.metadata.get('tab') == '1')
        except WindowActionError as exc:
            self._record_response(command, str(exc), duration_ms=0)
            self._emit_response(str(exc))
            return
        self.state.pending_confirmation = command
        self.state.pending_window_plan = plan
        self.state.status = 'waiting_confirmation'
        response = f'{plan.preview()} {self._confirmation_instructions()} Tienes 30 segundos.'
        self.state.last_response = response
        self._emit_response(response)
        self.state.confirmation_deadline = monotonic() + 30

    def _process_file_search(self, command: ParsedCommand) -> None:
        query = command.metadata['query']
        self.state.search_results = ()
        self.state.search_result_deadline = 0
        if not query:
            self._emit_response('Claro. ¿Cómo se llama el archivo? Puedes decirme solo una parte del nombre.')
            self.state.search_query_deadline = monotonic() + 15
            return

        self._notify('state', 'Buscando archivos')
        started_at = perf_counter()
        result = self.router.find_files(query)
        self.state.search_results = result.paths
        response = result.display()
        self._record_response(command, response, int((perf_counter() - started_at) * 1000))
        self._emit_response(response, speech=result.speech())
        if result.paths:
            self.state.search_result_deadline = monotonic() + 20

    def _open_search_result(self, command: ParsedCommand) -> None:
        paths = self.state.search_results
        index = command.entity
        if not index and len(paths) > 1:
            self._emit_response('Encontré varios archivos. ¿Cuál abro? Puedes decir «abre el primero» o «abre el segundo».')
            self.state.search_result_deadline = monotonic() + 20
            return
        ranks = ('primer', 'segund', 'tercer', 'cuart', 'quint')
        position = int(index) if index.isdigit() else next(
            (number for number, prefix in enumerate(ranks, 1) if index.startswith(prefix)), 1,
        )
        response = open_path(str(paths[position - 1])) if position <= len(paths) else 'No tengo ese resultado. Puedes pedirme otra búsqueda.'
        self._record_response(command, response, duration_ms=0)
        self._emit_response(response, speech=f'Abriendo {paths[position - 1].stem}.' if response.startswith('Abriendo') else response)

    def _process_file_selection(self, command: ParsedCommand) -> None:
        try:
            plan = self.router.prepare_file_action(command)
        except (FileActionError, OSError) as exc:
            response = f'No pude preparar la operación. {exc}'
            self._record_response(command, response, duration_ms=0)
            self._emit_response(response)
            return

        if plan.action == 'open':
            self._run_file_plan(command, plan)
            return

        preview = plan.preview()
        if not self.config.apply_file_changes:
            response = f'Vista previa. {preview}\nPara aplicar cambios, inicia Jarvis con --apply-file-changes.'
            self._record_response(command, response, duration_ms=0)
            self._emit_response(response)
            return

        self.state.pending_confirmation = command
        self.state.pending_file_plan = plan
        self.state.status = 'waiting_confirmation'
        response = f'{preview}\n{self._confirmation_instructions()} Tienes 30 segundos para confirmar.'
        self.state.last_response = response
        self._emit_response(response)
        self.state.confirmation_deadline = monotonic() + 30

    def _run_file_plan(self, command: ParsedCommand, plan: FilePlan) -> None:
        started_at = perf_counter()
        try:
            response = execute_file_plan(plan)
        except (FileActionError, OSError) as exc:
            response = f'No pude completar la operación. {exc}'
        self._record_response(command, response, int((perf_counter() - started_at) * 1000))
        self._emit_response(response)

    def _confirmation_instructions(self) -> str:
        if self.state.current_mode == 'voice' and self.config.voice_require_wake_word:
            wake_word = self.config.voice_wake_word
            return f'Di «{wake_word}, sí» o «{wake_word}, no».'
        return 'Responde si o no.'

    def _handle_pending_confirmation(self, raw_text: str) -> bool:
        decision = self.parser.parse(raw_text)
        pending = self.state.pending_confirmation
        assert pending is not None

        expired = monotonic() >= self.state.confirmation_deadline
        if decision.intent is Intent.CONFIRM and not expired:
            self.state.pending_confirmation = None
            window_plan = self.state.pending_window_plan
            self.state.pending_window_plan = None
            if window_plan is not None:
                try:
                    response = execute_window_close(window_plan)
                except WindowActionError as exc:
                    response = str(exc)
                self._record_response(pending, response, duration_ms=0)
                self._emit_response(response)
                return False
            plan = self.state.pending_file_plan
            self.state.pending_file_plan = None
            if plan is not None:
                self._run_file_plan(pending, plan)
                return False
            response, _duration_ms = self._execute_command(pending)
            self._emit_response(response)
            return False

        if expired or decision.intent in {Intent.CANCEL, Intent.EXIT}:
            response = 'Accion cancelada por tiempo de espera.' if expired else 'Accion cancelada por el usuario.'
            self._record_response(pending, response, duration_ms=0)
            self.state.pending_confirmation = None
            self.state.pending_file_plan = None
            self.state.pending_window_plan = None
            self._emit_response(response)
            if expired and decision.intent not in {Intent.CONFIRM, Intent.CANCEL, Intent.EXIT}:
                return self._process_command(raw_text)
            return decision.intent is Intent.EXIT

        response = f'Tienes una acción sensible pendiente. {self._confirmation_instructions()}'
        self.state.last_response = response
        self.state.status = 'waiting_confirmation'
        self._emit_response(response)
        return False

    def _execute_command(self, parsed: ParsedCommand) -> tuple[str, int]:
        action_status = {
            Intent.YOUTUBE: 'Buscando en YouTube',
            Intent.IMPORTANT_EMAIL: 'Consultando Gmail',
            Intent.CONNECT_GMAIL: 'Esperando autorización de Gmail',
        }.get(parsed.intent)
        if action_status:
            self._notify('state', action_status)
        started_at = perf_counter()
        response = self.router.handle(parsed)
        duration_ms = int((perf_counter() - started_at) * 1000)
        self._record_response(parsed, response, duration_ms)
        return response, duration_ms

    def _record_response(self, parsed: ParsedCommand, response: str, duration_ms: int) -> None:
        if self.config.record_history and parsed.intent not in {Intent.IMPORTANT_EMAIL, Intent.LIST_WINDOWS, Intent.CLOSE_WINDOW}:
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

    def _emit_response(self, response: str, *, speech: str | None = None) -> None:
        print(response)
        self._notify('reply', response)
        if self.config.enable_tts:
            self._notify('state', 'Respondiendo')
            spoken = response if speech is None else speech
            if len(spoken) > 420 and self._on_event is not None:
                spoken = spoken[:390].rsplit(' ', 1)[0] + '. Puedes leer el resto en la ventana.'
            if self.speaker.speak(spoken):
                if self._speech_failed:
                    self._speech_failed = False
                    self._notify('audio', '')
            elif not self._speech_failed:
                self._speech_failed = True
                warning = 'No pude reproducir la voz. Revisa la salida de audio de Windows.'
                print(warning)
                self._notify('audio', warning)

    def _refresh_runtime_state(self) -> None:
        aliases = self.memory_manager.load_aliases()
        self.memory_manager.sync_command_catalog(self.config.path_aliases, self.config.app_targets, aliases)
        self.parser = CommandParser(
            custom_paths=aliases['custom_paths'],
            custom_apps=aliases['custom_apps'],
        )
        self.router = CommandRouter(
            config=self.config,
            logger=self.logger,
            memory_manager=self.memory_manager,
            chat_history=self._chat_history,
            youtube=self.youtube,
        )

    def _infer_source(self, parsed: ParsedCommand) -> str:
        if parsed.intent is Intent.FILE_SELECTION:
            return 'explorer'
        if parsed.intent is Intent.YOUTUBE:
            return 'youtube'
        if parsed.intent in {
            Intent.GET_TIME,
            Intent.GET_DATE,
            Intent.LIST_COMMANDS,
            Intent.SHOW_METRICS,
            Intent.SHOW_STATUS,
            Intent.OPEN_URL,
            Intent.SEARCH_FILE,
            Intent.CREATE_NOTE,
            Intent.SET_TIMER,
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

    def _prepare_voice_command(self, transcript: str) -> tuple[str | None, str | None]:
        cleaned = transcript.strip()
        if not cleaned:
            return None, 'No escuche una orden clara. Intenta otra vez.'

        wake_word = self.config.voice_wake_word.strip()
        if not self.config.voice_require_wake_word or not wake_word:
            return cleaned, None

        wake_words = [self.parser._normalize(word) for word in re.findall(r'\w+', wake_word)]
        spoken_words = list(re.finditer(r'\w+', cleaned))
        if spoken_words and spoken_words[0].group().lower() in {'oye', 'hey', 'hola'}:
            spoken_words = spoken_words[1:]
        matched_words = len(wake_words)
        prefix = [self.parser._normalize(word.group()) for word in spoken_words[:matched_words]]
        if wake_words == ['jarvis']:
            if prefix in (['yarvis'], ['jarbis'], ['harvis'], ['jarviz']):
                prefix = wake_words
            elif [self.parser._normalize(word.group()) for word in spoken_words[:2]] == ['y', 'arvis']:
                prefix = wake_words
                matched_words = 2
        if not wake_words or prefix != wake_words:
            now = monotonic()
            if now < self.state.voice_activation_deadline:
                self.state.voice_activation_deadline = 0
                return cleaned, None
            if now < self.state.search_query_deadline:
                return f'busca el archivo llamado {cleaned}', None
            if now < self.state.command_followup_deadline:
                prefix = self.state.command_followup_prefix
                if self.parser._normalize(cleaned).startswith(f'{prefix} '):
                    return cleaned, None
                return f'{prefix} {cleaned}', None
            if now < self.state.search_result_deadline:
                if self.parser._normalize(cleaned).strip('.') in {'abrelo', 'abrela'}:
                    return 'abre el resultado', None
                follow_up = self.parser.parse(cleaned)
                if follow_up.intent is Intent.OPEN_SEARCH_RESULT:
                    return cleaned, None
            if now < self.state.media_followup_deadline and self.state.pending_confirmation is None:
                if self.parser.parse(cleaned).intent is Intent.YOUTUBE_CONTROL:
                    return cleaned, None
                if re.match(r'^y\s+(?:busca|pon|reproduce)\b', self.parser._normalize(cleaned)):
                    return f'abre youtube {cleaned}', None
            return None, f'No escuche la palabra de activacion "{wake_word}". Intenta otra vez.'

        command_text = cleaned[spoken_words[matched_words - 1].end():].lstrip(' \t,.;:-!')
        if not re.search(r'\w', command_text):
            self.state.voice_activation_deadline = monotonic() + 10
            return None, 'Te escucho.'
        self.state.voice_activation_deadline = 0
        if monotonic() < self.state.search_result_deadline and self.parser._normalize(command_text).strip('.') in {'abrelo', 'abrela'}:
            return 'abre el resultado', None
        return command_text, None

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
            f"- Wake word requerido: {'SI' if self.config.voice_require_wake_word else 'NO'}",
            f'- Wake word configurado: {self.config.voice_wake_word}',
            f'- Reconocimiento de voz actual: {self.speech_recognizer.backend_summary()}',
            f'- IA conversacional: {self.config.ai_status}',
            f"- Historial local: {'SI' if self.config.record_history else 'NO'}",
            f"- Cambios del Explorador: {'habilitados con confirmación' if self.config.apply_file_changes else 'vista previa'}",
        ]

        if self.state.current_mode == 'voice':
            lines.append('- Escucha continua.' if self.config.voice_continuous else '- Presiona Enter para hablar.')

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
        print(f"- Wake word requerido: {'SI' if self.config.voice_require_wake_word else 'NO'}")
        print(f'- Wake word configurado: {self.config.voice_wake_word}')
        print(f'- Reconocimiento de voz: {self.speech_recognizer.backend_summary()}')
        print(f'- IA conversacional: {self.config.ai_status}')
        if mode == 'voice':
            print('- Escucha continua.' if self.config.voice_continuous else '- Presiona Enter para hablar.')
        print(f'Prueba frases como: {examples}')
