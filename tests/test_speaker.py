from types import SimpleNamespace

from app.voice.speaker import Speaker


class FakeEngine:
    def __init__(self, voices: list[object]) -> None:
        self._voices = voices
        self.properties: dict[str, str] = {}

    def getProperty(self, name: str):
        if name == 'voices':
            return self._voices
        return self.properties.get(name)

    def setProperty(self, name: str, value: str) -> None:
        self.properties[name] = value

    def say(self, text: str) -> None:
        self.properties['last_text'] = text

    def runAndWait(self) -> None:
        self.properties['ran'] = '1'


def test_speaker_prefers_male_voice_when_available() -> None:
    speaker = Speaker.__new__(Speaker)
    speaker.engine = FakeEngine(
        [
            SimpleNamespace(id='voice-zira', name='Microsoft Zira Desktop', gender='female'),
            SimpleNamespace(id='voice-david', name='Microsoft David Desktop', gender='male'),
        ]
    )
    speaker.preferred_gender = 'male'
    speaker.selected_voice_id = ''
    speaker.selected_voice_name = ''
    speaker.selected_voice_gender = 'unknown'

    speaker._select_preferred_voice()

    assert speaker.engine.properties['voice'] == 'voice-david'
    assert speaker.selected_voice_gender == 'male'


def test_speaker_falls_back_to_first_voice_when_male_voice_is_missing() -> None:
    speaker = Speaker.__new__(Speaker)
    speaker.engine = FakeEngine(
        [
            SimpleNamespace(id='voice-zira', name='Microsoft Zira Desktop', gender='female'),
            SimpleNamespace(id='voice-helena', name='Helena', gender='female'),
        ]
    )
    speaker.preferred_gender = 'male'
    speaker.selected_voice_id = ''
    speaker.selected_voice_name = ''
    speaker.selected_voice_gender = 'unknown'

    speaker._select_preferred_voice()

    assert speaker.engine.properties['voice'] == 'voice-zira'
    assert speaker.selected_voice_name == 'Microsoft Zira Desktop'
