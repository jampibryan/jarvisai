from __future__ import annotations

import locale
import logging
from collections.abc import Callable
from math import log
from time import monotonic
from typing import Any
from xml.sax.saxutils import escape


logger = logging.getLogger('JarvisAI')
_ASYNC = 1
_PURGE = 2
_PLAIN_TEXT = 16
_XML = 8
VOICE_STYLES = {'Natural': (0, 0), 'Animada': (2, 3), 'Serena': (-2, -1)}


def _create_windows_voice() -> Any:
    from win32com.client import Dispatch

    return Dispatch('SAPI.SpVoice')


class Speaker:
    def __init__(self, preferred_gender: str = 'male', preferred_rate: int = 175, preferred_language: str = '') -> None:
        self.engine: Any = None
        self.error = ''
        self.preferred_gender = preferred_gender.lower()
        self.preferred_rate = preferred_rate
        self.preferred_language = preferred_language.lower().split('-', 1)[0]
        self.selected_voice_id = ''
        self.selected_voice_name = ''
        self.selected_voice_gender = 'unknown'
        self.voice_id = ''
        self.style = 'Natural'
        self.on_word: Callable[[], None] | None = None
        self._initialize()

    @property
    def available(self) -> bool:
        return self.engine is not None

    def _initialize(self) -> None:
        try:
            self.engine = _create_windows_voice()
            self._select_preferred_voice()
            self._apply_rate()
            self.error = ''
        except Exception as exc:
            self.engine = None
            self.error = str(exc)

    def _select_preferred_voice(self) -> None:
        voices = list(self.engine.GetVoices())
        matching = [
            voice for voice in voices
            if self.preferred_language and any(
                locale.windows_locale.get(int(code, 16), '').lower().split('_', 1)[0] == self.preferred_language
                for code in voice.GetAttribute('Language').split(';') if code
            )
        ]
        candidates = matching or voices
        requested = next((voice for voice in voices if voice.Id == self.voice_id), None)
        if requested is not None:
            self.engine.Voice = requested
        elif candidates:
            self.engine.Voice = next((voice for voice in candidates if voice.GetAttribute('Gender').lower() == self.preferred_gender), candidates[0])
        selected = self.engine.Voice
        self.selected_voice_id = selected.Id
        self.selected_voice_name = selected.GetDescription()
        self.selected_voice_gender = selected.GetAttribute('Gender').lower() or 'unknown'

    def available_voices(self) -> tuple[tuple[str, str], ...]:
        if self.engine is None:
            return ()
        return tuple((voice.Id, voice.GetDescription()) for voice in self.engine.GetVoices())

    def configure(self, *, voice_id: str | None = None, style: str | None = None) -> None:
        if voice_id is not None:
            self.voice_id = voice_id
        if style in VOICE_STYLES:
            self.style = style
        if self.engine is not None:
            if voice_id is not None:
                self._select_preferred_voice()
            self._apply_rate()

    def _apply_rate(self) -> None:
        if self.preferred_rate > 0:
            offset, _ = VOICE_STYLES[self.style]
            rate = round(log(self.preferred_rate / 156.63, 1.11))
            self.engine.Rate = max(-10, min(10, rate + offset))

    def speak(self, text: str) -> bool:
        if self.engine is None:
            self._initialize()
        if self.engine is None:
            logger.warning('No pude inicializar la voz de Windows: %s', self.error)
            return False

        try:
            _, pitch = VOICE_STYLES[self.style]
            if pitch:
                self.engine.Speak(f'<pitch absmiddle="{pitch}">{escape(text)}</pitch>', _ASYNC | _XML)
            else:
                self.engine.Speak(text, _ASYNC | _PLAIN_TEXT)
            if self._wait_for_audio():
                return True
            self.engine.Speak('', _ASYNC | _PURGE | _PLAIN_TEXT)
            logger.warning('La reproducción de voz de Windows no terminó a tiempo.')
        except Exception:
            logger.exception('Fallo al reproducir audio con la voz de Windows')
        self.engine = None
        return False

    def _wait_for_audio(self) -> bool:
        if self.on_word is None:
            return bool(self.engine.WaitUntilDone(30_000))

        deadline = monotonic() + 30
        last_position = None
        while monotonic() < deadline:
            if self.engine.WaitUntilDone(45):
                return True
            try:
                position = self.engine.Status.InputWordPosition
            except Exception:
                return bool(self.engine.WaitUntilDone(max(0, int((deadline - monotonic()) * 1000))))
            if position != last_position:
                self.on_word()
                last_position = position
        return False
