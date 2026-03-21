import sqlite3

from app.memory.memory_manager import MemoryManager


def test_memory_manager_syncs_command_catalog(tmp_path) -> None:
    aliases_path = tmp_path / 'aliases.json'
    aliases_path.write_text('{"custom_paths": {"reportes": "D:\\\\Reportes"}, "custom_apps": {"editor": "vscode"}}', encoding='utf-8')
    database_path = tmp_path / 'jarvis.db'

    memory = MemoryManager(aliases_path, database_path)
    memory.ensure_database()
    aliases = memory.load_aliases()
    memory.sync_command_catalog(
        path_aliases={'documents': 'C:/Docs'},
        app_targets={'vscode': 'vscode'},
        aliases=aliases,
    )

    commands = memory.list_commands()
    phrases = {item['phrase'] for item in commands}

    assert 'documentos' in phrases
    assert 'editor' in phrases
    assert 'comandos' in phrases
    assert 'metricas' in phrases

    with sqlite3.connect(database_path) as connection:
        total = connection.execute('SELECT COUNT(*) FROM command_catalog').fetchone()[0]

    assert total >= 4


def test_memory_manager_saves_and_replaces_alias(tmp_path) -> None:
    aliases_path = tmp_path / 'aliases.json'
    aliases_path.write_text('{"custom_paths": {}, "custom_apps": {}}', encoding='utf-8')
    database_path = tmp_path / 'jarvis.db'

    memory = MemoryManager(aliases_path, database_path)
    memory.ensure_database()
    memory.sync_command_catalog(
        path_aliases={'documents': 'C:/Docs'},
        app_targets={'vscode': 'vscode'},
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


def test_memory_manager_records_history_with_metrics(tmp_path) -> None:
    aliases_path = tmp_path / 'aliases.json'
    aliases_path.write_text('{"custom_paths": {}, "custom_apps": {}}', encoding='utf-8')
    database_path = tmp_path / 'jarvis.db'

    memory = MemoryManager(aliases_path, database_path)
    memory.ensure_database()
    memory.record_history('hora', 'hora', 'get_time', 'hora', 'system', 'Son las 10:00.', 12)
    memory.record_history('algo raro', 'algo raro', 'unknown', '', 'unknown', 'No entendi ese comando todavia.', 4)

    summary = memory.render_metrics_summary()

    assert 'Total de comandos: 2' in summary
    assert 'Fallos: 1' in summary
