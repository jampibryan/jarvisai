from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.assistant import JarvisAssistant
from app.config import AppConfig
from app.state import AssistantState


TEMP_ROOT = Path(r'C:\Users\jeibi\AppData\Local\Temp')


def _build_temp_root() -> Path:
    root = TEMP_ROOT / f'jarvis_assistant_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cleanup_dir(root: Path) -> None:
    for path in sorted(root.rglob('*'), reverse=True):
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                path.rmdir()
        except OSError:
            pass
    try:
        root.rmdir()
    except OSError:
        pass


def _build_test_config(root: Path, confirm_dangerous_actions: bool, enable_tts: bool | None = None) -> AppConfig:
    config = AppConfig.load()
    config = replace(
        config,
        app_name=f'JarvisAITest-{uuid4().hex}',
        log_dir=root / 'logs',
        history_path=root / 'history.db',
        aliases_path=root / 'aliases.json',
        google_credentials_path=root / 'credentials' / 'google_client_secret.json',
        google_calendar_token_path=root / 'credentials' / 'token_calendar.json',
        google_gmail_token_path=root / 'credentials' / 'token_gmail.json',
        confirm_dangerous_actions=confirm_dangerous_actions,
        enable_tts=config.enable_tts if enable_tts is None else enable_tts,
    )
    config.ensure_runtime_paths()
    return config


def test_assistant_executes_shutdown_without_confirmation_when_disabled() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=False))
        seen = []

        assistant.router.handle = lambda parsed: seen.append(parsed.intent) or 'Apagando el equipo.'

        should_exit = assistant._process_command('quiero apagar la laptop')

        assert should_exit is False
        assert seen == [assistant.parser.parse('quiero apagar la laptop').intent]
        assert assistant.state.pending_confirmation is None
        assert assistant.state.status == 'idle'
        assert assistant.state.last_response == 'Apagando el equipo.'
    finally:
        _cleanup_dir(root)


def test_assistant_keeps_confirmation_flow_when_enabled() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=True))
        assistant.state = AssistantState()

        should_exit = assistant._process_command('reinicia mi pc')

        assert should_exit is False
        assert assistant.state.pending_confirmation is not None
        assert assistant.state.pending_confirmation.intent.value == 'restart_computer'
        assert assistant.state.status == 'waiting_confirmation'
        assert 'Responde si o no' in assistant.state.last_response
    finally:
        _cleanup_dir(root)


def test_assistant_speaks_in_text_mode_when_tts_is_enabled() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=False, enable_tts=True))
        heard: list[str] = []
        assistant.speaker = SimpleNamespace(speak=lambda text: heard.append(text) or True)

        assistant._emit_response('Apagando el equipo en 3, 2, 1.', speak_response=False)

        assert heard == ['Apagando el equipo en 3, 2, 1.']
    finally:
        _cleanup_dir(root)


def test_assistant_does_not_speak_when_tts_is_disabled_in_text_mode() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=False, enable_tts=False))
        heard: list[str] = []
        assistant.speaker = SimpleNamespace(speak=lambda text: heard.append(text) or True)

        assistant._emit_response('Solo texto.', speak_response=False)

        assert heard == []
    finally:
        _cleanup_dir(root)
