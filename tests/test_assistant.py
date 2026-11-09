from dataclasses import replace
import logging
from pathlib import Path
from queue import SimpleQueue
from tempfile import gettempdir
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.actions.selected_files import FilePlan, SelectedFile
from app.actions.window_actions import Window, WindowPlan
from app.assistant import JarvisAssistant
from app.config import AppConfig
from app.state import AssistantState


TEMP_ROOT = Path(gettempdir())


@pytest.fixture(autouse=True)
def disable_real_speech(monkeypatch):
    monkeypatch.setattr('app.voice.speaker._create_windows_voice', Mock(side_effect=RuntimeError('audio disabled for tests')))


def _build_temp_root() -> Path:
    root = TEMP_ROOT / f'jarvis_assistant_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cleanup_dir(root: Path) -> None:
    logger = logging.getLogger(f'JarvisAITest-{root.name.removeprefix("jarvis_assistant_")}')
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
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
        app_name=f'JarvisAITest-{root.name.removeprefix("jarvis_assistant_")}',
        log_dir=root / 'logs',
        history_path=root / 'history.db',
        aliases_path=root / 'aliases.json',
        notes_dir=root / 'notes',
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

        assistant._emit_response('Apagando el equipo en 3, 2, 1.')

        assert heard == ['Apagando el equipo en 3, 2, 1.']
    finally:
        _cleanup_dir(root)


@pytest.mark.parametrize('mode', ['text', 'voice'])
def test_assistant_does_not_speak_when_tts_is_disabled(mode) -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=False, enable_tts=False))
        assistant.state.current_mode = mode
        heard: list[str] = []
        assistant.speaker = SimpleNamespace(speak=lambda text: heard.append(text) or True)

        assistant._emit_response('Solo texto.')

        assert heard == []
    finally:
        _cleanup_dir(root)


def test_assistant_suggests_similar_command_when_it_does_not_understand() -> None:
    root = _build_temp_root()
    try:
        config = _build_test_config(root, confirm_dangerous_actions=True, enable_tts=False)
        # Deshabilitamos Gemini para que el router use la logica de sugerencias locales.
        config = replace(config, gemini_api_key='')
        assistant = JarvisAssistant(config)

        should_exit = assistant._process_command('crhome')

        assert should_exit is False
        assert 'Quizas quisiste decir: chrome' in assistant.state.last_response
    finally:
        _cleanup_dir(root)


def test_assistant_requires_wake_word_for_voice_transcripts() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=True, enable_tts=False))

        command, feedback = assistant._prepare_voice_command('abre chrome')

        assert command is None
        assert feedback == 'No escuche la palabra de activacion "jarvis". Intenta otra vez.'
    finally:
        _cleanup_dir(root)


def test_assistant_extracts_command_after_wake_word() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=True, enable_tts=False))

        command, feedback = assistant._prepare_voice_command('Jarvis, abre chrome')

        assert command == 'abre chrome'
        assert feedback is None
    finally:
        _cleanup_dir(root)


def test_assistant_keeps_only_conversation_in_provider_context() -> None:
    root = _build_temp_root()
    try:
        config = _build_test_config(root, confirm_dangerous_actions=False, enable_tts=False)
        config = replace(config, ai_provider='deepseek', deepseek_api_key='fake_key', gemini_api_key='other_key')
        with patch('app.brain.router.DeepSeekClient') as provider:
            provider.return_value.ask.return_value = 'Respuesta de prueba.'
            assistant = JarvisAssistant(config)
            assistant._process_command('hora')
            assert assistant._chat_history == []

            assistant._process_command('explica la fotosíntesis')
            provider.assert_called_once_with('fake_key', 'deepseek-flash')
            provider.return_value.ask.assert_called_once_with('explica la fotosíntesis', history=[])
            assert assistant._chat_history == [
                {'role': 'user', 'text': 'explica la fotosíntesis'},
                {'role': 'model', 'text': 'Respuesta de prueba.'},
            ]
            assistant._refresh_runtime_state()
            assert assistant.router._chat_history is assistant._chat_history
    finally:
        _cleanup_dir(root)


def test_assistant_rejects_ambiguous_and_expired_confirmation() -> None:
    root = _build_temp_root()
    try:
        assistant = JarvisAssistant(_build_test_config(root, confirm_dangerous_actions=True, enable_tts=False))
        assistant.router.handle = Mock()

        with patch('app.assistant.monotonic', side_effect=[100, 110, 131]):
            assistant._process_command('apaga mi pc')
            assistant._process_command('no sé si debería')
            assert assistant.state.pending_confirmation is not None
            assistant._process_command('sí')

        assistant.router.handle.assert_not_called()
        assert assistant.state.pending_confirmation is None
        assert 'tiempo de espera' in assistant.state.last_response
    finally:
        _cleanup_dir(root)


