from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.voice.speaker import Speaker


def _token(name: str, language: str, gender: str):
    attributes = {'Language': language, 'Gender': gender}
    return SimpleNamespace(Id=name, GetDescription=lambda: name, GetAttribute=attributes.__getitem__)


def _engine(*voices, completed=True):
    return SimpleNamespace(
        Voice=voices[0], GetVoices=lambda: voices,
        Speak=Mock(), WaitUntilDone=Mock(return_value=completed),
    )


def test_speaker_prefers_male_voice_when_available() -> None:
    engine = _engine(_token('Zira', '409', 'Female'), _token('David', '409', 'Male'))
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker()

    assert speaker.selected_voice_id == 'David'
    assert speaker.selected_voice_gender == 'male'


def test_speaker_falls_back_to_first_voice_when_male_voice_is_missing() -> None:
    engine = _engine(_token('Zira', '409', 'Female'), _token('Helena', 'c0a', 'Female'))
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker()

    assert speaker.selected_voice_name == 'Zira'


def test_speaker_uses_spanish_even_when_only_english_has_preferred_gender() -> None:
    engine = _engine(_token('David', '409', 'Male'), _token('Helena', 'c0a', 'Female'))
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker(preferred_language='es-PE')

    assert speaker.selected_voice_id == 'Helena'
    assert speaker.speak('¿Cómo se llama el archivo?')
    engine.Speak.assert_called_once_with('¿Cómo se llama el archivo?', 17)
    engine.WaitUntilDone.assert_called_once_with(30_000)


def test_speaker_does_not_report_timed_out_audio_as_played() -> None:
    engine = _engine(_token('Helena', 'c0a', 'Female'), completed=False)
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker()

    assert not speaker.speak('Hola.')
    assert not speaker.available
    assert engine.Speak.call_args.args == ('', 19)


def test_speaker_can_switch_voice_and_animate_escaped_text() -> None:
    engine = _engine(_token('Helena', 'c0a', 'Female'), _token('Zira', '409', 'Female'))
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker(preferred_language='es-PE')

    assert speaker.available_voices() == (('Helena', 'Helena'), ('Zira', 'Zira'))
    natural_rate = engine.Rate
    speaker.configure(voice_id='Zira', style='Animada')
    assert speaker.selected_voice_id == 'Zira'
    assert engine.Rate > natural_rate
    assert speaker.speak('Hola & <adiós>')
    engine.Speak.assert_called_once_with('<pitch absmiddle="3">Hola &amp; &lt;adiós&gt;</pitch>', 9)


def test_speaker_emits_one_pulse_per_word_position() -> None:
    engine = _engine(_token('Helena', 'c0a', 'Female'))
    engine.Status = SimpleNamespace(InputWordPosition=2)
    engine.WaitUntilDone.side_effect = [False, False, True]
    with patch('app.voice.speaker._create_windows_voice', return_value=engine):
        speaker = Speaker()
    speaker.on_word = Mock()

    assert speaker.speak('Hola.')
    speaker.on_word.assert_called_once()
