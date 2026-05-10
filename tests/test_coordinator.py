"""Unit tests for coordinator parsing logic (no HA fixtures required)."""

import pytest

from custom_components.moixa.coordinator import _parse_core_readings

from .const import MOCK_CORE_READINGS


def test_parse_core_readings_full_response() -> None:
    """All six channels are extracted correctly from a real-shaped JTS response."""
    result = _parse_core_readings(MOCK_CORE_READINGS)

    assert result["consumption_w"] == pytest.approx(489.6)
    assert result["grid_import_w"] == pytest.approx(0.0)
    assert result["grid_export_w"] == pytest.approx(1751.7)
    assert result["solar_w"] == pytest.approx(722.0)
    assert result["battery_charging_w"] == pytest.approx(1984.1)
    assert result["battery_discharging_w"] == pytest.approx(0.0)


def test_parse_core_readings_empty_data() -> None:
    """An empty data list returns an empty dict (no KeyError)."""
    readings = {**MOCK_CORE_READINGS, "data": []}
    result = _parse_core_readings(readings)
    assert result == {}


def test_parse_core_readings_missing_channel() -> None:
    """A channel absent from the column map returns None for that key."""
    # Remove the solar column from the header.
    stripped = dict(MOCK_CORE_READINGS)
    stripped["header"] = {
        **MOCK_CORE_READINGS["header"],
        "columns": {
            k: v
            for k, v in MOCK_CORE_READINGS["header"]["columns"].items()
            if v["id"] != "core/production/out/AC/W"
        },
    }
    result = _parse_core_readings(stripped)
    assert result["solar_w"] is None
    assert result["consumption_w"] == pytest.approx(489.6)


def test_parse_core_readings_null_value() -> None:
    """A null 'v' field in the JTS row is returned as None, not 0."""
    readings = {
        **MOCK_CORE_READINGS,
        "data": [{"ts": "2026-01-01T00:00:00Z", "f": {"1": {"v": None}}}],
    }
    result = _parse_core_readings(readings)
    assert result["consumption_w"] is None


def test_parse_core_readings_empty_response() -> None:
    """A completely empty dict does not raise."""
    result = _parse_core_readings({})
    assert result == {}
