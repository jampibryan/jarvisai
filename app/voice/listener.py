from __future__ import annotations

from typing import Any

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - depends on local environment
    sr = None


class VoiceListener:
    def __init__(self, timeout: int = 5, phrase_time_limit: int = 8) -> None:
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.available = sr is not None
        self.recognizer = sr.Recognizer() if sr is not None else None

    def list_devices(self) -> list[str]:
        if sr is None:
            return []
        return sr.Microphone.list_microphone_names()

    def listen_once(self) -> Any:
        if sr is None or self.recognizer is None:
            raise RuntimeError(
                "Las dependencias de voz no estan instaladas. Instala SpeechRecognition y PyAudio."
            )

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            return self.recognizer.listen(
                source,
                timeout=self.timeout,
                phrase_time_limit=self.phrase_time_limit,
            )
