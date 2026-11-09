from __future__ import annotations

import re
import unicodedata
from pathlib import Path

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
        'abriendo ',
        'me abres ',
        'me abres el ',
        'me abres la ',
        'me abres los ',
        'me abres las ',
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
    WEB_SUFFIXES = (
        ' web',
        ' en web',
        ' por web',
        ' navegador',
        ' en navegador',
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

        connected_command = self._match_connected_command(working_text, normalized)
        if connected_command is not None:
            return connected_command

        selection_command = self._match_file_selection(working_text, normalized)
        if selection_command is not None:
            return selection_command

        result_match = re.fullmatch(
            r'(?:abre|abrir|abreme)\s+(?:(?:el|la)\s+)?(?:resultado\s*)?(?P<index>[1-5]|primer[oa]|segund[oa]|tercer[oa]|cuart[oa]|quint[oa])(?:\s+resultado)?\.?',
            self._strip_conversational_prefix(normalized),
        )
        if result_match:
            return ParsedCommand(raw_text, normalized, Intent.OPEN_SEARCH_RESULT, entity=result_match['index'])
        if normalized.rstrip('.') in {'abre el resultado', 'abre ese archivo'}:
            return ParsedCommand(raw_text, normalized, Intent.OPEN_SEARCH_RESULT)

        productivity_command = self._match_productivity_command(working_text, normalized)
        if productivity_command is not None:
            return productivity_command

        system_command = self._match_system_command(raw_text, normalized)
        if system_command is not None:
            return system_command

        open_command = self._match_open_command(raw_text, normalized)
        if open_command is not None:
            return open_command

        return ParsedCommand(raw_text, normalized, Intent.UNKNOWN)

    def _match_connected_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        normalized = re.sub(r'(?<=\w)\.\s+(?=\w)', ' ', normalized)
        request = re.sub(
            r'^(?:(?:oye|por favor|puedes|podrias|quiero(?: que)?|necesito(?: que)?)\s+)+',
            '', normalized.rstrip('.'),
        )
        request = self._strip_polite_suffix(request).strip()
        if re.fullmatch(r'(?:abre|abrir|abreme)(?:\s+(?:el|la|un|una)(?:\s+(?:aplicacion|programa|carpeta|pagina))?)?', request):
            return ParsedCommand(raw_text, normalized, Intent.CLARIFY_COMMAND, entity='open')
        if re.fullmatch(
            r'(?:pon|reproduce)(?:\s+(?:(?:la|el|una|un)\s+)?(?:musica|cancion|video))?'
            r'(?:\s+en\s+you\s*tube)?|(?:abre\s+you\s*tube\s+y\s+)?busca(?:me|r)?\s+en\s+you\s*tube|'
            r'abre\s+you\s*tube\s+y\s+busca(?:me|r)?',
            request,
        ) and request != 'pon':
            return ParsedCommand(raw_text, normalized, Intent.CLARIFY_COMMAND, entity='youtube')
        if request in {'conecta gmail', 'conectar gmail', 'conecta mi gmail'}:
            return ParsedCommand(raw_text, normalized, Intent.CONNECT_GMAIL)
        if re.fullmatch(r'(?:revisa|revisar|muestra|mirar|lee|abre|ver)\s+(?:(?:mis|los)\s+)?correos importantes(?: no leidos)?', request):
            return ParsedCommand(raw_text, normalized, Intent.IMPORTANT_EMAIL, metadata={
                'unread': '1' if request.endswith('no leidos') else '0',
            })
        if request in {'que ventanas tengo abiertas', 'muestra las ventanas abiertas', 'ventanas abiertas', 'programas abiertos'}:
            return ParsedCommand(raw_text, normalized, Intent.LIST_WINDOWS)

        closing = re.fullmatch(r'(?:cierra|cerrar)\s+(?P<target>.+)', request)
        if closing and closing['target'] not in {'jarvis', 'el asistente', 'asistente'}:
            target = self._strip_leading_articles(closing['target'])
            tab = re.fullmatch(r'(?:esta\s+|esa\s+)?pestana(?:\s+activa)?(?:\s+de\s+(.+))?', target)
            if tab:
                return ParsedCommand(raw_text, normalized, Intent.CLOSE_WINDOW, entity=tab[1] or '', metadata={'tab': '1'})
            if target in {'esta ventana', 'esa ventana', 'ventana', 'ventana activa'}:
                target = ''
            else:
                target = re.sub(r'^(?:ventana|programa|aplicacion|documento)\s+(?:de\s+)?', '', target)
            return ParsedCommand(raw_text, normalized, Intent.CLOSE_WINDOW, entity=target, metadata={'tab': '0'})

        controls = {
            'pausa': 'pause', 'pausa el video': 'pause', 'pausa la cancion': 'pause', 'pausa la musica': 'pause',
            'reanuda': 'resume', 'reanuda el video': 'resume', 'continua la cancion': 'resume',
            'reproducela': 'play_last', 'reproducelo': 'play_last', 'ponla': 'play_last',
        }
        if request in controls:
            return ParsedCommand(raw_text, normalized, Intent.YOUTUBE_CONTROL, entity=controls[request])

        youtube = re.fullmatch(
            r'(?:(?:abre|abrir)\s+you\s*tube\s+y\s+)?'
            r'(?P<verb>busca(?:me|r)?|reproduce|pon)(?:\s+en\s+you\s*tube)?\s+(?P<query>.+)',
            request,
        )
        if not youtube:
            return None
        query = youtube['query']
        tagged = re.search(r'\byou\s*tube\b', request) is not None
        explicit_media = re.match(r'^(?:la\s+)?(?:cancion|musica|video)\b', query) is not None
        if not tagged and youtube['verb'] != 'reproduce' and not (youtube['verb'] == 'pon' and explicit_media):
            return None
        query, play_suffix = re.subn(r'\s+y\s+(?:reproduce(?:la|lo)?|reproducir|ponla|ponlo)$', '', query)
        query = re.sub(r'\s+en\s+you\s*tube$', '', query)
        query = re.sub(r'^(?:(?:la|el)\s+)?(?:cancion|video|musica)\s+(?:(?:llamada|llamado|que se llama)\s+)?', '', query).strip()
        if not query or query in {'de', 'del', 'el', 'la', 'un', 'una', 'musica', 'la musica', 'cancion', 'la cancion', 'video', 'el video'}:
            return ParsedCommand(raw_text, normalized, Intent.CLARIFY_COMMAND, entity='youtube')
        return ParsedCommand(raw_text, normalized, Intent.YOUTUBE, metadata={
            'query': query, 'play': '1' if play_suffix or not youtube['verb'].startswith('busca') else '0',
        })

    def _match_file_selection(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        request = re.sub(
            r'^(?:(?:por favor[,\s]+|(?:puedes|podr[ií]as|quiero|necesito)\s+))+',
            '', raw_text.strip().lstrip('¿'), flags=re.IGNORECASE,
        ).rstrip('?')
        match = re.fullmatch(
            r'(?P<verb>[aá]bre|abrir|c[oó]pia|copiar|mu[eé]ve|mover|ren[oó]mbra|renombrar|m[aá]nda|mandar|env[ií]a|enviar|'
            r'b[oó]rra|borrar|elim[ií]na|eliminar)(?P<pronoun>lo|la|los|las)?(?:\s+(?P<rest>.+))?',
            request,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        verb = self._normalize(match['verb'])
        action = {
            'abre': 'open', 'abrir': 'open',
            'copia': 'copy', 'copiar': 'copy',
            'mueve': 'move', 'mover': 'move',
            'renombra': 'rename', 'renombrar': 'rename',
            'manda': 'recycle', 'mandar': 'recycle', 'envia': 'recycle', 'enviar': 'recycle',
            'borra': 'recycle', 'borrar': 'recycle', 'elimina': 'recycle', 'eliminar': 'recycle',
        }[verb]
        rest = (match['rest'] or '').strip()
        if action in {'copy', 'move', 'rename'}:
            separator = r'a|hacia|en' if action != 'rename' else r'a|como'
            split = re.search(rf'(?:^|\s+)(?:{separator})\s+', rest, flags=re.IGNORECASE)
            subject = rest[:split.start()] if split else rest
            argument = rest[split.end():].strip() if split else ''
        elif action == 'recycle':
            split = re.search(
                r'(?:^|\s+)(?:a\s+la|al)\s+(?:papelera(?:\s+de\s+reciclaje)?|tacho(?:\s+de(?:\s+la)?\s+basura)?)\.?$',
                rest, flags=re.IGNORECASE,
            )
            subject = rest[:split.start()] if split else rest
            argument = 'recycle' if split else ''
        else:
            subject, argument = rest, ''

        subject = self._normalize(subject).rstrip('.')
        if action == 'recycle' and not argument:
            subject = re.sub(r'(?:^|\s+)(?:definitivamente|permanentemente|de forma permanente|para siempre)$', '', subject)
        explicit_selection = re.fullmatch(
            r'(?:esto|la seleccion|(?:este|esta|estos|estas|el|la|los|las)\s+(?:archivo|archivos|documento|documentos|pdf|pdfs)'
            r'(?:\s+seleccionad[oa]s?)?|(?:el|la|los|las)\s+seleccionad[oa]s?|'
            r'(?:archivo|archivos|documento|documentos)\s+seleccionad[oa]s?)',
            subject,
        )
        if not (explicit_selection or (match['pronoun'] and not subject) or (not subject and argument)):
            return None

        metadata = {}
        if action in {'copy', 'move'}:
            destination = argument.strip('"')
            key = self._normalize(destination).rstrip('.')
            if destination and Path(destination).is_absolute():
                metadata['destination'] = destination
            elif key in self.custom_paths:
                metadata['destination'] = self.custom_paths[key]['target']
            elif builtin := find_builtin_command(BUILTIN_PATH_COMMANDS, self._strip_leading_articles(key)):
                metadata['folder_entity'] = builtin.entity
        else:
            metadata['argument'] = argument.strip('"')

        return ParsedCommand(raw_text, normalized, Intent.FILE_SELECTION, entity=action, metadata=metadata)

    def _match_productivity_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        return (
            self._match_note_command(raw_text, normalized)
            or self._match_timer_command(raw_text, normalized)
            or self._match_web_search_command(raw_text, normalized)
            or self._match_file_search_command(raw_text, normalized)
            or self._match_url_command(raw_text, normalized)
        )

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
        exact_text = normalized.rstrip('.:-').strip()
        if '?' not in raw_text and exact_text in SYSTEM_PHRASES['confirm']:
            return ParsedCommand(raw_text, normalized, Intent.CONFIRM)
        if exact_text in SYSTEM_PHRASES['cancel']:
            return ParsedCommand(raw_text, normalized, Intent.CANCEL)
        if self._strip_conversational_prefix(exact_text) in SYSTEM_PHRASES['exit']:
            return ParsedCommand(raw_text, normalized, Intent.EXIT)

        command_map = (
            (SYSTEM_PHRASES['list_commands'], Intent.LIST_COMMANDS),
            (SYSTEM_PHRASES['show_metrics'], Intent.SHOW_METRICS),
            (SYSTEM_PHRASES['show_status'], Intent.SHOW_STATUS),
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

    def _match_note_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        pattern = (
            r"^\s*(?:anota|anotame|guardar nota|guarda una nota|crea nota|crea una nota|nota)\s*[:\-]?\s+"
            r"(?P<content>.+?)\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        content = match.group('content').strip()
        return ParsedCommand(
            raw_text,
            normalized,
            Intent.CREATE_NOTE,
            metadata={'content': content},
        )

    def _match_timer_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        pattern = (
            r"^\s*(?:pon(?:me)?|inicia|crea|arranca)?\s*"
            r"(?:un\s+)?(?:temporizador|timer|alarma)\s*(?:de|por)?\s*"
            r"(?P<amount>\d+)\s*(?P<unit>segundo|segundos|minuto|minutos|hora|horas|min|mins|h)\b"
            r"(?:\s+para\s+(?P<label>.+))?\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        amount = int(match.group('amount'))
        unit = self._normalize(match.group('unit'))
        seconds = self._convert_to_seconds(amount, unit)
        if seconds <= 0:
            return None

        label = (match.group('label') or '').strip()
        metadata = {'duration_seconds': str(seconds)}
        if label:
            metadata['label'] = label

        return ParsedCommand(raw_text, normalized, Intent.SET_TIMER, metadata=metadata)

    def _match_file_search_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        normalized = re.sub(r'(?<=\w)\.\s+(?=\w)', ' ', normalized)
        request = self._strip_conversational_prefix(normalized).strip(' .')
        match = re.fullmatch(
            r'(?:(?:me ayudas a|ayudame a)\s+)?'
            r'(?:busca(?:me|r)?|encuentra(?:me)?|encontrar|ubicar?|localizar?|(?:en )?donde (?:esta|quedo|guarde))'
            r'(?:\s+(?P<query>.*))?',
            request,
        )
        if not match:
            return None
        query = self._strip_leading_articles(match['query'] or '')
        query = re.sub(r'^(?:archivo|documento|doucmento|fichero)\b\s*', '', query)
        query = re.sub(r'^(?:(?:que se llama|se llama|llamado|llamada|de nombre|con el nombre)\b\s*)+', '', query)
        query = self._strip_leading_articles(self._strip_polite_suffix(query).strip(' .'))
        return ParsedCommand(raw_text, normalized, Intent.SEARCH_FILE, metadata={'query': query})

    def _match_url_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        candidate = self._extract_url_candidate(raw_text)
        if candidate is None:
            return None

        return ParsedCommand(
            raw_text,
            normalized,
            Intent.OPEN_URL,
            metadata={'url': candidate},
        )

    def _match_web_search_command(self, raw_text: str, normalized: str) -> ParsedCommand | None:
        pattern = (
            r"^\s*(?:busca(?:r)?\s+(?:en\s+)?(?:google|la\s+web|internet|la\s+red)|"
            r"consulta(?:r)?\s+(?:en\s+)?(?:google|la\s+web|internet|la\s+red)|"
            r"googlea(?:r)?)\s+(?P<query>.+?)\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        query = match.group('query').strip(' ?')
        if len(self._normalize(query)) < 2:
            return None

        return ParsedCommand(
            raw_text,
            normalized,
            Intent.WEB_SEARCH,
            metadata={'query': query},
        )

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
            lookup_candidate, open_mode = self._extract_open_mode(candidate)
            builtin_app = find_builtin_command(BUILTIN_APP_COMMANDS, lookup_candidate)
            if builtin_app is not None:
                metadata = {}
                if open_mode:
                    metadata['open_mode'] = open_mode
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_APP,
                    entity=builtin_app.entity,
                    metadata=metadata,
                )

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
        return re.sub(r"^(?:el|la|los|las|mi|mis|un|una)(?:\s+|$)", '', text).strip()

    def _strip_polite_suffix(self, text: str) -> str:
        return re.sub(r"\s+por favor$", '', text).strip()

    def _extract_open_mode(self, text: str) -> tuple[str, str]:
        cleaned = text.strip()
        for suffix in self.WEB_SUFFIXES:
            if cleaned.endswith(suffix):
                return cleaned[: -len(suffix)].strip(), 'web'
        return cleaned, ''

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
            (r'\babir\b', 'abrir'),
            (r'\bavrir\b', 'abrir'),
            (r'\bhabrir\b', 'abrir'),
            (r'\bcrome\b', 'chrome'),
            (r'\bfacebokk\b', 'facebook'),
            (r'\bcalculado?ra\b', 'calculadora'),
            (r'\bconfigurasion\b', 'configuracion'),
        )

        fixed = text
        for pattern, replacement in replacements:
            fixed = re.sub(pattern, replacement, fixed)
        return fixed

    def _extract_url_candidate(self, raw_text: str) -> str | None:
        stripped = raw_text.strip()
        direct_match = re.match(r'^(https?://\S+|www\.\S+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?)$', stripped)
        if direct_match:
            return self._normalize_url(direct_match.group(1))

        pattern = (
            r"^\s*(?:abre|abrir|abriendo|ve a|ir a|entra a|visita|abre la pagina|abre la web)\s+"
            r"(?P<url>https?://\S+|www\.\S+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?)\s*$"
        )
        match = re.match(pattern, stripped, flags=re.IGNORECASE)
        if not match:
            return None

        return self._normalize_url(match.group('url'))

    def _normalize_url(self, url: str) -> str:
        cleaned = url.strip().rstrip('.,;')
        if cleaned.lower().startswith(('http://', 'https://')):
            return cleaned
        return f'https://{cleaned}'

    def _convert_to_seconds(self, amount: int, unit: str) -> int:
        multipliers = {
            'segundo': 1,
            'segundos': 1,
            'minuto': 60,
            'minutos': 60,
            'min': 60,
            'mins': 60,
            'hora': 3600,
            'horas': 3600,
            'h': 3600,
        }
        return amount * multipliers.get(unit, 0)

    def _matches_any_phrase(self, text: str, phrases: tuple[str, ...]) -> bool:
        for phrase in phrases:
            pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            if re.search(pattern, text):
                return True
        return False

    def _matches_system_action(self, text: str, action: str) -> bool:
        action_patterns = {
            'restart': r'(?:reinicia|reiniciar|reinicie)',
            'shutdown': r'(?:apaga|apagar|apague)',
        }
        target_pattern = r'(?:\s+(?:(?:el|la|mi|tu|su)\s+)?(?:equipo|laptop|computadora|pc|ordenador|computador|compu|sistema))?'
        command = self._strip_polite_suffix(self._strip_conversational_prefix(text.rstrip('.:-').strip()))
        return re.fullmatch(rf'{action_patterns[action]}{target_pattern}', command) is not None

    def _build_alias_index(self, aliases: dict[str, str]) -> dict[str, dict[str, str]]:
        index: dict[str, dict[str, str]] = {}
        for label, target in aliases.items():
            normalized_label = self._normalize(label)
            if normalized_label:
                index[normalized_label] = {'label': label, 'target': target}
        return index
