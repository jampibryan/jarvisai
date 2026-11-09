from unittest.mock import Mock, patch
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from app.actions.window_actions import Window, WindowActionError, WindowPlan, execute_window_close
from app.brain.intents import Intent
from app.brain.parser import CommandParser
from app.integrations.gmail_client import GmailClient
from app.integrations.youtube_player import YouTubePlayer


@pytest.mark.parametrize(
    ('phrase', 'intent', 'entity', 'metadata'),
    [
        ('Jarvis, abre YouTube y busca la canción Imagine de John Lennon y reprodúcela', Intent.YOUTUBE, '',
         {'query': 'imagine de john lennon', 'play': '1'}),
        ('Abre YouTube. Y busca la canción Persiana americana y reprodúcela.', Intent.YOUTUBE, '',
         {'query': 'persiana americana', 'play': '1'}),
        ('¿Podrías abrir YouTube y buscar Bohemian Rhapsody?', Intent.YOUTUBE, '',
         {'query': 'bohemian rhapsody', 'play': '0'}),
        ('Pon la canción Imagine en YouTube', Intent.YOUTUBE, '', {'query': 'imagine', 'play': '1'}),
        ('Reprodúcela', Intent.YOUTUBE_CONTROL, 'play_last', {}),
        ('Pausa la canción', Intent.YOUTUBE_CONTROL, 'pause', {}),
        ('Revisa mis correos importantes no leídos', Intent.IMPORTANT_EMAIL, '', {'unread': '1'}),
        ('Cierra la pestaña de YouTube', Intent.CLOSE_WINDOW, 'youtube', {'tab': '1'}),
        ('Cierra Chrome', Intent.CLOSE_WINDOW, 'chrome', {'tab': '0'}),
        ('Cierra Jarvis', Intent.EXIT, '', {}),
    ],
)
def test_natural_connected_command_routing(phrase, intent, entity, metadata) -> None:
    parsed = CommandParser().parse(phrase)
    assert (parsed.intent, parsed.entity, parsed.metadata) == (intent, entity, metadata)


def test_window_close_revalidates_the_confirmed_window() -> None:
    window = Window(12, 34, 'chrome.exe', 'YouTube')
    changed = Window(12, 34, 'chrome.exe', 'Other tab')
    with (
        patch('app.actions.window_actions._window', return_value=changed),
        patch('app.actions.window_actions.win32api.keybd_event') as send,
    ):
        with pytest.raises(WindowActionError, match='cambió'):
            execute_window_close(WindowPlan(window, tab=True))
    send.assert_not_called()


def test_window_close_uses_wm_close_instead_of_killing_process() -> None:
    from win32con import WM_CLOSE

    window = Window(12, 34, 'winword.exe', 'Tesis - Word')
    with (
        patch('app.actions.window_actions._window', return_value=window),
        patch('app.actions.window_actions.win32gui.PostMessage') as send,
    ):
        response = execute_window_close(WindowPlan(window, tab=False))
    send.assert_called_once_with(12, WM_CLOSE, 0, 0)
    assert 'guardar cambios' in response


def test_gmail_important_filter_without_authorization(tmp_path) -> None:
    client = GmailClient(tmp_path / 'client.json', tmp_path / 'token.json')
    with patch('app.integrations.gmail_client.open_url', return_value='Abriendo Gmail.') as open_url:
        result = client.important(unread=True)

    url = open_url.call_args.args[0]
    assert unquote(urlsplit(url).fragment) == 'search/in:inbox is:important is:unread'
    assert 'filtro' in result


def test_youtube_plays_first_video_and_verifies_playback(tmp_path) -> None:
    player = YouTubePlayer(tmp_path / 'browser')
    page = Mock()
    page.url = 'https://www.youtube.com/watch?v=example'
    page.get_by_role.return_value.first.is_visible.return_value = False
    result, video = Mock(), Mock()
    result.get_attribute.return_value = 'Imagine'
    page.locator.side_effect = [Mock(first=result), Mock(first=video)]
    with patch.object(player, '_ensure_page', return_value=page):
        response = player.search('imagine de john lennon', play=True)

    url = page.goto.call_args.args[0]
    assert parse_qs(urlsplit(url).query)['search_query'] == ['imagine de john lennon']
    result.click.assert_called_once()
    video.evaluate.assert_called_once()
    page.wait_for_function.assert_called_once()
    assert response == 'Reproduciendo en YouTube: Imagine.'
