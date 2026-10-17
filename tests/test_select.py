"""Tests for Moixa select entities."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator

from .const import MOCK_MOIXA_DATA, MOCK_SCHEDULE, MOCK_SITE_ID

_ENTITY_UID = f"{MOCK_SITE_ID}_operation_mode"


async def test_operation_mode_registered(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Operation mode select entity is created in the entity registry."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _ENTITY_UID)
    assert entity_id is not None


async def test_operation_mode_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Select entity reflects the operation mode from coordinator data."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _ENTITY_UID)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == MOCK_MOIXA_DATA.operation_mode


async def test_schedule_windows_attribute(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Select entity exposes the weekly schedule as readable windows in local time."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _ENTITY_UID)
    assert entity_id is not None
    windows = hass.states.get(entity_id).attributes["windows"]

    charge = [w for w in windows if w["kind"] == "charge/discharge"]
    charge_end = MOCK_SCHEDULE["intents"][1]["durationMinutes"]
    charge_start = MOCK_SCHEDULE["intents"][0]["durationMinutes"]
    charge_minutes = sum((_minutes(w["end"]) or 24 * 60) - _minutes(w["start"]) for w in charge)
    assert charge_minutes == charge_end - charge_start
    assert {w["power_watts"] for w in charge} == {2000}
    assert {w["day"] for w in windows} <= {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def _minutes(clock: str) -> int:
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


async def test_select_option_calls_coordinator(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Selecting an option delegates to coordinator.async_set_operation_mode."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _ENTITY_UID)
    assert entity_id is not None

    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(
        coordinator,
        "async_set_operation_mode",
        new_callable=AsyncMock,
    ) as mock_set:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "simple"},
            blocking=True,
        )
    mock_set.assert_awaited_once_with("simple")


async def test_operation_mode_unavailable_when_data_is_none(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Select entity reports 'unavailable' when coordinator data is None."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data

    with patch.object(MoixaCoordinator, "_fetch", side_effect=OSError("offline")):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _ENTITY_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
