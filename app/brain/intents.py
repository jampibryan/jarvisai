from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    OPEN_PATH = "open_path"
    OPEN_APP = "open_app"
    GET_TIME = "get_time"
    GET_DATE = "get_date"
    LIST_COMMANDS = "list_commands"
    SHOW_METRICS = "show_metrics"
    LEARN_ALIAS = "learn_alias"
    REPLACE_ALIAS = "replace_alias"
    RESTART_COMPUTER = "restart_computer"
    SHUTDOWN_COMPUTER = "shutdown_computer"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    EXIT = "exit"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParsedCommand:
    raw_text: str
    normalized_text: str
    intent: Intent
    entity: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
