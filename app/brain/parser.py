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
        normalized = self._normalize(raw_text)

        if any(term in normalized for term in {"salir", "terminar", "cerrar asistente"}):
            return ParsedCommand(raw_text, normalized, Intent.EXIT)

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

        if entity in {"chrome", "vscode", "excel", "power_bi", "whatsapp"} and (
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
                    metadata={"source": "custom_path", "target": alias["target"], "label": alias["label"]},
                )

        for candidate in alias_candidates:
            if candidate in self.custom_apps and (has_open_trigger or looks_like_short_command):
                alias = self.custom_apps[candidate]
                return ParsedCommand(
                    raw_text,
                    normalized,
                    Intent.OPEN_APP,
                    entity=candidate,
                    metadata={"source": "custom_app", "target": alias["target"], "label": alias["label"]},
                )

        return ParsedCommand(raw_text, normalized, Intent.UNKNOWN)

    def _normalize(self, raw_text: str) -> str:
        no_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", raw_text.lower())
            if not unicodedata.combining(char)
        )
        clean = re.sub(r"[^a-z0-9\s:]", " ", no_accents)
        return re.sub(r"\s+", " ", clean).strip()

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
