from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_name: str
    language: str
    input_mode: str
    enable_voice: bool
    enable_tts: bool
    voice_timeout: int
    voice_phrase_time_limit: int
    voice_ambient_duration: float
    voice_pause_threshold: float
    voice_non_speaking_duration: float
    voice_dynamic_energy_threshold: bool
    voice_energy_threshold: int
    voice_require_wake_word: bool
    voice_wake_word: str
    voice_offline_fallback: bool
    voice_engine: str
    voice_continuous: bool
    voice_rate: int
    safe_mode: bool
    confirm_dangerous_actions: bool
    log_level: str
    root_dir: Path
    log_dir: Path
    history_path: Path
    aliases_path: Path
    notes_dir: Path
    google_calendar_enabled: bool
    google_gmail_enabled: bool
    google_credentials_path: Path
    google_calendar_token_path: Path
    google_gmail_token_path: Path
    gemini_api_key: str
    gemini_model: str
    ai_provider: str
    deepseek_api_key: str
    deepseek_model: str
    record_history: bool
    apply_file_changes: bool
    path_aliases: dict[str, str]
    app_targets: dict[str, str]
    app_web_targets: dict[str, str]

    @classmethod
    def load(cls) -> 'AppConfig':
        root_dir = Path(__file__).resolve().parent.parent
        _load_dotenv(root_dir)
        user_home = Path.home()
        env = os.environ

        path_aliases = {
            'drive_d': r'D:\\',
            'downloads': str(user_home / 'Downloads'),
            'documents': str(user_home / 'Documents'),
            'desktop': str(user_home / 'Desktop'),
            'pictures': str(user_home / 'Pictures'),
            'videos': str(user_home / 'Videos'),
            'music': str(user_home / 'Music'),
        }

        app_targets = {
            'chrome': 'chrome',
            'chatgpt': 'chatgpt',
            'youtube': 'youtube',
            'gmail': 'gmail',
            'github': 'github',
            'facebook': 'facebook',
            'instagram': 'instagram',
            'tiktok': 'tiktok',
            'x': 'x',
            'linkedin': 'linkedin',
            'google_drive': 'drive',
            'google_maps': 'maps',
            'google_translate': 'translate',
            'netflix': 'netflix',
            'spotify': 'spotify',
            'discord': 'discord',
            'telegram': 'telegram',
            'notion': 'notion',
            'canva': 'canva',
            'google_calendar': 'calendar',
            'google_meet': 'meet',
            'claude': 'claude',
            'gemini': 'gemini',
            'copilot': 'copilot',
            'perplexity': 'perplexity',
            'stack_overflow': 'stackoverflow',
            'reddit': 'reddit',
            'amazon': 'amazon',
            'mercado_libre': 'mercadolibre',
            'brave': 'brave',
            'vscode': 'vscode',
            'excel': 'excel',
            'power_bi': 'power_bi',
            'whatsapp': 'whatsapp',
            'cmd': 'cmd',
            'notepad': 'notepad',
            'calculator': 'calculator',
            'paint': 'paint',
            'task_manager': 'task_manager',
            'control_panel': 'control_panel',
            'settings': 'settings',
        }

        app_web_targets = {
            'chatgpt': 'https://chatgpt.com',
            'youtube': 'https://www.youtube.com',
            'gmail': 'https://mail.google.com',
            'github': 'https://github.com',
            'whatsapp': 'https://web.whatsapp.com',
            'facebook': 'https://www.facebook.com',
            'instagram': 'https://www.instagram.com',
            'tiktok': 'https://www.tiktok.com',
            'x': 'https://x.com',
            'linkedin': 'https://www.linkedin.com',
            'google_drive': 'https://drive.google.com',
            'google_maps': 'https://maps.google.com',
            'google_translate': 'https://translate.google.com',
            'netflix': 'https://www.netflix.com',
            'spotify': 'https://open.spotify.com',
            'discord': 'https://discord.com/app',
            'telegram': 'https://web.telegram.org',
            'notion': 'https://www.notion.so',
            'canva': 'https://www.canva.com',
            'google_calendar': 'https://calendar.google.com',
            'google_meet': 'https://meet.google.com',
            'claude': 'https://claude.ai',
            'gemini': 'https://gemini.google.com',
            'copilot': 'https://copilot.microsoft.com',
            'perplexity': 'https://www.perplexity.ai',
            'stack_overflow': 'https://stackoverflow.com',
            'reddit': 'https://www.reddit.com',
            'amazon': 'https://www.amazon.com',
            'mercado_libre': 'https://www.mercadolibre.com',
        }

        return cls(
            app_name='JarvisAI',
            language=env.get('JARVIS_LANGUAGE', 'es-PE'),
            input_mode=_read_input_mode(env.get('JARVIS_INPUT_MODE')),
            enable_voice=_read_bool_env(env, 'JARVIS_ENABLE_VOICE', False),
            enable_tts=_read_bool_env(env, 'JARVIS_ENABLE_TTS', True),
            voice_timeout=_read_int_env(env, 'JARVIS_VOICE_TIMEOUT', 5),
            voice_phrase_time_limit=_read_int_env(env, 'JARVIS_VOICE_PHRASE_TIME_LIMIT', 28),
            voice_ambient_duration=_read_float_env(env, 'JARVIS_VOICE_AMBIENT_DURATION', 0.8),
            voice_pause_threshold=_read_float_env(env, 'JARVIS_VOICE_PAUSE_THRESHOLD', 2.4),
            voice_non_speaking_duration=_read_float_env(env, 'JARVIS_VOICE_NON_SPEAKING_DURATION', 0.5),
            voice_dynamic_energy_threshold=_read_bool_env(env, 'JARVIS_VOICE_DYNAMIC_ENERGY', True),
            voice_energy_threshold=_read_int_env(env, 'JARVIS_VOICE_ENERGY_THRESHOLD', 300),
            voice_require_wake_word=_read_bool_env(env, 'JARVIS_VOICE_REQUIRE_WAKE_WORD', True),
            voice_wake_word=env.get('JARVIS_VOICE_WAKE_WORD', 'jarvis').strip() or 'jarvis',
            voice_offline_fallback=_read_bool_env(env, 'JARVIS_VOICE_OFFLINE_FALLBACK', True),
            voice_engine=env.get('JARVIS_VOICE_ENGINE', 'auto').strip().lower(),
            voice_continuous=_read_bool_env(env, 'JARVIS_VOICE_CONTINUOUS', False),
            voice_rate=_read_int_env(env, 'JARVIS_VOICE_RATE', 175),
            safe_mode=_read_bool_env(env, 'JARVIS_SAFE_MODE', True),
            confirm_dangerous_actions=_read_bool_env(env, 'JARVIS_CONFIRM_DANGEROUS_ACTIONS', True),
            log_level='INFO',
            root_dir=root_dir,
            log_dir=root_dir / 'logs',
            history_path=root_dir / 'data' / 'history.db',
            aliases_path=root_dir / 'data' / 'runtime' / 'aliases.json',
            notes_dir=root_dir / 'data' / 'notes',
            google_calendar_enabled=False,
            google_gmail_enabled=False,
            google_credentials_path=root_dir / 'credentials' / 'google_client_secret.json',
            google_calendar_token_path=root_dir / 'credentials' / 'token_calendar.json',
            google_gmail_token_path=root_dir / 'credentials' / 'token_gmail.json',
            gemini_api_key=env.get('JARVIS_GEMINI_API_KEY', '').strip(),
            gemini_model=env.get('JARVIS_GEMINI_MODEL', 'gemini-2.5-flash').strip() or 'gemini-2.5-flash',
            ai_provider=env.get('JARVIS_AI_PROVIDER', 'gemini').strip().lower() or 'gemini',
            deepseek_api_key=env.get('JARVIS_DEEPSEEK_API_KEY', '').strip(),
            deepseek_model=env.get('JARVIS_DEEPSEEK_MODEL', 'deepseek-flash').strip() or 'deepseek-flash',
            record_history=_read_bool_env(env, 'JARVIS_RECORD_HISTORY', True),
            apply_file_changes=_read_bool_env(env, 'JARVIS_APPLY_FILE_CHANGES', False),
            path_aliases=path_aliases,
            app_targets=app_targets,
            app_web_targets=app_web_targets,
        )

    @property
    def ai_status(self) -> str:
        if self.ai_provider == 'off':
            return 'desactivada'
        if self.ai_provider == 'gemini':
            return f'Gemini ({self.gemini_model})' if self.gemini_api_key else 'Gemini sin clave configurada'
        if self.ai_provider == 'deepseek':
            return f'DeepSeek ({self.deepseek_model})' if self.deepseek_api_key else 'DeepSeek sin clave configurada'
        return 'proveedor inválido. Usa gemini, deepseek u off.'

    def ensure_runtime_paths(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.aliases_path.parent.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.google_credentials_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.aliases_path.exists():
            seed = self.root_dir / 'data' / 'aliases.json'
            content = seed.read_text(encoding='utf-8-sig') if seed.is_file() else (
                '{\n  "custom_paths": {},\n  "custom_apps": {}\n}\n'
            )
            try:
                with self.aliases_path.open('x', encoding='utf-8') as destination:
                    destination.write(content)
            except FileExistsError:
                pass


def _read_bool_env(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on', 'si'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return default



def _read_input_mode(raw_value: str | None) -> str:
    normalized = (raw_value or 'text').strip().lower()
    if normalized in {'text', 'voice'}:
        return normalized
    return 'text'


def _read_int_env(env: Mapping[str, str], key: str, default: int) -> int:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    try:
        return int(raw_value.strip())
    except ValueError:
        return default


def _read_float_env(env: Mapping[str, str], key: str, default: float) -> float:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    try:
        return float(raw_value.strip())
    except ValueError:
        return default


def _load_dotenv(root_dir: Path) -> None:
    env_file = root_dir / '.env'
    if not env_file.exists():
        return
    try:
        content = env_file.read_text(encoding='utf-8')
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass
