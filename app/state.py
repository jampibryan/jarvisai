from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.brain.intents import ParsedCommand

if TYPE_CHECKING:
    from app.actions.selected_files import FilePlan
    from app.actions.window_actions import WindowPlan


@dataclass(slots=True)
class AssistantState:
    # Estado general del asistente para el loop actual.
    status: str = 'idle'
    current_mode: str = 'text'
    last_command: str = ''
    last_response: str = ''
    pending_confirmation: ParsedCommand | None = None
    pending_file_plan: FilePlan | None = None
    pending_window_plan: WindowPlan | None = None
    confirmation_deadline: float = 0.0
    search_query_deadline: float = 0.0
    search_result_deadline: float = 0.0
    media_followup_deadline: float = 0.0
    command_followup_deadline: float = 0.0
    command_followup_prefix: str = ''
    voice_activation_deadline: float = 0.0
    search_results: tuple[Path, ...] = ()
