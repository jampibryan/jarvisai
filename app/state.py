from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AssistantState:
    status: str = "idle"
    last_command: str = ""
    last_response: str = ""

