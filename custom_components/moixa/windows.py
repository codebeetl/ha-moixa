"""Conversion between Moixa schedule windows and Home Assistant friendly dicts."""

from __future__ import annotations

from typing import Any

from .moixa_api.schedule_windows import ScheduleWindow

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def window_to_dict(window: ScheduleWindow) -> dict[str, Any]:
    """Return a single-day window as a dict with local HH:MM times."""
    return {
        "day": WEEKDAYS[window.days[0]],
        "start": window.start.strftime("%H:%M"),
        "end": window.end.strftime("%H:%M"),
        "kind": window.kind,
        "soc_min": window.soc_min,
        "soc_max": window.soc_max,
        "power_watts": window.power_watts,
        "power_watts_min": window.power_watts_min,
        "power_watts_max": window.power_watts_max,
    }
