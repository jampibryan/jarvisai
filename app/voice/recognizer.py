from __future__ import annotations

import re
from importlib.util import find_spec
from os import cpu_count
from pathlib import Path
from typing import Any

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - depends on local environment
    sr = None


class SpeechRecognizer:
    def __init__(
        self, language: str = 'es-PE', enable_offline_fallback: bool = True, *,
        engine: str = 'auto', whisper_path: Path | None = None,
    ) -> None:
        self.language = language
        self.enable_offline_fallback = enable_offline_fallback
        self.engine = engine
        self.whisper_path = whisper_path
        self._whisper = None
        self.recognizer = sr.Recognizer() if sr is not None else None
        if self.recognizer is not None:
            self.recognizer.operation_timeout = 7
        self.last_backend = ''
        self.available_backends = self._build_available_backends()
        self.available = sr is not None and self.recognizer is not None and bool(self.available_backends)

    def transcribe(self, audio: Any) -> str:
        if sr is None or self.recognizer is None:
            raise RuntimeError(
                "Las dependencias de reconocimiento no estan instaladas. Instala SpeechRecognition."
            )

        errors: list[Exception] = []

        for backend in self.available_backends:
            try:
                text = self._transcribe_with_backend(audio, backend)
                self.last_backend = backend
                return text
            except Exception as exc:
                errors.append(exc)
                continue

        if errors:
            raise errors[-1]

        raise RuntimeError('No hay motores de reconocimiento de voz disponibles.')

    def backend_summary(self) -> str:
        if not self.available_backends:
            return 'ninguno'
        labels = {
            'whisper': 'Whisper local (sin Internet)',
            'google': 'Google online',
            'sphinx': 'Sphinx offline',
        }
        return ' + '.join(labels.get(item, item) for item in self.available_backends)

    def _build_available_backends(self) -> list[str]:
        if sr is None or self.recognizer is None:
            return []

        if self.engine != 'google':
            model_ready = self.whisper_path is not None and all(
                (self.whisper_path / name).is_file() for name in ('model.bin', 'tokenizer.json', 'config.json')
            )
            if model_ready and find_spec('faster_whisper') is not None:
                return ['whisper']
            if self.engine == 'whisper':
                return []
        backends = ['google']
        if self.enable_offline_fallback and self._is_sphinx_available():
            backends.append('sphinx')
        return backends

    def _transcribe_with_backend(self, audio: Any, backend: str) -> str:
        if backend == 'whisper':
            return self._transcribe_whisper(audio)
        if backend == 'google':
            return self.recognizer.recognize_google(audio, language=self.language)

        if backend == 'sphinx':
            offline_language = self._offline_language()
            try:
                return self.recognizer.recognize_sphinx(audio, language=offline_language)
            except TypeError:
                return self.recognizer.recognize_sphinx(audio)

        raise RuntimeError(f'Backend de voz no soportado: {backend}')

    def _transcribe_whisper(self, audio: Any) -> str:
        import numpy as np
        from faster_whisper import WhisperModel

        if self._whisper is None:
            self._whisper = WhisperModel(
                str(self.whisper_path), device='cpu', compute_type='int8',
                cpu_threads=min(4, cpu_count() or 1), local_files_only=True,
            )
        pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
        waveform = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
        segments, _ = self._whisper.transcribe(
            waveform, language=self.language.lower().split('-', 1)[0],
            beam_size=3, condition_on_previous_text=False, without_timestamps=True,
        )
        text = ' '.join(segment.text.strip() for segment in segments).strip()
        if self.language.lower().startswith('es'):
            text = re.sub(r'\bmi(tesis|archivo|documento|presentaci[oó]n)\b', r'mi \1', text, flags=re.IGNORECASE)
        if not text:
            raise sr.UnknownValueError()
        return text

    def _offline_language(self) -> str:
        normalized = (self.language or '').strip().lower()
        if normalized.startswith('es'):
            return 'es-ES'
        if normalized.startswith('en'):
            return 'en-US'
        return self.language

    def _is_sphinx_available(self) -> bool:
        if self.recognizer is None or not hasattr(self.recognizer, 'recognize_sphinx'):
            return False

        try:
            import pocketsphinx  # noqa: F401
        except ImportError:
            return False

        return True
