from app.config import AppConfig


def test_config_loads_secure_defaults() -> None:
    config = AppConfig.load()

    assert config.app_name
    assert config.input_mode in {'text', 'voice'}
    assert 'drive_d' in config.path_aliases
    assert config.enable_tts is True
    assert config.safe_mode is True
    assert config.confirm_dangerous_actions is True



def test_config_reads_runtime_overrides_from_env(monkeypatch) -> None:
    monkeypatch.setenv('JARVIS_INPUT_MODE', 'voice')
    monkeypatch.setenv('JARVIS_ENABLE_TTS', 'off')
    monkeypatch.setenv('JARVIS_SAFE_MODE', '0')
    monkeypatch.setenv('JARVIS_CONFIRM_DANGEROUS_ACTIONS', 'no')
    monkeypatch.setenv('JARVIS_ENABLE_VOICE', 'yes')
    monkeypatch.setenv('JARVIS_VOICE_REQUIRE_WAKE_WORD', '0')
    monkeypatch.setenv('JARVIS_VOICE_WAKE_WORD', 'viernes')
    monkeypatch.setenv('JARVIS_VOICE_OFFLINE_FALLBACK', '0')
    monkeypatch.setenv('JARVIS_AI_PROVIDER', ' DeepSeek ')
    monkeypatch.setenv('JARVIS_DEEPSEEK_API_KEY', 'fake_key')
    monkeypatch.setenv('JARVIS_RECORD_HISTORY', '0')

    config = AppConfig.load()

    assert config.input_mode == 'voice'
    assert config.enable_tts is False
    assert config.safe_mode is False
    assert config.confirm_dangerous_actions is False
    assert config.enable_voice is True
    assert config.voice_require_wake_word is False
    assert config.voice_wake_word == 'viernes'
    assert config.voice_offline_fallback is False
    assert config.ai_provider == 'deepseek'
    assert config.ai_status == 'DeepSeek (deepseek-flash)'
    assert config.record_history is False
