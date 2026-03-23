from unittest.mock import patch

from app.actions.system_actions import COUNTDOWN_SECONDS, restart_computer, shutdown_computer


def test_shutdown_computer_uses_countdown() -> None:
    with patch('app.actions.system_actions.subprocess.Popen') as popen:
        response = shutdown_computer(safe_mode=False)

    popen.assert_called_once_with(['shutdown.exe', '/s', '/t', str(COUNTDOWN_SECONDS)])
    assert response == f'Apagando el equipo en {COUNTDOWN_SECONDS}, 2, 1.'


def test_restart_computer_uses_countdown() -> None:
    with patch('app.actions.system_actions.subprocess.Popen') as popen:
        response = restart_computer(safe_mode=False)

    popen.assert_called_once_with(['shutdown.exe', '/r', '/t', str(COUNTDOWN_SECONDS)])
    assert response == f'Reiniciando el equipo en {COUNTDOWN_SECONDS}, 2, 1.'


def test_shutdown_computer_safe_mode_mentions_countdown() -> None:
    response = shutdown_computer(safe_mode=True)

    assert response == f'Modo seguro activo: se habria apagado el equipo en {COUNTDOWN_SECONDS}, 2, 1.'
