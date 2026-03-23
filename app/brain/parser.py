from __future__ import annotations

import re
import unicodedata

from app.brain.command_catalog import (
    BUILTIN_APP_COMMANDS,
    BUILTIN_PATH_COMMANDS,
    LEARN_VERBS,
    OPEN_TRIGGERS,
    REPLACE_VERBS,
    SYSTEM_PHRASES,
    find_builtin_command,
)
from app.brain.intents import Intent, ParsedCommand


class CommandParser:
    """Convierte frases humanas en intenciones internas de Jarvis.

    Este parser no intenta resolver lenguaje natural libre. En su lugar,
    trabaja con reglas claras y faciles de mantener para que el proyecto
    siga siendo predecible mientras crece.
    """

    # Prefijos conversacionales que vuelven mas natural hablarle a Jarvis,
    # pero que no cambian la intencion principal del usuario.
    CONVERSATIONAL_PREFIXES = (
        'me gustaria abrir ',
        'me gustaria abrirr ',
        'me gustaria ver ',
        'me gustaria usar ',
        'quiero abrir ',
        'quiero abrirr ',
        'quiero ver ',
        'quiero usar ',
        'quiero ir a ',
        'necesito abrir ',
        'necesito ver ',
        'necesito usar ',
        'puedes abrir ',
        'puedes mostrar ',
        'puedes abrirme ',
        'entra a ',
        'entra al ',
        'entra a la ',
        'entrar a ',
        'entrar al ',
        'podrias abrir ',
        'podrias mostrar ',
        'llevame a ',
        'ir a ',
        'muestrame ',
        'muestrame el ',
        'muestrame la ',
        'muestrame los ',
        'muestrame las ',
        'por favor ',
        'puedes ',
        'podrias ',
        'quiero ',
        'necesito ',
        'me gustaria ',
    )

    def __init__(
        self,
        custom_paths: dict[str, str] | None = None,
        custom_apps: dict[str, str] | None = None,
    ) -> None:
        self.custom_paths = self._build_alias_index(custom_paths or {})
        self.custom_apps = self._build_alias_index(custom_apps or {})

    def parse(self, raw_text: str) -> ParsedCommand:
        """Punto de entrada principal del cerebro textual.

        El orden importa: primero revisamos aprendizaje de alias, luego
        comandos del sistema y al final aperturas de rutas o aplicaciones.
        """
        working_text = self._strip_assistant_prefix(raw_text)

        alias_command = self._match_alias_command(working_text)
        if alias_command is not None:
            return alias_command

        normalized = self._normalize(working_text)

        system_command = self._match_system_command(raw_text, normalized)
        if system_command is not None:
            return system_command

        open_command = self._match_open_command(raw_text, normalized)
        if open_command is not None:
            return open_command

        return ParsedCommand(raw_text, normalized, Intent.UNKNOWN)

    def _match_alias_command(self, raw_text: str) -> ParsedCommand | None:
        # Soportamos dos estilos: uno explicito (`aprende ruta x = y`) y
        # otro mas natural (`recuerda que editor es vscode`).
        for verbs, intent in ((LEARN_VERBS, Intent.LEARN_ALIAS), (REPLACE_VERBS, Intent.REPLACE_ALIAS)):
            explicit = self._match_explicit_alias_command(raw_text, verbs, intent)
            if explicit is not None:
                return explicit

            natural = self._match_natural_alias_command(raw_text, verbs, intent)
            if natural is not None:
                return natural

        return self._match_phrase_based_alias_command(raw_text)

    def _match_explicit_alias_command(
        self,
        raw_text: str,
        verbs: set[str],
        intent: Intent,
    ) -> ParsedCommand | None:
        pattern = r"^\s*(?P<verb>\w+)\s+(?P<kind>ruta|app)\s+(?P<label>.+?)\s*=\s*(?P<target>.+?)\s*$"
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        verb = self._normalize(match.group('verb'))
        if verb not in verbs:
            return None

        return self._build_alias_command(
            raw_text=raw_text,
            intent=intent,
            alias_kind=self._normalize(match.group('kind')),
            label=match.group('label').strip(),
            target=match.group('target').strip(),
        )

    def _match_natural_alias_command(
        self,
        raw_text: str,
        verbs: set[str],
        intent: Intent,
    ) -> ParsedCommand | None:
        pattern = (
            r"^\s*(?P<verb>\w+)\s+(?:que\s+)?(?P<label>.+?)\s+"
            r"(?P<link>abre|es|sea|significa)\s+(?P<target>.+?)\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        verb = self._normalize(match.group('verb'))
        if verb not in verbs:
            return None

        label = match.group('label').strip(' ,')
        target = match.group('target').strip()
        alias_kind = self._infer_alias_kind(target, self._normalize(match.group('link')))
        return self._build_alias_command(raw_text, intent, alias_kind, label, target)

    def _match_phrase_based_alias_command(self, raw_text: str) -> ParsedCommand | None:
        # Permite formas un poco mas humanas como:
        # - cuando diga reportes abre D:\Reportes
        # - si digo editor es vscode
        pattern = (
            r"^\s*(?:cuando\s+diga|si\s+digo)\s+(?P<label>.+?)\s+"
            r"(?P<link>abre|es|sea|significa)\s+(?P<target>.+?)\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        label = match.group('label').strip(' ,')
        target = match.group('target').strip()
        alias_kind = self._infer_alias_kind(target, self._normalize(match.group('link')))
        return self._build_alias_command(raw_text, Intent.LEARN_ALIAS, alias_kind, label, target)

    def _match_system_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        command_map = (
            (SYSTEM_PHRASES['confirm'], Intent.CONFIRM),
            (SYSTEM_PHRASES['cancel'], Intent.CANCEL),
            (SYSTEM_PHRASES['exit'], Intent.EXIT),
            (SYSTEM_PHRASES['list_commands'], Intent.LIST_COMMANDS),
            (SYSTEM_PHRASES['show_metrics'], Intent.SHOW_METRICS),
            (SYSTEM_PHRASES['show_status'], Intent.SHOW_STATUS),
            (SYSTEM_PHRASES['restart'], Intent.RESTART_COMPUTER),
            (SYSTEM_PHRASES['shutdown'], Intent.SHUTDOWN_COMPUTER),
        )

        for phrases, intent in command_map:
            if self._matches_any_phrase(normalized, phrases):
                return ParsedCommand(raw_text, normalized, intent)

        if self._matches_any_phrase(normalized, SYSTEM_PHRASES['get_time']):
            return ParsedCommand(raw_text, normalized, Intent.GET_TIME)

        if self._matches_any_phrase(normalized, SYSTEM_PHRASES['get_date']):
            return ParsedCommand(raw_text, normalized, Intent.GET_DATE)

        if self._matches_system_action(normalized, action='restart'):
            return ParsedCommand(raw_text, normalized, Intent.RESTART_COMPUTER)

        if self._matches_system_action(normalized, action='shutdown'):
            return ParsedCommand(raw_text, normalized, Intent.SHUTDOWN_COMPUTER)

        return None

    def _match_open_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        # Generamos varias vistas de la misma frase para tolerar articulos,
        # verbos y formas mas conversacionales sin llenar el codigo de ifs.
        candidates = self._build_lookup_candidates(normalized)

        # Los alias del usuario tienen prioridad sobre los comandos base.
        for candidate in candidates:
            if candidate in self.custom_paths:
                alias = self.custom_paths[candidate]
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_PATH,
                    entity=candidate,
                    metadata={
                        'source': 'custom_path',
                        'target': alias['target'],
                        'label': alias['label'],
                    },
                )

        for candidate in candidates:
            if candidate in self.custom_apps:
                alias = self.custom_apps[candidate]
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_APP,
                    entity=candidate,
                    metadata={
                        'source': 'custom_app',
                        'target': alias['target'],
                        'label': alias['label'],
                    },
                )

        for candidate in candidates:
            builtin_path = find_builtin_command(BUILTIN_PATH_COMMANDS, candidate)
            if builtin_path is not None:
                return ParsedCommand(raw_text, normalized, Intent.OPEN_PATH, entity=builtin_path.entity)

        for candidate in candidates:
            builtin_app = find_builtin_command(BUILTIN_APP_COMMANDS, candidate)
            if builtin_app is not None:
                return ParsedCommand(raw_text, normalized, Intent.OPEN_APP, entity=builtin_app.entity)

        return None

    def _build_lookup_candidates(self, normalized: str) -> list[str]:
        transforms = (
            self._strip_polite_suffix,
            self._strip_conversational_prefix,
            self._strip_open_trigger,
            self._strip_leading_articles,
        )

        candidates: list[str] = []
        queue = [normalized]
        seen: set[str] = set()

        while queue:
            current = queue.pop(0).strip()
            if not current or current in seen:
                continue

            seen.add(current)
            candidates.append(current)

            for transform in transforms:
                transformed = transform(current)
                if transformed and transformed not in seen and transformed != current:
                    queue.append(transformed)

        return candidates

    def _build_alias_command(
        self,
        raw_text: str,
        intent: Intent,
        alias_kind: str,
        label: str,
        target: str,
    ) -> ParsedCommand:
        return ParsedCommand(
            raw_text,
            self._normalize(raw_text),
            intent,
            entity=self._normalize(label),
            metadata={
                'alias_kind': alias_kind,
                'label': label,
                'target': target,
            },
        )

    def _infer_alias_kind(self, target: str, link: str) -> str:
        normalized_target = self._normalize(target)

        if link == 'abre':
            if self._looks_like_path(target):
                return 'ruta'
            if find_builtin_command(BUILTIN_APP_COMMANDS, normalized_target) is not None:
                return 'app'
            return 'ruta'

        return 'app'

    def _looks_like_path(self, target: str) -> bool:
        return bool(re.search(r"[a-zA-Z]:\\|\\|/|\.pdf$|\.txt$|\.docx?$|\.xlsx?$", target.strip(), re.IGNORECASE))

    def _strip_assistant_prefix(self, raw_text: str) -> str:
        stripped = raw_text.strip()
        return re.sub(r"^jarvis\s*[,;:\-]?\s*", '', stripped, flags=re.IGNORECASE)

    def _strip_conversational_prefix(self, text: str) -> str:
        lowered = text
        changed = True
        while changed:
            changed = False
            for prefix in self.CONVERSATIONAL_PREFIXES:
                if lowered.startswith(prefix):
                    lowered = lowered[len(prefix):].strip()
                    changed = True
                    break
        return lowered

    def _strip_open_trigger(self, text: str) -> str:
        return re.sub(rf"^({'|'.join(OPEN_TRIGGERS)})\s+", '', text).strip()

    def _strip_leading_articles(self, text: str) -> str:
        return re.sub(r"^(el|la|los|las|mi|mis|un|una)\s+", '', text).strip()

    def _strip_polite_suffix(self, text: str) -> str:
        return re.sub(r"\s+por favor$", '', text).strip()

    def _normalize(self, raw_text: str) -> str:
        no_accents = ''.join(
            char
            for char in unicodedata.normalize('NFKD', raw_text.lower())
            if not unicodedata.combining(char)
        )
        clean = re.sub(r"[^a-z0-9\s:\\\.-]", ' ', no_accents)
        normalized = re.sub(r"\s+", ' ', clean).strip()
        return self._normalize_common_typos(normalized)

    def _normalize_common_typos(self, text: str) -> str:
        replacements = (
            (r'\babrirr\b', 'abrir'),
        )

        fixed = text
        for pattern, replacement in replacements:
            fixed = re.sub(pattern, replacement, fixed)
        return fixed

    def _matches_any_phrase(self, text: str, phrases: tuple[str, ...]) -> bool:
        for phrase in phrases:
            pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            if re.search(pattern, text):
                return True
        return False

    def _matches_system_action(self, text: str, action: str) -> bool:
        action_patterns = {
            'restart': r'\b(reinicia|reiniciar|reinicie|reinicies)\b',
            'shutdown': r'\b(apaga|apagar|apague|apagues)\b',
        }
        target_pattern = r'(?:\s+(?:el|la|mi|tu|su))?(?:\s+(equipo|laptop|computadora|pc|ordenador|computador|compu|sistema))?'
        verb_pattern = action_patterns[action]
        return re.search(rf'{verb_pattern}{target_pattern}', text) is not None

    def _build_alias_index(self, aliases: dict[str, str]) -> dict[str, dict[str, str]]:
        index: dict[str, dict[str, str]] = {}
        for label, target in aliases.items():
            normalized_label = self._normalize(label)
            if normalized_label:
                index[normalized_label] = {'label': label, 'target': target}
        return index
