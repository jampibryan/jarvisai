from io import BytesIO
from struct import pack
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.voice.listener import VoiceCaptureInterrupted, VoiceListener, sr


def test_voice_listener_configures_recognizer_thresholds() -> None:
    listener = VoiceListener.__new__(VoiceListener)
    listener.timeout = 5
    listener.phrase_time_limit = 8
    listener.ambient_duration = 0.8
    listener.pause_threshold = 1.1
    listener.non_speaking_duration = 0.4
    listener.dynamic_energy_threshold = False
    listener.energy_threshold = 450
    listener.recognizer = SimpleNamespace(
        dynamic_energy_threshold=True,
        energy_threshold=300,
        pause_threshold=0.8,
        non_speaking_duration=0.2,
    )

    listener._configure_recognizer()

    assert listener.recognizer.dynamic_energy_threshold is False
    assert listener.recognizer.energy_threshold == 450
    assert listener.recognizer.pause_threshold == 1.1
    assert listener.recognizer.non_speaking_duration == 0.4


def test_capture_keeps_speech_after_a_pause_longer_than_the_old_threshold() -> None:
    first = pack('<h', 1_000)
    second = pack('<h', 2_000)
    silence = b'\x00\x00'
    pcm = first * 4_000 + silence * 9_600 + second * 4_000 + silence * 16_000

    class BufferedSource(sr.AudioSource):
        SAMPLE_RATE = 8_000
        SAMPLE_WIDTH = 2
        CHUNK = 800

        def __init__(self):
            samples = BytesIO(pcm)
            self.stream = SimpleNamespace(read=lambda frames: samples.read(frames * self.SAMPLE_WIDTH))

    before = VoiceListener(pause_threshold=0.8, dynamic_energy_threshold=False).listen_once(source=BufferedSource())
    levels = []
    after = VoiceListener(dynamic_energy_threshold=False).listen_once(source=BufferedSource(), on_level=levels.append)

    assert second * 800 not in before.frame_data
    assert first * 800 in after.frame_data
    assert second * 800 in after.frame_data
    assert 0.0 in levels
    assert max(levels) > 0.8


def test_voice_capture_yields_to_a_desktop_control_without_reading_more_audio() -> None:
    class BufferedSource(sr.AudioSource):
        SAMPLE_RATE = 8_000
        SAMPLE_WIDTH = 2
        CHUNK = 800

        def __init__(self):
            self.stream = Mock()

    source = BufferedSource()
    stream = source.stream
    with pytest.raises(VoiceCaptureInterrupted):
        VoiceListener().listen_once(source=source, interrupt=lambda: True)

    stream.read.assert_not_called()
    assert source.stream is stream


def test_capture_keeps_quiet_words_after_a_two_second_pause() -> None:
    loud = pack('<h', 4_000)
    quiet = pack('<h', 260)
    silence = b'\x00\x00'
    pcm = loud * 4_800 + silence * 16_000 + quiet * 4_800 + silence * 24_000

    class BufferedSource(sr.AudioSource):
        SAMPLE_RATE = 8_000
        SAMPLE_WIDTH = 2
        CHUNK = 800

        def __init__(self):
            samples = BytesIO(pcm)
            self.stream = SimpleNamespace(read=lambda frames: samples.read(frames * self.SAMPLE_WIDTH))

    listener = VoiceListener()
    audio = listener.listen_once(source=BufferedSource())

    assert quiet * 800 in audio.frame_data
    assert listener.recognizer.energy_threshold == listener.energy_threshold
    assert listener.recognizer.dynamic_energy_threshold
