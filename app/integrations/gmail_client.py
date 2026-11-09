from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from app.actions.productivity_actions import open_url


_SCOPE = ['https://www.googleapis.com/auth/gmail.readonly']
_MESSAGES = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
logger = logging.getLogger('JarvisAI')

class GmailClient:
    def __init__(self, client_path: Path, token_path: Path) -> None:
        self.client_path, self.token_path = client_path, token_path

    def connect(self) -> str:
        if not self.client_path.is_file():
            return 'Para leer Gmail desde Jarvis necesitas configurar un cliente de escritorio de Google. Por ahora puedo abrir el filtro de correos importantes.'
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_path), _SCOPE)
            credentials = flow.run_local_server(
                host='127.0.0.1', port=0, timeout_seconds=90, authorization_prompt_message=None,
                success_message='Gmail está conectado a Jarvis. Puedes cerrar esta pestaña.',
            )
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(credentials.to_json(), encoding='utf-8')
            return 'Gmail conectado en modo de solo lectura. Puedes decir «revisa mis correos importantes».'
        except Exception:
            logger.warning('No se completó la autorización de Gmail.')
            return 'No pude completar la autorización de Gmail. Puedes volver a intentarlo.'

    def important(self, *, unread: bool) -> str:
        query = 'in:inbox is:important' + (' is:unread' if unread else '')
        if not self.token_path.is_file():
            response = open_url('https://mail.google.com/mail/u/0/#search/' + quote(query, safe=''))
            return 'Abrí Gmail con el filtro de correos importantes.' if response.startswith('Abriendo') else response

        try:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2.credentials import Credentials

            credentials = Credentials.from_authorized_user_file(str(self.token_path), scopes=_SCOPE)
            with AuthorizedSession(credentials, refresh_timeout=8) as session:
                response = session.get(_MESSAGES, params={'q': query, 'maxResults': 5}, timeout=8)
                response.raise_for_status()
                items = response.json().get('messages', [])
                messages = []
                for item in items[:5]:
                    details = session.get(
                        f'{_MESSAGES}/{quote(item["id"], safe="")}',
                        params=[('format', 'metadata'), ('metadataHeaders', 'From'), ('metadataHeaders', 'Subject')],
                        timeout=5,
                    )
                    details.raise_for_status()
                    headers = {header['name'].lower(): header['value'] for header in details.json()['payload']['headers']}
                    sender = ' '.join(headers.get('from', 'Remitente desconocido').split())[:120]
                    subject = ' '.join(headers.get('subject', 'Sin asunto').split())[:150]
                    messages.append(f'{subject} · {sender}')
            if not messages:
                return 'Gmail no encontró correos con ese filtro.'
            return 'Correos importantes recientes:\n' + '\n'.join(f'• {message}' for message in messages)
        except Exception:
            logger.warning('No se pudo consultar Gmail en modo de solo lectura.')
            return 'No pude consultar Gmail. Si la autorización venció, di «conecta Gmail» para renovarla.'

