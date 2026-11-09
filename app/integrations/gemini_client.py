from __future__ import annotations

import json
import urllib.request
import urllib.error

from app.integrations.chat import ChatError, SYSTEM_INSTRUCTION


class GeminiClient:
    """Cliente para comunicarse con Google Gemini API sin dependencias externas."""

    def __init__(self, api_key: str, model: str = 'gemini-2.5-flash') -> None:
        self.api_key = api_key
        self.model = model

    def ask(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        """Envía el prompt y el historial a la API de Gemini."""
        if not self.api_key:
            raise ChatError('No hay clave de API configurada para Gemini.')

        contents = [
            {'role': turn['role'], 'parts': [{'text': turn['text']}]}
            for turn in history or []
        ]
        contents.append({'role': 'user', 'parts': [{'text': prompt}]})
        payload = {
            'contents': contents,
            'systemInstruction': {'parts': [{'text': SYSTEM_INSTRUCTION}]},
        }
        request = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': self.api_key},
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                candidates = json.load(response).get('candidates', [])
                parts = candidates[0].get('content', {}).get('parts', []) if candidates else []
                text = ''.join(part.get('text', '') for part in parts).strip()
        except urllib.error.HTTPError as exc:
            with exc:
                status = exc.code
            raise ChatError(f'Gemini devolvió HTTP {status}.') from None
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ChatError('Gemini no respondió con una respuesta válida.') from None

        if not text:
            raise ChatError('Gemini devolvió una respuesta vacía.')
        return text
