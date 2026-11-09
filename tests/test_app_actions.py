from unittest.mock import patch

from app.actions.app_actions import _resolve_explicit_path_candidates, open_application


def test_open_application_opens_cmd_in_new_console_when_resolved() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=r'C:\Windows\System32\cmd.exe'),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('cmd')

    popen.assert_called_once_with(
        [r'C:\Windows\System32\cmd.exe'],
        shell=False,
        creationflags=getattr(__import__('subprocess'), 'CREATE_NEW_CONSOLE', 0),
    )
    assert response == 'Abriendo CMD.'


def test_open_application_opens_gui_apps_without_console_flags() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=r'C:\Windows\System32\notepad.exe'),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('notepad')

    popen.assert_called_once_with(
        [r'C:\Windows\System32\notepad.exe'],
        shell=False,
        creationflags=(
            getattr(__import__('subprocess'), 'DETACHED_PROCESS', 0)
            | getattr(__import__('subprocess'), 'CREATE_NO_WINDOW', 0)
        ),
        stdin=__import__('subprocess').DEVNULL,
        stdout=__import__('subprocess').DEVNULL,
        stderr=__import__('subprocess').DEVNULL,
    )
    assert response == 'Abriendo Bloc de notas.'


def test_open_application_uses_friendly_label_for_web_targets() -> None:
    with patch('app.actions.app_actions.os.startfile') as startfile:
        response = open_application('https://www.youtube.com')

    startfile.assert_called_once_with('https://www.youtube.com')
    assert response == 'Abriendo YouTube.'


def test_open_application_falls_back_to_web_without_generic_desktop_guess() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch('app.actions.app_actions._try_open_explicit_path', return_value=False),
        patch('app.actions.app_actions.os.startfile') as startfile,
    ):
        response = open_application(
            'facebook',
            display_name='Facebook',
            fallback_target='https://www.facebook.com',
            fallback_display_name='Facebook web',
            allow_generic_start=False,
        )

    startfile.assert_called_once_with('https://www.facebook.com')
    assert response == 'No encontre la app de escritorio de Facebook. Abriendo Facebook web.'


def test_open_application_falls_back_to_web_when_desktop_target_is_missing() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch('app.actions.app_actions._try_open_explicit_path', return_value=False),
        patch('app.actions.app_actions.os.startfile') as startfile,
    ):
        response = open_application(
            'notion',
            display_name='Notion',
            fallback_target='https://www.notion.so',
            fallback_display_name='Notion Web',
        )

    startfile.assert_called_once_with('https://www.notion.so')
    assert response == 'No encontre la app de escritorio de Notion. Abriendo Notion Web.'


def test_open_application_does_not_run_alias_target_as_a_shell_command() -> None:
    with (
        patch('app.actions.app_actions.os.startfile') as startfile,
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('app&echo', display_name='Demo')

    startfile.assert_not_called()
    popen.assert_not_called()
    assert response == 'No pude abrir demo.'


def test_open_application_tries_web_if_spotify_protocol_is_unavailable() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch('app.actions.app_actions._try_open_explicit_path', return_value=False),
        patch('app.actions.app_actions.os.startfile', side_effect=[OSError, OSError, None]) as startfile,
    ):
        response = open_application('spotify', fallback_target='https://open.spotify.com')

    assert [call.args[0] for call in startfile.call_args_list] == [
        'spotify:',
        'shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify',
        'https://open.spotify.com',
    ]
    assert response == 'No encontre la app de escritorio de Spotify. Abriendo Spotify.'


def test_open_application_uses_notion_desktop_fallback_path() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch(
            'app.actions.app_actions._try_open_explicit_path',
            side_effect=lambda command: isinstance(command, str) and command.lower().endswith('notion\\notion.exe'),
        ),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('notion', display_name='Notion')

    popen.assert_not_called()
    assert response == 'Abriendo Notion.'


def test_open_application_uses_discord_desktop_launcher() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch('app.actions.app_actions._try_open_explicit_path', return_value=False),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('discord', display_name='Discord')

    launched = popen.call_args[0][0]
    assert launched[0].lower().endswith('discord\\update.exe')
    assert launched[1:] == ['--processStart', 'Discord.exe']
    assert response == 'Abriendo Discord.'


def test_open_application_uses_telegram_desktop_path() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch(
            'app.actions.app_actions._try_open_explicit_path',
            side_effect=lambda command: isinstance(command, str) and 'telegram desktop\\telegram.exe' in command.lower(),
        ),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('telegram', display_name='Telegram')

    popen.assert_not_called()
    assert response == 'Abriendo Telegram.'


def test_open_application_uses_whatsapp_desktop_path_before_protocol() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch(
            'app.actions.app_actions._try_open_explicit_path',
            side_effect=lambda command: isinstance(command, str) and command.lower().endswith('whatsapp\\whatsapp.exe'),
        ),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('whatsapp', display_name='WhatsApp')

    popen.assert_not_called()
    assert response == 'Abriendo WhatsApp.'


def test_open_application_uses_google_drive_desktop_path_pattern() -> None:
    with (
        patch('app.actions.app_actions.shutil.which', return_value=None),
        patch(
            'app.actions.app_actions._try_open_explicit_path',
            side_effect=lambda command: isinstance(command, str) and 'googledrivefs.exe' in command.lower(),
        ),
        patch('app.actions.app_actions.subprocess.Popen') as popen,
    ):
        response = open_application('drive', display_name='Google Drive')

    popen.assert_not_called()
    assert response == 'Abriendo Google Drive.'


def test_resolve_explicit_path_candidates_expands_wildcards() -> None:
    with patch(
        'app.actions.app_actions.glob.glob',
        return_value=[r'C:\Program Files\Google\Drive File Stream\123\GoogleDriveFS.exe'],
    ) as glob_search:
        matches = _resolve_explicit_path_candidates(
            r'C:\Program Files\Google\Drive File Stream\*\GoogleDriveFS.exe'
        )

    glob_search.assert_called_once_with(r'C:\Program Files\Google\Drive File Stream\*\GoogleDriveFS.exe')
    assert matches == [r'C:\Program Files\Google\Drive File Stream\123\GoogleDriveFS.exe']
