"""Derived battery SOC trend values."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

MIN_HISTORY_SECONDS = 600
MIN_RATE_PER_HOUR = 0.5


def predict_limit_time(
    soc: float,
    rate: float | None,
    slot: dict | None,
    now: datetime,
) -> datetime | None:
    """Return when SOC reaches the slot's limit at the current rate, if before the slot ends.

    The limit is the slot's socMax while charging and socMin while discharging.
    """
    if rate is None or slot is None or abs(rate) < MIN_RATE_PER_HOUR:
        return None
    intent = slot["intent"]
    limit = intent["socMax" if rate > 0 else "socMin"] * 100
    remaining = limit - soc
    if remaining * rate <= 0:
        return None
    predicted = now + timedelta(hours=remaining / rate)
    slot_end = dt_util.parse_datetime(slot["endTime"]) if slot.get("endTime") else None
    if slot_end is not None and predicted > slot_end:
        return None
    return predicted


def soc_rate_per_hour(history: Sequence[tuple[datetime, float]]) -> float | None:
    """Return the least-squares SOC slope in percent per hour, or None without enough history."""
    if len(history) < 2:
        return None
    start = history[0][0]
    seconds = [(moment - start).total_seconds() for moment, _ in history]
    if seconds[-1] < MIN_HISTORY_SECONDS:
        return None
    socs = [soc for _, soc in history]
    mean_seconds = sum(seconds) / len(seconds)
    mean_soc = sum(socs) / len(socs)
    variance = sum((s - mean_seconds) ** 2 for s in seconds)
    covariance = sum((s - mean_seconds) * (v - mean_soc) for s, v in zip(seconds, socs))
    return covariance / variance * 3600
