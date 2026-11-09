from unittest.mock import patch

from app.actions.productivity_actions import open_url


def test_open_url_returns_friendly_name_for_known_sites() -> None:
    with patch('app.actions.productivity_actions.webbrowser.open', return_value=True) as open_browser:
        response = open_url('https://openai.com')

    open_browser.assert_called_once_with('https://openai.com', new=2)
    assert response == 'Abriendo OpenAI.'
