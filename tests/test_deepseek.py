import json
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from app.integrations.chat import ChatError
from app.integrations.deepseek_client import DeepSeekClient


def test_deepseek_sends_chat_history_and_returns_message() -> None:
    body = b'{"choices": [{"message": {"content": "Entendido."}}]}'
    history = [{'role': 'user', 'text': 'Hola'}, {'role': 'model', 'text': 'Hola, Señor'}]

    with patch('urllib.request.urlopen', return_value=BytesIO(body)) as send:
        assert DeepSeekClient('fake_key').ask('Continúa', history) == 'Entendido.'

    request = send.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == 'https://api.deepseek.com/chat/completions'
    assert request.get_header('Authorization') == 'Bearer fake_key'
    assert payload['model'] == 'deepseek-flash'
    assert payload['thinking'] == {'type': 'disabled'}
    assert [turn['role'] for turn in payload['messages']] == ['system', 'user', 'assistant', 'user']
    assert payload['messages'][-1]['content'] == 'Continúa'


def test_deepseek_reports_insufficient_balance_without_exposing_response_body() -> None:
    error = HTTPError('https://api.deepseek.com', 402, 'Payment required', {}, BytesIO(b'sensitive'))
    with patch('urllib.request.urlopen', side_effect=error):
        with pytest.raises(ChatError, match='HTTP 402. Revisa el saldo') as exc:
            DeepSeekClient('fake_key').ask('Hola')
    assert 'sensitive' not in str(exc.value)
