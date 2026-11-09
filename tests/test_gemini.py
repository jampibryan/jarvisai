import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.chat import ChatError
from app.integrations.gemini_client import GeminiClient


def test_gemini_client_success() -> None:
    client = GeminiClient(api_key="fake_key")
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Sí, Señor. Estoy listo."
                        }
                    ]
                }
            }
        ]
    }).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        reply = client.ask("hola")
        assert reply == "Sí, Señor. Estoy listo."
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args.args[0]
        assert request.get_header('X-goog-api-key') == 'fake_key'
        assert 'fake_key' not in request.full_url


def test_gemini_client_http_error() -> None:
    client = GeminiClient(api_key="fake_key")
    
    err_body = json.dumps({
        "error": {
            "message": "Invalid API Key"
        }
    }).encode("utf-8")
    
    mock_err = urllib.error.HTTPError(
        url="http://fake.url",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=BytesIO(err_body)
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = mock_err
        
        with pytest.raises(ChatError, match='HTTP 400'):
            client.ask("hola")


def test_gemini_client_general_error() -> None:
    client = GeminiClient(api_key="fake_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = TimeoutError("Connection Timeout")
        
        with pytest.raises(ChatError, match='respuesta válida'):
            client.ask("hola")


def test_gemini_client_missing_key() -> None:
    client = GeminiClient(api_key="")
    with pytest.raises(ChatError, match='No hay clave de API configurada'):
        client.ask("hola")


def test_gemini_client_with_history() -> None:
    client = GeminiClient(api_key="fake_key", model="gemini-3.5-flash")
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Entendido, Señor."
                        }
                    ]
                }
            }
        ]
    }).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        history = [
            {"role": "user", "text": "hola"},
            {"role": "model", "text": "Hola, Señor. ¿En qué le puedo asistir?"}
        ]
        reply = client.ask("¿cuál es la siguiente tarea?", history=history)
        assert reply == "Entendido, Señor."
        
        # Verificar que el request contenga la estructura de historial esperada
        called_args = mock_urlopen.call_args[0][0]
        posted_data = json.loads(called_args.data.decode("utf-8"))
        assert len(posted_data["contents"]) == 3
        assert posted_data["contents"][0]["role"] == "user"
        assert posted_data["contents"][0]["parts"][0]["text"] == "hola"
        assert posted_data["contents"][1]["role"] == "model"
        assert posted_data["contents"][2]["role"] == "user"
        assert posted_data["contents"][2]["parts"][0]["text"] == "¿cuál es la siguiente tarea?"

