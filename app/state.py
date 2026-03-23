from __future__ import annotations

from dataclasses import dataclass

from app.brain.intents import ParsedCommand


@dataclass(slots=True)
class AssistantState:
    # Estado general del asistente para el loop actual.
    status: str = 'idle'
    current_mode: str = 'text'
    last_command: str = ''
    last_response: str = ''
    pending_confirmation: ParsedCommand | None = None
