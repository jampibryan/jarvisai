from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.integrations.chat import ChatError, SYSTEM_INSTRUCTION


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = 'deepseek-flash') -> None:
        self.api_key = api_key
        self.model = model

    def ask(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        messages = [{'role': 'system', 'content': SYSTEM_INSTRUCTION}]
        messages.extend(
            {'role': 'assistant' if turn['role'] == 'model' else 'user', 'content': turn['text']}
            for turn in history or []
        )
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.model,
            'messages': messages,
            'thinking': {'type': 'disabled'},
            'max_tokens': 512,
        }
        request = urllib.request.Request(
            'https://api.deepseek.com/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                text = json.load(response)['choices'][0]['message']['content'].strip()
        except urllib.error.HTTPError as exc:
            with exc:
                detail = {
                    401: 'revisa la clave de API',
                    402: 'revisa el saldo de tu cuenta',
                    429: 'el servicio alcanzó su límite de solicitudes',
                }.get(exc.code, 'el servidor rechazó la solicitud')
            raise ChatError(f'DeepSeek devolvió HTTP {exc.code}. {detail.capitalize()}.') from None
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ChatError('DeepSeek no respondió con una respuesta válida.') from None

        if not text:
            raise ChatError('DeepSeek devolvió una respuesta vacía.')
        return text
