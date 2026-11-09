import sqlite3
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from app.memory.memory_manager import MemoryManager


TEMP_ROOT = Path(gettempdir())


def _build_temp_paths() -> tuple[Path, Path]:
    token = uuid4().hex
    aliases_path = TEMP_ROOT / f'jarvis_{token}_aliases.json'
    database_path = TEMP_ROOT / f'jarvis_{token}.db'
    return aliases_path, database_path


def _cleanup_paths(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def test_memory_manager_syncs_command_catalog() -> None:
    aliases_path, database_path = _build_temp_paths()
    try:
        aliases_path.write_text('{"custom_paths": {"reportes": "D:\\\\Reportes"}, "custom_apps": {"editor": "vscode"}}', encoding='utf-8')

        memory = MemoryManager(aliases_path, database_path)
        memory.ensure_database()
        aliases = memory.load_aliases()
        memory.sync_command_catalog(
            path_aliases={
                'documents': 'C:/Docs',
                'desktop': 'C:/Desktop',
                'pictures': 'C:/Pictures',
                'downloads': 'C:/Downloads',
                'drive_d': 'D:/',
            },
            app_targets={
                'vscode': 'vscode',
                'cmd': 'cmd',
                'explorer': 'explorer',
                'notepad': 'notepad',
                'calculator': 'calculator',
            },
            aliases=aliases,
        )

        commands = memory.list_commands()
        phrases = {item['phrase'] for item in commands}

        assert 'documentos' in phrases
        assert 'escritorio' in phrases
        assert 'cmd' in phrases
        assert 'bloc de notas' in phrases
        assert 'editor' in phrases
        assert 'comandos' in phrases
        assert 'ayuda' in phrases
        assert 'metricas' in phrases

        with sqlite3.connect(database_path) as connection:
            total = connection.execute('SELECT COUNT(*) FROM command_catalog').fetchone()[0]

        assert total >= 20
    finally:
        _cleanup_paths(aliases_path, database_path)


def test_memory_manager_saves_and_replaces_alias() -> None:
    aliases_path, database_path = _build_temp_paths()
    try:
        aliases_path.write_text('{"custom_paths": {}, "custom_apps": {}}', encoding='utf-8')

        memory = MemoryManager(aliases_path, database_path)
        memory.ensure_database()
        memory.sync_command_catalog(
            path_aliases={'documents': 'C:/Docs', 'desktop': 'C:/Desktop', 'pictures': 'C:/Pictures', 'downloads': 'C:/Downloads', 'drive_d': 'D:/'},
            app_targets={'vscode': 'vscode', 'cmd': 'cmd', 'explorer': 'explorer', 'notepad': 'notepad', 'calculator': 'calculator'},
            aliases=memory.load_aliases(),
        )

        created = memory.save_alias('ruta', 'reportes', r'D:\\Reportes')
        assert created['ok'] == '1'

        conflict = memory.save_alias('ruta', 'reportes', r'D:\\Otros')
        assert conflict['ok'] == '0'

        replaced = memory.save_alias('ruta', 'reportes', r'D:\\Otros', replace=True)
        assert replaced['ok'] == '1'

        aliases = memory.load_aliases()
        assert aliases['custom_paths']['reportes'] == r'D:\\Otros'
    finally:
        _cleanup_paths(aliases_path, database_path)


def test_memory_manager_records_history_with_metrics() -> None:
    aliases_path, database_path = _build_temp_paths()
    try:
        aliases_path.write_text('{"custom_paths": {}, "custom_apps": {}}', encoding='utf-8')

        memory = MemoryManager(aliases_path, database_path)
        memory.ensure_database()
        memory.record_history('hora', 'hora', 'get_time', 'hora', 'system', 'Son las 10:00.', 12)
        memory.record_history('algo raro', 'algo raro', 'unknown', '', 'unknown', 'No entendi ese comando todavia.', 4)

        summary = memory.render_metrics_summary()

        assert 'Total de comandos: 2' in summary
        assert 'Fallos: 1' in summary
    finally:
        _cleanup_paths(aliases_path, database_path)


def test_memory_manager_renders_human_command_guide() -> None:
    aliases_path, database_path = _build_temp_paths()
    try:
        aliases_path.write_text('{"custom_paths": {}, "custom_apps": {}}', encoding='utf-8')

        memory = MemoryManager(aliases_path, database_path)
        memory.ensure_database()
        memory.sync_command_catalog(
            path_aliases={'documents': 'C:/Docs', 'desktop': 'C:/Desktop', 'pictures': 'C:/Pictures', 'downloads': 'C:/Downloads', 'drive_d': 'D:/'},
            app_targets={'vscode': 'vscode', 'cmd': 'cmd', 'explorer': 'explorer', 'notepad': 'notepad', 'calculator': 'calculator'},
            aliases=memory.load_aliases(),
        )

        summary = memory.render_command_summary()

        assert 'Guia rapida de comandos recomendados:' in summary
        assert 'jarvis, abre cmd' in summary
        assert 'jarvis, abre bloc de notas' in summary
    finally:
        _cleanup_paths(aliases_path, database_path)


def test_memory_manager_suggests_close_commands() -> None:
    aliases_path, database_path = _build_temp_paths()
    try:
        aliases_path.write_text('{"custom_paths": {}, "custom_apps": {"editor": "vscode"}}', encoding='utf-8')

        memory = MemoryManager(aliases_path, database_path)
        memory.ensure_database()
        memory.sync_command_catalog(
            path_aliases={'documents': 'C:/Docs', 'desktop': 'C:/Desktop', 'pictures': 'C:/Pictures', 'downloads': 'C:/Downloads', 'drive_d': 'D:/'},
            app_targets={'vscode': 'vscode', 'cmd': 'cmd', 'notepad': 'notepad', 'calculator': 'calculator', 'chrome': 'chrome'},
            aliases=memory.load_aliases(),
        )

        suggestions = memory.suggest_commands('crome')

        assert 'chrome' in suggestions
    finally:
        _cleanup_paths(aliases_path, database_path)
