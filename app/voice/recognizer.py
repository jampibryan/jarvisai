from __future__ import annotations

from typing import Any

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - depends on local environment
    sr = None


class SpeechRecognizer:
    def __init__(self, language: str = 'es-PE') -> None:
        self.language = language
        self.available = sr is not None
        self.recognizer = sr.Recognizer() if sr is not None else None

    def transcribe(self, audio: Any) -> str:
        if sr is None or self.recognizer is None:
            raise RuntimeError(
                "Las dependencias de reconocimiento no estan instaladas. Instala SpeechRecognition."
            )

        return self.recognizer.recognize_google(audio, language=self.language)