@pytest.mark.parametrize('apply_changes', [False, True])
def test_file_changes_preview_and_use_the_same_plan_on_confirmation(apply_changes) -> None:
    root = _build_temp_root()
    try:
        config = replace(
            _build_test_config(root, confirm_dangerous_actions=False, enable_tts=False),
            apply_file_changes=apply_changes, ai_provider='deepseek', deepseek_api_key='fake',
        )
        plan = FilePlan('recycle', (SelectedFile(root / 'demo.txt', (0, 0, 0, 0, 0)),))
        with patch('app.brain.router.DeepSeekClient') as provider, patch('app.assistant.execute_file_plan') as execute:
            execute.return_value = 'Enviado.'
            assistant = JarvisAssistant(config)
            assistant.router.prepare_file_action = Mock(return_value=plan)
            assistant._process_command('manda este archivo a la papelera')
            assert 'demo.txt' in assistant.state.last_response
            execute.assert_not_called()
            if apply_changes:
                assistant._process_command('sí')
                execute.assert_called_once_with(plan)
                assert assistant.state.pending_file_plan is None
            else:
                assert 'Vista previa' in assistant.state.last_response
                assert assistant.state.pending_confirmation is None
            provider.return_value.ask.assert_not_called()
    finally:
        _cleanup_dir(root)


def test_continuous_voice_confirms_a_file_change_and_exits_without_keyboard() -> None:
    root = _build_temp_root()
    try:
        config = replace(
            _build_test_config(root, confirm_dangerous_actions=True, enable_tts=True),
            voice_continuous=True, apply_file_changes=True,
        )
        assistant = JarvisAssistant(config)
        assistant.state.current_mode = 'voice'
        assistant.listener = SimpleNamespace(
            available=True, list_devices=lambda: ['default'], ambient_duration=0.8,
            calibrate=Mock(), listen_once=Mock(return_value='audio'),
        )
        assistant.speech_recognizer = SimpleNamespace(
            available=True, transcribe=Mock(side_effect=[
                'le dije a Jarvis que abra esto', 'Jarvis, manda este archivo a la Papelera',
                'sí', 'Jarvis, sí', 'Jarvis, salir',
            ]),
        )
        assistant.speaker = SimpleNamespace(available=True, speak=Mock())
        plan = FilePlan('recycle', (SelectedFile(root / 'demo.txt', (0, 0, 0, 0, 0)),))
        assistant.router.prepare_file_action = Mock(return_value=plan)

        with patch('builtins.input') as keyboard, patch('app.assistant.execute_file_plan', return_value='Enviado.') as execute:
            assistant._run_voice_loop()

        keyboard.assert_not_called()
        assistant.listener.calibrate.assert_called_once()
        assert assistant.listener.listen_once.call_count == 5
        assistant.router.prepare_file_action.assert_called_once()
        execute.assert_called_once_with(plan)
        assert any('jarvis, sí' in call.args[0] for call in assistant.speaker.speak.call_args_list)
        assert assistant.state.last_response == 'Cerrando JarvisAI.'
    finally:
        _cleanup_dir(root)


def test_speaker_applies_voice_rate_from_config() -> None:
    from app.voice.speaker import Speaker
    engine = Mock()
    engine.GetVoices.return_value = []
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker(preferred_rate=210)
    assert speaker.preferred_rate == 210
    assert engine.Rate == 3


def test_audio_failure_keeps_the_answer_visible_and_clears_on_recovery() -> None:
    root = _build_temp_root()
    try:
        events = []
        config = _build_test_config(root, confirm_dangerous_actions=True, enable_tts=True)
        assistant = JarvisAssistant(config, on_event=lambda kind, message: events.append((kind, message)))
        assistant.speaker = SimpleNamespace(speak=Mock(side_effect=[False, True]))
        assistant._emit_response('Primera respuesta')
        assistant._emit_response('Segunda respuesta')

        assert ('reply', 'Primera respuesta') in events
        assert ('reply', 'Segunda respuesta') in events
        audio_events = [message for kind, message in events if kind == 'audio']
        assert 'No pude reproducir' in audio_events[0]
        assert audio_events[1] == ''
    finally:
        _cleanup_dir(root)


def test_desktop_panel_requests_and_attachment_previews_stay_local() -> None:
    root = _build_temp_root()
    try:
        attachment = root / 'nota de prueba.txt'
        attachment.write_text('Contenido de prueba.', encoding='utf-8')
        events = []
        controls = SimpleQueue()
        config = _build_test_config(root, confirm_dangerous_actions=True, enable_tts=False)
        assistant = JarvisAssistant(config, on_event=lambda kind, message: events.append((kind, message)),
                                    voice_controls=controls)
        assistant.router.handle = Mock()
        controls.put(('command', 'mi agenda'))
        controls.put(('preview_attachment', str(attachment)))

        assert not assistant._apply_voice_controls()
        assert ('panel', 'agenda') in events
        assert ('state', 'Analizando documento') in events
        assert any('Contenido de prueba.' in message for kind, message in events if kind == 'reply')
        assistant.router.handle.assert_not_called()
    finally:
        _cleanup_dir(root)


