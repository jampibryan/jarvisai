from __future__ import annotations

import re
import unicodedata

from app.brain.intents import Intent, ParsedCommand


class CommandParser:
    def __init__(
        self,
        custom_paths: dict[str, str] | None = None,
        custom_apps: dict[str, str] | None = None,
    ) -> None:
        self.custom_paths = self._build_alias_index(custom_paths or {})
        self.custom_apps = self._build_alias_index(custom_apps or {})

    def parse(self, raw_text: str) -> ParsedCommand:
        working_text = self._strip_assistant_prefix(raw_text)

        learn_match = self._match_alias_command(working_text, {"aprende", "agrega", "recuerda"})
        if learn_match:
            return learn_match

        replace_match = self._match_alias_command(working_text, {"reemplaza", "actualiza", "cambia"})
        if replace_match:
            return replace_match

        normalized = self._normalize(working_text)

        if normalized in {"si", "sí", "confirmar", "confirma", "ok", "aceptar"}:
            return ParsedCommand(raw_text, normalized, Intent.CONFIRM)

        if normalized in {"no", "cancelar", "cancela"}:
            return ParsedCommand(raw_text, normalized, Intent.CANCEL)

        if any(term in normalized for term in {"salir", "terminar", "cerrar asistente"}):
            return ParsedCommand(raw_text, normalized, Intent.EXIT)

        if any(term in normalized for term in {"comandos", "ayuda", "que puedes hacer"}):
            return ParsedCommand(raw_text, normalized, Intent.LIST_COMMANDS)

        if any(term in normalized for term in {"metricas", "metrica", "estadisticas", "resumen"}):
            return ParsedCommand(raw_text, normalized, Intent.SHOW_METRICS)

        if self._matches_restart(normalized):
            return ParsedCommand(raw_text, normalized, Intent.RESTART_COMPUTER)

        if self._matches_shutdown(normalized):
            return ParsedCommand(raw_text, normalized, Intent.SHUTDOWN_COMPUTER)

        if "hora" in normalized:
            return ParsedCommand(raw_text, normalized, Intent.GET_TIME)

        if "fecha" in normalized:
            return ParsedCommand(raw_text, normalized, Intent.GET_DATE)

        entity = self._extract_open_entity(normalized)
        has_open_trigger = any(
            trigger in normalized for trigger in {"abre", "abrir", "abreme", "ejecuta", "inicia", "iniciar"}
        )
        looks_like_short_command = 1 <= len(normalized.split()) <= 4
        alias_candidates = self._extract_alias_candidates(normalized)

        if entity in {"drive_d", "downloads", "documents"} and (has_open_trigger or looks_like_short_command):
            return ParsedCommand(raw_text, normalized, Intent.OPEN_PATH, entity=entity)

        if entity in {"chrome", "vscode", "excel", "power_bi", "whatsapp", "cmd", "explorer"} and (
            has_open_trigger or looks_like_short_command
        ):
            return ParsedCommand(raw_text, normalized, Intent.OPEN_APP, entity=entity)

        for candidate in alias_candidates:
            if candidate in self.custom_paths and (has_open_trigger or looks_like_short_command):
                alias = self.custom_paths[candidate]
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_PATH,
                    entity=candidate,
                    metadata={
                        "source": "custom_path",
                        "target": alias["target"],
                        "label": alias["label"],
                    },
                )

        for candidate in alias_candidates:
            if candidate in self.custom_apps and (has_open_trigger or looks_like_short_command):
                alias = self.custom_apps[candidate]
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_APP,
                    entity=candidate,
                    metadata={
                        "source": "custom_app",
                        "target": alias["target"],
                        "label": alias["label"],
                    },
                )

        return ParsedCommand(raw_text, normalized, Intent.UNKNOWN)

    def _match_alias_command(self, raw_text: str, verbs: set[str]) -> ParsedCommand | None:
        explicit_match = self._match_explicit_alias_command(raw_text, verbs)
        if explicit_match:
            return explicit_match
        return self._match_natural_alias_command(raw_text, verbs)

    def _match_explicit_alias_command(self, raw_text: str, verbs: set[str]) -> ParsedCommand | None:
        pattern = r"^\s*(?P<verb>\w+)\s+(?P<kind>ruta|app)\s+(?P<label>.+?)\s*=\s*(?P<target>.+?)\s*$"
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        verb = self._normalize(match.group("verb"))
        if verb not in verbs:
            return None

        alias_kind = self._normalize(match.group("kind"))
        label = match.group("label").strip()
        target = match.group("target").strip()
        return self._build_alias_command(raw_text, verb, alias_kind, label, target)

    def _match_natural_alias_command(self, raw_text: str, verbs: set[str]) -> ParsedCommand | None:
        pattern = (
            r"^\s*(?P<verb>\w+)\s+(?:que\s+)?(?P<label>.+?)\s+"
            r"(?P<link>abre|es|sea|significa)\s+(?P<target>.+?)\s*$"
        )
        match = re.match(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            return None

        verb = self._normalize(match.group("verb"))
        if verb not in verbs:
            return None

        label = match.group("label").strip(" ,")
        target = match.group("target").strip()
        link = self._normalize(match.group("link"))
        alias_kind = self._infer_alias_kind(target, link)
        return self._build_alias_command(raw_text, verb, alias_kind, label, target)

    def _build_alias_command(
        self,
        raw_text: str,
        verb: str,
        alias_kind: str,
        label: str,
        target: str,
    ) -> ParsedCommand:
        normalized = self._normalize(raw_text)
        intent = Intent.LEARN_ALIAS if verb in {"aprende", "agrega", "recuerda"} else Intent.REPLACE_ALIAS
        return ParsedCommand(
            raw_text,
            normalized,
            intent,
            entity=self._normalize(label),
            metadata={
                "alias_kind": alias_kind,
                "label": label,
                "target": target,
            },
        )

    def _infer_alias_kind(self, target: str, link: str) -> str:
        normalized_target = self._normalize(target)
        if link == "abre":
            if self._looks_like_path(target):
                return "ruta"
            if self._extract_open_entity(normalized_target) in {"chrome", "vscode", "excel", "power_bi", "whatsapp", "cmd", "explorer"}:
                return "app"
            return "ruta"
        return "app"

    def _looks_like_path(self, target: str) -> bool:
        return bool(re.search(r"[a-zA-Z]:\\|\\|/|\.pdf$|\.txt$|\.docx?$|\.xlsx?$", target.strip(), re.IGNORECASE))

    def _strip_assistant_prefix(self, raw_text: str) -> str:
        stripped = raw_text.strip()
        return re.sub(r"^jarvis\s*[,;:\-]?\s*", "", stripped, flags=re.IGNORECASE)

    def _normalize(self, raw_text: str) -> str:
        no_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", raw_text.lower())
            if not unicodedata.combining(char)
        )
        clean = re.sub(r"[^a-z0-9\s:\\\.-]", " ", no_accents)
        return re.sub(r"\s+", " ", clean).strip()

    def _matches_restart(self, text: str) -> bool:
        return any(term in text for term in {"reinicia", "reiniciar", "reinicia el equipo", "reinicia la laptop"})

    def _matches_shutdown(self, text: str) -> bool:
        return any(term in text for term in {"apaga", "apagar", "apaga la laptop", "apaga el equipo"})

    def _extract_open_entity(self, text: str) -> str:
        path_patterns = [
            (r"\bdisco d\b", "drive_d"),
            (r"\bunidad d\b", "drive_d"),
            (r"\bdescargas\b", "downloads"),
            (r"\bdownloads\b", "downloads"),
            (r"\bdocumentos\b", "documents"),
            (r"\bdocuments\b", "documents"),
            (r"^(d|d:)$", "drive_d"),
        ]
        app_patterns = [
            (r"\bgoogle chrome\b", "chrome"),
            (r"\bchrome\b", "chrome"),
            (r"\bvisual studio code\b", "vscode"),
            (r"\bvs code\b", "vscode"),
            (r"\bvscode\b", "vscode"),
            (r"\bcode\b", "vscode"),
            (r"\bexcel\b", "excel"),
            (r"\bpower bi\b", "power_bi"),
            (r"\bwhatsapp\b", "whatsapp"),
            (r"\bterminal\b", "cmd"),
            (r"\bconsola\b", "cmd"),
            (r"\bexplorador\b", "explorer"),
            (r"\barchivos\b", "explorer"),
        ]

        for pattern, value in path_patterns:
            if re.search(pattern, text):
                return value

        for pattern, value in app_patterns:
            if re.search(pattern, text):
                return value

        return ""

    def _extract_alias_candidates(self, text: str) -> list[str]:
        stripped = re.sub(r"^(abre|abrir|abreme|ejecuta|inicia|iniciar)\s+", "", text).strip()
        simplified = re.sub(r"^(el|la|los|las|mi|mis|un|una)\s+", "", stripped).strip()

        candidates: list[str] = []
        for value in [stripped, simplified, text]:
            if value and value not in candidates:
                candidates.append(value)
        return candidates

    def _build_alias_index(self, aliases: dict[str, str]) -> dict[str, dict[str, str]]:
        index: dict[str, dict[str, str]] = {}
        for label, target in aliases.items():
            normalized_label = self._normalize(label)
            if normalized_label:
                index[normalized_label] = {"label": label, "target": target}
        return index
