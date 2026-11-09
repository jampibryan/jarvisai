from app.voice.recognizer import SpeechRecognizer
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import speech_recognition as sr


def test_speech_recognizer_falls_back_to_sphinx_when_google_fails() -> None:
    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.language = 'es-PE'
    recognizer.enable_offline_fallback = True
    recognizer.last_backend = ''
    recognizer.available_backends = ['google', 'sphinx']

    calls: list[str] = []

    class FakeRecognizer:
        def recognize_google(self, audio, language='es-PE'):
            calls.append(f'google:{language}')
            raise RuntimeError('google down')

        def recognize_sphinx(self, audio, language='es-ES'):
            calls.append(f'sphinx:{language}')
            return 'jarvis abre chrome'

    recognizer.recognizer = FakeRecognizer()

    transcript = recognizer.transcribe(audio='fake-audio')

    assert transcript == 'jarvis abre chrome'
    assert recognizer.last_backend == 'sphinx'
    assert calls == ['google:es-PE', 'sphinx:es-ES']


def test_speech_recognizer_reports_backend_summary() -> None:
    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.available_backends = ['google', 'sphinx']

    assert recognizer.backend_summary() == 'Google online + Sphinx offline'


def test_speech_recognizer_detects_missing_sphinx_dependency() -> None:
    recognizer = SpeechRecognizer.__new__(SpeechRecognizer)
    recognizer.recognizer = SimpleNamespace(recognize_sphinx=lambda audio: 'ok')

    assert recognizer._is_sphinx_available() is False


def test_whisper_is_selected_and_silence_is_not_sent_to_google(tmp_path) -> None:
    for name in ('model.bin', 'tokenizer.json', 'config.json'):
        (tmp_path / name).touch()
    with patch('app.voice.recognizer.find_spec', return_value=object()):
        recognizer = SpeechRecognizer(engine='auto', whisper_path=tmp_path)

    assert recognizer.available_backends == ['whisper']
    with patch.object(recognizer, '_transcribe_with_backend', side_effect=sr.UnknownValueError) as transcribe:
        with pytest.raises(sr.UnknownValueError):
            recognizer.transcribe('audio')
    transcribe.assert_called_once_with('audio', 'whisper')
