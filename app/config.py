from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_name: str
    language: str
    input_mode: str
    enable_voice: bool
    enable_tts: bool
    safe_mode: bool
    confirm_dangerous_actions: bool
    log_level: str
    root_dir: Path
    log_dir: Path
    history_path: Path
    aliases_path: Path
    google_calendar_enabled: bool
    google_gmail_enabled: bool
    google_credentials_path: Path
    google_calendar_token_path: Path
    google_gmail_token_path: Path
    path_aliases: dict[str, str]
    app_targets: dict[str, str]

    @classmethod
    def load(cls) -> 'AppConfig':
        root_dir = Path(__file__).resolve().parent.parent
        user_home = Path.home()

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

        return cls(
            app_name='JarvisAI',
            language='es-PE',
            input_mode='text',
            enable_voice=False,
            enable_tts=True,
            safe_mode=False,
            confirm_dangerous_actions=False,
            log_level='INFO',
            root_dir=root_dir,
            log_dir=root_dir / 'logs',
            history_path=root_dir / 'data' / 'history.db',
            aliases_path=root_dir / 'data' / 'aliases.json',
            google_calendar_enabled=False,
            google_gmail_enabled=False,
            google_credentials_path=root_dir / 'credentials' / 'google_client_secret.json',
            google_calendar_token_path=root_dir / 'credentials' / 'token_calendar.json',
            google_gmail_token_path=root_dir / 'credentials' / 'token_gmail.json',
            path_aliases=path_aliases,
            app_targets=app_targets,
        )

    def ensure_runtime_paths(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.aliases_path.parent.mkdir(parents=True, exist_ok=True)
        self.google_credentials_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.aliases_path.exists():
            self.aliases_path.write_text(
                '{\n  "custom_paths": {},\n  "custom_apps": {}\n}\n',
                encoding='utf-8',
            )
