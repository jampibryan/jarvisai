from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from time import monotonic


_SKIP = {
    '.git', '.tmp', '.pytest_tmp', '__pycache__', '.venv', 'venv', 'node_modules',
    '$recycle.bin', 'system volume information', 'appdata', 'windows',
}
_QUERY_CONNECTORS = {'guion', 'guiones', 'de', 'del', 'la', 'el', 'los', 'las', 'mi', 'mis', 'un', 'una'}


@dataclass(frozen=True)
class FileSearchResult:
    query: str
    paths: tuple[Path, ...]
    incomplete: bool = False

    def speech(self) -> str:
        if not self.paths:
            if self.incomplete:
                return f'No encontré «{self.query}» en las carpetas que alcancé a revisar. Puedes darme más detalles.'
            return f'No encontré archivos que coincidan con «{self.query}».'
        if len(self.paths) == 1:
            return f'Encontré {self.paths[0].stem}. Puedes decir «abre el resultado».'
        return f'Encontré {len(self.paths)} resultados. El primero es {self.paths[0].stem}. Puedes decir «abre el primero».'

    def display(self) -> str:
        if not self.paths:
            return self.speech()
        results = '\n'.join(f'{index}. {path}' for index, path in enumerate(self.paths, 1))
        suffix = '\nLa búsqueda se detuvo al alcanzar el límite de tiempo.' if self.incomplete else ''
        return f'Encontre estos archivos para «{self.query}»:\n{results}{suffix}'


def find_files(query: str, roots: list[Path], limit: int = 5, seconds: float = 3.0) -> FileSearchResult:
    query_words = _words(query)
    tokens = [word for word in query_words if word not in _QUERY_CONNECTORS] or query_words
    if not tokens:
        return FileSearchResult(query, ())
    phrase = ' '.join(tokens)

    deadline = monotonic() + seconds
    matches: dict[Path, int] = {}
    visited: set[Path] = set()
    incomplete = False
    exact_count = 0
    for root in roots:
        for folder, directories, filenames in os.walk(root):
            if monotonic() >= deadline:
                incomplete = True
                break
            current = Path(folder)
            if current in visited:
                directories.clear()
                continue
            visited.add(current)
            directories[:] = [
                name for name in directories
                if name.lower() not in _SKIP and not name.startswith(('.', 'pytest-cache-files-', 'jarvis-tests-'))
            ]
            for filename in filenames:
                if monotonic() >= deadline:
                    incomplete = True
                    break
                file = current / filename
                stem = ' '.join(_words(file.stem))
                if stem == phrase:
                    matches[file] = 4
                    exact_count += 1
                    if exact_count >= limit:
                        break
                    continue
                words = _words(filename)
                normalized = ' '.join(words)
                if phrase in normalized:
                    matches[file] = 3
                elif all(token in normalized for token in tokens):
                    matches[file] = 2
                elif all(any(_close_word(token, word) for word in words) for token in tokens):
                    matches[file] = 1
            if incomplete or exact_count >= limit:
                break
        if incomplete or exact_count >= limit:
            break

    ranked = sorted(matches, key=matches.__getitem__, reverse=True)[:limit]
    return FileSearchResult(query, tuple(ranked), incomplete)


def _words(text: str) -> list[str]:
    ascii_text = ''.join(char for char in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(char))
    return re.findall(r'[^\W_]+', ascii_text)


def _close_word(query: str, word: str) -> bool:
    if query == word:
        return True
    return (
        len(query) >= 5 and query[0] == word[0] and abs(len(query) - len(word)) <= 2
        and SequenceMatcher(None, query, word).ratio() >= 0.8
    )
