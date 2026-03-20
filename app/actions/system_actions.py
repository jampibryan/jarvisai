from __future__ import annotations

from datetime import datetime


def get_current_time() -> str:
    return f"Son las {datetime.now():%H:%M}."


def get_current_date() -> str:
    return f"Hoy es {datetime.now():%Y-%m-%d}."

