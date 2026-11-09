from __future__ import annotations

from collections.abc import Callable
from math import sqrt
from typing import Any

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - depends on local environment
    sr = None


class VoiceCaptureInterrupted(Exception):
    pass


class _InterruptibleStream:
    def __init__(
        self, read: Callable[[int], bytes], interrupt: Callable[[], bool], on_level: Callable[[float], None] | None,
    ) -> None:
        self._read = read
        self._interrupt = interrupt
        self._on_level = on_level

    def read(self, frames: int) -> bytes:
        if self._interrupt():
            raise VoiceCaptureInterrupted
        audio = self._read(frames)
        if self._on_level is not None and audio and len(audio) % 2 == 0:
            samples = memoryview(audio).cast('h')
            level = sqrt(sum(sample * sample for sample in samples) / len(samples))
            self._on_level(level)
        return audio


class VoiceListener:
    def __init__(
        self,
        timeout: int = 5,
        phrase_time_limit: int = 28,
        ambient_duration: float = 0.8,
        pause_threshold: float = 2.4,
        non_speaking_duration: float = 0.5,
        dynamic_energy_threshold: bool = True,
        energy_threshold: int = 300,
    ) -> None:
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.ambient_duration = ambient_duration
        self.pause_threshold = pause_threshold
        self.non_speaking_duration = non_speaking_duration
        self.dynamic_energy_threshold = dynamic_energy_threshold
        self.energy_threshold = energy_threshold
        self.device_index: int | None = None
        self.available = sr is not None
        self.recognizer = sr.Recognizer() if sr is not None else None
        self._configure_recognizer()

    def list_devices(self) -> list[str]:
        if sr is None:
            return []
        return sr.Microphone.list_microphone_names()

    @staticmethod
    def input_devices() -> dict[int, str]:
        if sr is None:
            return {}
        try:
            audio = sr.Microphone.get_pyaudio().PyAudio()
        except (OSError, AttributeError):
            return {}
        try:
            devices = {}
            for index in range(audio.get_device_count()):
                try:
                    info = audio.get_device_info_by_index(index)
                    input_channels = int(info.get('maxInputChannels', 0))
                except (OSError, TypeError, ValueError):
                    continue
                if input_channels > 0:
                    devices[index] = str(info['name'])
            return devices
        finally:
            audio.terminate()

    def _configure_recognizer(self) -> None:
        if self.recognizer is None:
            return

        self.recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold
        self.recognizer.energy_threshold = self.energy_threshold
        self.recognizer.pause_threshold = self.pause_threshold
        self.recognizer.non_speaking_duration = self.non_speaking_duration

    def calibrate(self) -> None:
        if self.ambient_duration <= 0:
            return
        if sr is None or self.recognizer is None:
            raise RuntimeError('Instala SpeechRecognition y PyAudio para usar el micrófono.')
        with sr.Microphone(device_index=self.device_index) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=self.ambient_duration)

    def listen_once(
        self, source: Any = None, *, calibrate: bool = True, interrupt: Callable[[], bool] | None = None,
        on_level: Callable[[float], None] | None = None,
    ) -> Any:
        if sr is None or self.recognizer is None:
            raise RuntimeError(
                "Las dependencias de voz no estan instaladas. Instala SpeechRecognition y PyAudio."
            )

        if source is not None:
            return self._capture(source, interrupt, on_level)

        with sr.Microphone(device_index=self.device_index) as src:
            if calibrate and self.ambient_duration > 0:
                self.recognizer.adjust_for_ambient_noise(src, duration=self.ambient_duration)
            return self._capture(src, interrupt, on_level)

    def _capture(
        self, source: Any, interrupt: Callable[[], bool] | None, on_level: Callable[[float], None] | None,
    ) -> Any:
        recognizer = self.recognizer
        if recognizer is None:
            raise RuntimeError('Instala SpeechRecognition y PyAudio para usar el micrófono.')

        stream = source.stream
        onset_threshold = None

        def process_level(rms: float) -> None:
            nonlocal onset_threshold
            if self.dynamic_energy_threshold and onset_threshold is None and rms > recognizer.energy_threshold:
                onset_threshold = recognizer.energy_threshold
                recognizer.dynamic_energy_threshold = False
                # Keep quiet syllables after the beginning of a phrase.
                recognizer.energy_threshold = round(onset_threshold * 0.8)
            if on_level is not None:
                on_level(min(1.0, rms / 2400))

        measure = source.SAMPLE_WIDTH == 2 and (self.dynamic_energy_threshold or on_level is not None)
        if interrupt is not None or measure:
            source.stream = _InterruptibleStream(stream.read, interrupt or (lambda: False),
                                                 process_level if measure else None)
        try:
            return recognizer.listen(source, timeout=self.timeout, phrase_time_limit=self.phrase_time_limit)
        finally:
            if onset_threshold is not None:
                recognizer.energy_threshold = onset_threshold
                recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold
            source.stream = stream
