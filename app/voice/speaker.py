from __future__ import annotations

import re

try:
    import pyttsx3
except ImportError:  # pragma: no cover - depends on local environment
    pyttsx3 = None


class Speaker:
    def __init__(self, preferred_gender: str = 'male') -> None:
        self.engine = None
        self.available = False
        self.error = ''
        self.preferred_gender = preferred_gender
        self.selected_voice_id = ''
        self.selected_voice_name = ''
        self.selected_voice_gender = 'unknown'
        self._initialize()

    def _initialize(self) -> None:
        if pyttsx3 is None:
            self.error = 'pyttsx3 no esta instalado.'
            return

        try:
            self.engine = pyttsx3.init()
            self._select_preferred_voice()
            self.available = True
        except Exception as exc:
            self.engine = None
            self.available = False
            self.error = str(exc)

    def _select_preferred_voice(self) -> None:
        if self.engine is None:
            return

        voices = list(self.engine.getProperty('voices') or [])
        if not voices:
            return

        preferred = self._find_voice_by_gender(voices, self.preferred_gender)
        selected = preferred or voices[0]

        try:
            self.engine.setProperty('voice', selected.id)
        except Exception:
            # Si no se puede fijar la voz, seguimos con la predeterminada.
            selected = voices[0]

        self.selected_voice_id = getattr(selected, 'id', '')
        self.selected_voice_name = getattr(selected, 'name', '')
        self.selected_voice_gender = self._infer_voice_gender(selected)

    def _find_voice_by_gender(self, voices: list[object], preferred_gender: str) -> object | None:
        for voice in voices:
            if self._infer_voice_gender(voice) == preferred_gender:
                return voice
        return None

    def _infer_voice_gender(self, voice: object) -> str:
        fields = [
            str(getattr(voice, 'name', '') or ''),
            str(getattr(voice, 'id', '') or ''),
            str(getattr(voice, 'gender', '') or ''),
        ]
        haystack = ' '.join(fields).lower()
        tokens = set(re.findall(r'[a-z0-9]+', haystack))

        male_keywords = {'male', 'man', 'masculine', 'masculino', 'david', 'mark', 'jorge', 'pablo'}
        female_keywords = {'female', 'woman', 'feminine', 'femenino', 'zira', 'helena', 'sabina'}

        if tokens & female_keywords:
            return 'female'
        if tokens & male_keywords:
            return 'male'
        return 'unknown'

    def speak(self, text: str) -> bool:
        if not self.available or self.engine is None:
            return False

        try:
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception:
            self.available = False
            return False
