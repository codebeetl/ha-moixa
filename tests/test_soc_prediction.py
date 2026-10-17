"""Tests for the derived SOC trend values."""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.moixa.soc_prediction import predict_limit_time, soc_rate_per_hour

_START = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def _history(*points: tuple[int, float]) -> list[tuple[datetime, float]]:
    return [(_START + timedelta(minutes=minutes), soc) for minutes, soc in points]


def _slot(soc_min: float, soc_max: float, ends_in_minutes: int) -> dict:
    return {
        "endTime": (_START + timedelta(minutes=ends_in_minutes)).isoformat(),
        "intent": {"kind": "balance", "socMin": soc_min, "socMax": soc_max},
    }


@pytest.mark.parametrize(
    ("soc", "rate", "slot", "expected_minutes"),
    [
        (50.0, 10.0, _slot(0.1, 0.9, 600), 240),
        (50.0, -10.0, _slot(0.2, 1.0, 600), 180),
        (50.0, 10.0, _slot(0.1, 0.9, 120), None),
        (50.0, 0.2, _slot(0.1, 0.9, 600), None),
        (95.0, 10.0, _slot(0.1, 0.9, 600), None),
        (50.0, None, _slot(0.1, 0.9, 600), None),
        (50.0, 10.0, None, None),
    ],
)
def test_predict_limit_time(
    soc: float,
    rate: float | None,
    slot: dict | None,
    expected_minutes: int | None,
) -> None:
    """Limit time is when SOC reaches the current slot's limit before the slot ends."""
    expected = None if expected_minutes is None else _START + timedelta(minutes=expected_minutes)
    assert predict_limit_time(soc, rate, slot, _START) == expected


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        (_history((0, 50.0), (15, 52.0), (30, 54.0)), 8.0),
        (_history((0, 80.0), (30, 75.0)), -10.0),
        (_history((0, 50.0), (5, 50.5)), None),
        (_history((0, 50.0)), None),
        ([], None),
    ],
)
def test_soc_rate_per_hour(
    history: list[tuple[datetime, float]], expected: float | None
) -> None:
    """Rate is the SOC slope in %/h, and unknown without enough history."""
    assert soc_rate_per_hour(history) == pytest.approx(expected)
