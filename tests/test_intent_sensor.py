"""Tests for Moixa current intent sensor and schedule attribute on select."""

import dataclasses
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator

from .const import MOCK_INTENT_SERIES, MOCK_MOIXA_DATA, MOCK_SCHEDULE, MOCK_SITE_ID

_INTENT_UID = f"{MOCK_SITE_ID}_current_intent"
_MODE_UID = f"{MOCK_SITE_ID}_operation_mode"


async def test_intent_sensor_registered(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Current intent sensor appears in the entity registry."""
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, _INTENT_UID) is not None


async def test_intent_sensor_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Current intent state is the kind from the first intent series slot."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _INTENT_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == MOCK_INTENT_SERIES[0]["intent"]["kind"]


async def test_intent_sensor_schedule_attribute(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Current intent sensor carries the full series as a 'schedule' attribute."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _INTENT_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    series = state.attributes.get("schedule")
    assert series is not None
    assert len(series) == len(MOCK_INTENT_SERIES)
    assert series[0]["intent"]["kind"] == MOCK_INTENT_SERIES[0]["intent"]["kind"]


async def test_intent_sensor_unknown_when_series_none(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Intent sensor reports 'unknown' when coordinator returns intent_series=None."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(
        MoixaCoordinator,
        "_fetch",
        return_value=dataclasses.replace(MOCK_MOIXA_DATA, intent_series=None),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _INTENT_UID)
    assert hass.states.get(entity_id).state == "unknown"


async def test_operation_mode_schedule_attribute(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Operation mode select entity exposes the schedule plan as an attribute."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _MODE_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    schedule = state.attributes.get("schedule")
    assert schedule is not None
    assert schedule["periodDays"] == MOCK_SCHEDULE["periodDays"]
    assert len(schedule["intents"]) == len(MOCK_SCHEDULE["intents"])


async def test_operation_mode_no_schedule_attribute_when_none(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Schedule attribute is absent when coordinator returns schedule=None."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(
        MoixaCoordinator,
        "_fetch",
        return_value=dataclasses.replace(MOCK_MOIXA_DATA, schedule=None),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, _MODE_UID)
    state = hass.states.get(entity_id)
    assert "schedule" not in state.attributes
