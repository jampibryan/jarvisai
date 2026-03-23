from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from app.brain.command_catalog import (
    BUILTIN_APP_COMMANDS,
    BUILTIN_PATH_COMMANDS,
    HUMAN_COMMAND_GUIDE,
    SYSTEM_PHRASES,
)


class MemoryManager:
    def __init__(self, aliases_path: Path, database_path: Path) -> None:
        self.aliases_path = aliases_path
        self.database_path = database_path

    def ensure_database(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_catalog (
                    phrase TEXT PRIMARY KEY,
                    intent TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    target TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    risk_level TEXT NOT NULL DEFAULT 'low',
                    description TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT '',
                    response TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    error_type TEXT NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_column(connection, 'command_catalog', 'category', "TEXT NOT NULL DEFAULT 'general'")
            self._ensure_column(connection, 'command_catalog', 'risk_level', "TEXT NOT NULL DEFAULT 'low'")
            self._ensure_column(connection, 'command_history', 'source', "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, 'command_history', 'error_type', "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, 'command_history', 'duration_ms', "INTEGER NOT NULL DEFAULT 0")
            connection.commit()

    def load_aliases(self) -> dict[str, dict[str, str]]:
        default_aliases = {'custom_paths': {}, 'custom_apps': {}}

        if not self.aliases_path.exists():
            return default_aliases

        try:
            data = json.loads(self.aliases_path.read_text(encoding='utf-8-sig'))
        except (OSError, json.JSONDecodeError):
            return default_aliases

        custom_paths = data.get('custom_paths', {})
        custom_apps = data.get('custom_apps', {})

        if not isinstance(custom_paths, dict):
            custom_paths = {}
        if not isinstance(custom_apps, dict):
            custom_apps = {}

        return {
            'custom_paths': {str(key): str(value) for key, value in custom_paths.items()},
            'custom_apps': {str(key): str(value) for key, value in custom_apps.items()},
        }

    def save_alias(self, alias_kind: str, label: str, target: str, replace: bool = False) -> dict[str, str]:
        aliases = self.load_aliases()
        label = label.strip()
        target = target.strip()
        normalized = self._normalize_phrase(label)

        if alias_kind not in {'ruta', 'app'}:
            return {'ok': '0', 'message': 'El tipo de alias debe ser ruta o app.'}

        if not normalized or len(normalized) < 2:
            return {'ok': '0', 'message': 'El alias es demasiado corto o invalido.'}

        if not target:
            return {'ok': '0', 'message': 'Debes indicar un destino para el alias.'}

        conflict = self.find_conflict(normalized)
        source_key = 'custom_paths' if alias_kind == 'ruta' else 'custom_apps'
        other_key = 'custom_apps' if alias_kind == 'ruta' else 'custom_paths'

        if conflict and conflict['source'] not in {'custom_path', 'custom_app'}:
            return {
                'ok': '0',
                'message': f"El alias '{label}' choca con un comando reservado del sistema o base.",
            }

        other_match = self._find_alias_key_by_normalized(aliases[other_key], normalized)
        if other_match:
            return {
                'ok': '0',
                'message': f"El alias '{label}' ya existe en otra categoria personalizada. Usa otro nombre.",
            }

        current_key = self._find_alias_key_by_normalized(aliases[source_key], normalized)
        if current_key:
            current_target = aliases[source_key][current_key]
            if current_target == target:
                return {
                    'ok': '1',
                    'message': f"El alias '{current_key}' ya existia con ese mismo destino.",
                }
            if not replace:
                return {
                    'ok': '0',
                    'message': (
                        f"El alias '{current_key}' ya existe y apunta a '{current_target}'. "
                        f"Usa reemplaza {alias_kind} {current_key} = {target} si quieres actualizarlo."
                    ),
                }
            del aliases[source_key][current_key]
            aliases[source_key][label] = target
            self._write_aliases(aliases)
            return {
                'ok': '1',
                'message': f"Alias actualizado: '{label}' ahora apunta a '{target}'.",
            }

        aliases[source_key][label] = target
        self._write_aliases(aliases)
        return {
            'ok': '1',
            'message': f"Alias guardado: '{label}' -> '{target}'.",
        }

    def sync_command_catalog(
        self,
        path_aliases: dict[str, str],
        app_targets: dict[str, str],
        aliases: dict[str, dict[str, str]],
    ) -> None:
        self.ensure_database()

        rows = []
        rows.extend(self._build_builtin_path_rows(path_aliases))
        rows.extend(self._build_builtin_app_rows(app_targets))
        rows.extend(self._build_custom_rows(aliases.get('custom_paths', {}), 'open_path', 'path', 'custom_path'))
        rows.extend(self._build_custom_rows(aliases.get('custom_apps', {}), 'open_app', 'app', 'custom_app'))
        rows.extend(self._build_system_rows())

        with sqlite3.connect(self.database_path) as connection:
            connection.execute('DELETE FROM command_catalog')
            connection.executemany(
                """
                INSERT OR REPLACE INTO command_catalog (
                    phrase, intent, entity, target, target_type, source, category, risk_level, description, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    def list_commands(self) -> list[dict[str, str]]:
        self.ensure_database()

        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                SELECT phrase, intent, target_type, source, category, risk_level, description
                FROM command_catalog
                WHERE enabled = 1
                ORDER BY
                    CASE category
                        WHEN 'system' THEN 1
                        WHEN 'path' THEN 2
                        WHEN 'app' THEN 3
                        WHEN 'custom_path' THEN 4
                        WHEN 'custom_app' THEN 5
                        WHEN 'dangerous' THEN 6
                        ELSE 7
                    END,
                    phrase ASC
                """
            )
            rows = cursor.fetchall()

        return [
            {
                'phrase': row[0],
                'intent': row[1],
                'target_type': row[2],
                'source': row[3],
                'category': row[4],
                'risk_level': row[5],
                'description': row[6],
            }
            for row in rows
        ]

    def render_command_summary(self) -> str:
        commands = self.list_commands()
        if not commands:
            return 'Todavia no hay comandos registrados.'

        lines = ['Guia rapida de comandos recomendados:']
        for example in HUMAN_COMMAND_GUIDE:
            lines.append(f'- {example}')

        custom_paths = [item for item in commands if item['category'] == 'custom_path']
        custom_apps = [item for item in commands if item['category'] == 'custom_app']

        if custom_paths:
            lines.append('')
            lines.append('Alias de rutas aprendidos:')
            for item in custom_paths:
                lines.append(f"- {item['phrase']}: {item['description']}")

        if custom_apps:
            lines.append('')
            lines.append('Alias de apps aprendidos:')
            for item in custom_apps:
                lines.append(f"- {item['phrase']}: {item['description']}")

        return '\n'.join(lines)

    def render_metrics_summary(self) -> str:
        self.ensure_database()
        with sqlite3.connect(self.database_path) as connection:
            total = connection.execute('SELECT COUNT(*) FROM command_history').fetchone()[0]
            success = connection.execute('SELECT COUNT(*) FROM command_history WHERE success = 1').fetchone()[0]
            failures = connection.execute('SELECT COUNT(*) FROM command_history WHERE success = 0').fetchone()[0]
            avg_duration = connection.execute(
                'SELECT COALESCE(ROUND(AVG(duration_ms), 1), 0) FROM command_history'
            ).fetchone()[0]
            top_rows = connection.execute(
                """
                SELECT normalized_text, COUNT(*)
                FROM command_history
                WHERE normalized_text != ''
                GROUP BY normalized_text
                ORDER BY COUNT(*) DESC, normalized_text ASC
                LIMIT 5
                """
            ).fetchall()
            last_failure = connection.execute(
                """
                SELECT raw_text, error_type
                FROM command_history
                WHERE success = 0
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if total == 0:
            return 'Todavia no hay metricas. Usa algunos comandos y luego consulta metricas.'

        success_rate = round((success / total) * 100, 1) if total else 0
        lines = [
            'Metricas del asistente:',
            f'- Total de comandos: {total}',
            f'- Exitos: {success}',
            f'- Fallos: {failures}',
            f'- Tasa de exito: {success_rate}%',
            f'- Tiempo promedio de respuesta: {avg_duration} ms',
        ]
        if top_rows:
            top_text = ', '.join(f'{row[0]} ({row[1]})' for row in top_rows)
            lines.append(f'- Comandos mas usados: {top_text}')
        if last_failure:
            lines.append(f"- Ultimo fallo: {last_failure[0]} [{last_failure[1] or 'desconocido'}]")
        return '\n'.join(lines)

    def record_history(
        self,
        raw_text: str,
        normalized_text: str,
        intent: str,
        entity: str,
        source: str,
        response: str,
        duration_ms: int,
    ) -> None:
        self.ensure_database()
        success = 1 if self._is_success_response(response) else 0
        error_type = self._classify_error(response, intent)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO command_history (
                    raw_text, normalized_text, intent, entity, source, response, success, error_type, duration_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (raw_text, normalized_text, intent, entity, source, response, success, error_type, duration_ms),
            )
            connection.commit()

    def find_conflict(self, normalized_phrase: str) -> dict[str, str] | None:
        for command in self.list_commands():
            if self._normalize_phrase(command['phrase']) == normalized_phrase:
                return command
        return None

    def _write_aliases(self, aliases: dict[str, dict[str, str]]) -> None:
        self.aliases_path.parent.mkdir(parents=True, exist_ok=True)
        self.aliases_path.write_text(
            json.dumps(aliases, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    def _find_alias_key_by_normalized(self, values: dict[str, str], normalized_phrase: str) -> str | None:
        for key in values:
            if self._normalize_phrase(key) == normalized_phrase:
                return key
        return None

    def _normalize_phrase(self, text: str) -> str:
        no_accents = ''.join(
            char
            for char in unicodedata.normalize('NFKD', text.lower())
            if not unicodedata.combining(char)
        )
        clean = re.sub(r'[^a-z0-9\s]', ' ', no_accents)
        return re.sub(r'\s+', ' ', clean).strip()

    def _is_success_response(self, response: str) -> bool:
        failure_prefixes = (
            'No ',
            'La ruta configurada no existe',
            'El alias ',
            'Debes indicar',
            'El tipo de alias',
            'Accion cancelada',
        )
        return not response.startswith(failure_prefixes)

    def _classify_error(self, response: str, intent: str) -> str:
        if response.startswith('No entendi'):
            return 'unknown_command'
        if response.startswith('No pude abrir'):
            return 'launch_error'
        if response.startswith('La ruta configurada no existe'):
            return 'missing_target'
        if 'ya existe' in response or 'choca' in response:
            return 'conflict'
        if response.startswith('Accion cancelada'):
            return 'cancelled'
        if intent in {'restart_computer', 'shutdown_computer'} and 'Modo seguro' in response:
            return 'safe_mode'
        return ''

    def _ensure_column(self, connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
        if column not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

    def _build_builtin_path_rows(self, path_aliases: dict[str, str]) -> list[tuple[str, str, str, str, str, str, str, str, str, int]]:
        rows = []
        for entity, command in BUILTIN_PATH_COMMANDS.items():
            target = path_aliases.get(entity, '')
            for phrase in command.phrases:
                rows.append((phrase, 'open_path', entity, target, 'path', 'builtin_path', 'path', 'low', command.description, 1))
        return rows

    def _build_builtin_app_rows(self, app_targets: dict[str, str]) -> list[tuple[str, str, str, str, str, str, str, str, str, int]]:
        rows = []
        for entity, command in BUILTIN_APP_COMMANDS.items():
            target = app_targets.get(entity, '')
            for phrase in command.phrases:
                rows.append((phrase, 'open_app', entity, target, 'app', 'builtin_app', 'app', 'low', command.description, 1))
        return rows

    def _build_custom_rows(
        self,
        values: dict[str, str],
        intent: str,
        target_type: str,
        source: str,
    ) -> list[tuple[str, str, str, str, str, str, str, str, str, int]]:
        rows = []
        category = 'custom_path' if target_type == 'path' else 'custom_app'
        for phrase, target in values.items():
            description = f'Alias personalizado para {target_type}: {target}'
            rows.append((phrase, intent, phrase, target, target_type, source, category, 'low', description, 1))
        return rows

    def _build_system_rows(self) -> list[tuple[str, str, str, str, str, str, str, str, str, int]]:
        rows: list[tuple[str, str, str, str, str, str, str, str, str, int]] = []

        mapping = {
            'get_time': ('get_time', 'hora', 'Consulta la hora actual', 'system', 'low'),
            'get_date': ('get_date', 'fecha', 'Consulta la fecha actual', 'system', 'low'),
            'list_commands': ('list_commands', 'comandos', 'Muestra una guia de comandos utiles', 'system', 'low'),
            'show_metrics': ('show_metrics', 'metricas', 'Muestra metricas simples del asistente', 'system', 'low'),
            'show_status': ('show_status', 'estado', 'Muestra el diagnostico actual del asistente', 'system', 'low'),
            'confirm': ('confirm', 'confirmar', 'Confirma una accion pendiente', 'system', 'low'),
            'cancel': ('cancel', 'cancelar', 'Cancela una accion pendiente', 'system', 'low'),
            'restart': ('restart_computer', 'reiniciar', 'Reinicia el equipo', 'dangerous', 'high'),
            'shutdown': ('shutdown_computer', 'apagar', 'Apaga el equipo', 'dangerous', 'high'),
            'exit': ('exit', 'salir', 'Cierra el asistente', 'system', 'low'),
        }

        for key, phrases in SYSTEM_PHRASES.items():
            intent, entity, description, category, risk_level = mapping[key]
            for phrase in phrases:
                rows.append((phrase, intent, entity, '', 'system', 'system', category, risk_level, description, 1))

        return rows