def test_window_closure_requires_confirmation_and_cancel_discards_the_plan() -> None:
    root = _build_temp_root()
    try:
        config = _build_test_config(root, confirm_dangerous_actions=False, enable_tts=False)
        assistant = JarvisAssistant(config)
        plan = WindowPlan(Window(12, 34, 'chrome.exe', 'Pestaña de prueba'), tab=True)
        with (
            patch('app.assistant.prepare_window_close', return_value=plan),
            patch('app.assistant.execute_window_close', return_value='Cierre solicitado.') as execute,
        ):
            assistant._process_command('cierra esta pestaña')
            execute.assert_not_called()
            assistant._process_command('no')
            assert assistant.state.pending_window_plan is None
            execute.assert_not_called()
            assistant._process_command('cierra esta pestaña')
            assistant._process_command('sí')
            execute.assert_called_once_with(plan)
    finally:
        _cleanup_dir(root)


def test_youtube_follow_up_can_pause_without_repeating_wake_word() -> None:
    root = _build_temp_root()
    try:
        config = _build_test_config(root, confirm_dangerous_actions=True, enable_tts=False)
        assistant = JarvisAssistant(config)
        assistant.youtube.search = Mock(return_value='Reproduciendo en YouTube: Imagine.')
        assistant._process_command('pon la canción Imagine en YouTube')
        assistant.youtube.search.assert_called_once_with('imagine', play=True)
        assert assistant._prepare_voice_command('pausa la canción') == ('pausa la canción', None)
        assert assistant._prepare_voice_command('cierra Chrome')[0] is None
    finally:
        _cleanup_dir(root)


def test_incomplete_voice_commands_ask_locally_and_accept_the_title_without_wake_word() -> None:
    root = _build_temp_root()
    try:
        config = _build_test_config(root, confirm_dangerous_actions=True, enable_tts=False)
        assistant = JarvisAssistant(config)
        assistant.youtube.search = Mock(return_value='Reproduciendo en YouTube: Persiana americana.')
        assistant.router._handle_unknown = Mock(return_value='No entendí')
        command, _ = assistant._prepare_voice_command('Y Arvis, pon la música.')
        assistant._process_command(command)
        assert assistant.state.last_response == '¿Qué canción o video quieres en YouTube?'
        assistant.youtube.search.assert_not_called()

        reply, _ = assistant._prepare_voice_command('Persiana americana')
        assistant._process_command(reply)
        assistant.youtube.search.assert_called_once_with('persiana americana', play=True)
        assistant.router._handle_unknown.assert_not_called()

        assistant._process_command('abre')
        assert assistant.state.last_response == '¿Qué quieres que abra?'
        assistant.router._handle_unknown.assert_not_called()
    finally:
        _cleanup_dir(root)


def test_voice_recovers_then_finds_and_opens_file_with_natural_follow_ups() -> None:
    root = _build_temp_root()
    try:
        path = root / 'Tesis - Diapositivas.pptx'
        path.touch()
        config = replace(
            _build_test_config(root, confirm_dangerous_actions=True, enable_tts=True),
            voice_continuous=True,
        )
        events = []
        assistant = JarvisAssistant(config, on_event=lambda kind, message: events.append((kind, message)))
        assistant.state.current_mode = 'voice'
        assistant.listener = SimpleNamespace(
            available=True, calibrate=Mock(),
            listen_once=Mock(side_effect=[OSError('disconnected'), *(['audio'] * 6)]),
        )
        assistant.speech_recognizer = SimpleNamespace(
            available=True, transcribe=Mock(side_effect=[
                'Oye Yarvis', 'busca un documento', 'se llama diapositivas de la tesis', 'ábrelo',
                'Jarvis, dime la hora', 'Jarvis, salir',
            ]),
        )
        assistant.speaker = SimpleNamespace(available=True, speak=Mock())
        assistant.router._build_search_roots = lambda: [root]

        with patch.object(assistant._stop, 'wait'), patch('app.assistant.open_path', return_value=f'Abriendo {path}.') as open_file:
            assistant._run_voice_loop()

        open_file.assert_called_once_with(str(path))
        assert any('Reintentando' in message for kind, message in events if kind == 'state')
        assert any(str(path) in message for kind, message in events if kind == 'reply')
        assert all(str(path) not in call.args[0] for call in assistant.speaker.speak.call_args_list)
        assert any('Son las' in message for kind, message in events if kind == 'reply')
        assert assistant.state.last_response == 'Cerrando JarvisAI.'
    finally:
        _cleanup_dir(root)
