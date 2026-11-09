from pathlib import Path
from tempfile import gettempdir
from unittest.mock import patch
from uuid import uuid4

from app.actions.productivity_actions import create_quick_note, open_url, search_files, start_timer


TEMP_ROOT = Path(gettempdir())


def _build_temp_root() -> Path:
    root = TEMP_ROOT / f'jarvis_productivity_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cleanup_dir(root: Path) -> None:
    for path in sorted(root.rglob('*'), reverse=True):
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                path.rmdir()
        except OSError:
            pass
    try:
        root.rmdir()
    except OSError:
        pass


def test_open_url_uses_webbrowser() -> None:
    with patch('app.actions.productivity_actions.webbrowser.open', return_value=True) as open_browser:
        response = open_url('https://openai.com')

    open_browser.assert_called_once_with('https://openai.com', new=2)
    assert response == 'Abriendo OpenAI.'


def test_create_quick_note_writes_file() -> None:
    root = _build_temp_root()
    try:
        response = create_quick_note(root, 'comprar leche')

        created_files = list(root.glob('*.txt'))
        assert len(created_files) == 1
        assert created_files[0].read_text(encoding='utf-8').strip() == 'comprar leche'
        assert 'Nota guardada en' in response
    finally:
        _cleanup_dir(root)


def test_search_files_returns_matching_files() -> None:
    root = _build_temp_root()
    try:
        docs = root / 'docs'
        docs.mkdir()
        target = docs / 'Presupuesto Final.xlsx'
        target.write_text('contenido', encoding='utf-8')

        response = search_files('presupuesto final', [root])

        assert 'Encontre estos archivos' in response
        assert str(target) in response
    finally:
        _cleanup_dir(root)


def test_search_files_matches_a_short_word_with_one_misheard_letter(tmp_path) -> None:
    thesis = tmp_path / 'Tesis - Diapositivas.pptx'
    thesis.touch()
    assert str(thesis) in search_files('tecis', [tmp_path])


def test_start_timer_schedules_background_timer() -> None:
    fake_timer = None

    class FakeTimer:
        def __init__(self, seconds, callback, kwargs=None):
            nonlocal fake_timer
            self.seconds = seconds
            self.callback = callback
            self.kwargs = kwargs or {}
            self.daemon = False
            self.started = False
            fake_timer = self

        def start(self):
            self.started = True

    with patch('app.actions.productivity_actions.threading.Timer', FakeTimer):
        response = start_timer(120, label='descansar')

    assert fake_timer is not None
    assert fake_timer.seconds == 120
    assert fake_timer.kwargs == {'duration_seconds': 120, 'label': 'descansar'}
    assert fake_timer.daemon is True
    assert fake_timer.started is True
    assert response == 'Temporizador iniciado por 2 minutos para descansar.'
