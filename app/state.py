from __future__ import annotations

from dataclasses import dataclass

from app.brain.intents import ParsedCommand


@dataclass(slots=True)
class AssistantState:
    status: str = "idle"
    last_command: str = ""
    last_response: str = ""
    pending_confirmation: ParsedCommand | None = None
