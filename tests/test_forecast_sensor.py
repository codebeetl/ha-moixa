"""Tests for Moixa forecast sensor entities."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator, MoixaData

from .const import MOCK_FORECASTS, MOCK_MOIXA_DATA, MOCK_SITE_ID

_CONSUMPTION_UID = f"{MOCK_SITE_ID}_forecast_consumption"
_SOLAR_UID = f"{MOCK_SITE_ID}_forecast_solar"


async def test_forecast_sensors_registered(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Both forecast sensor entities appear in the registry."""
    for uid in (_CONSUMPTION_UID, _SOLAR_UID):
        assert entity_registry.async_get_entity_id("sensor", DOMAIN, uid) is not None


async def test_forecast_consumption_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Forecast consumption state is the first slot's consumption_W value."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _CONSUMPTION_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == MOCK_FORECASTS[0]["consumption_W"]


async def test_forecast_solar_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Forecast solar state is the first slot's production_W value."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _SOLAR_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == MOCK_FORECASTS[0]["production_W"]


async def test_forecast_attributes_contain_series(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Forecast attribute contains the full series as a list of {ts, W} dicts."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, _CONSUMPTION_UID)
    state = hass.states.get(entity_id)
    assert state is not None
    series = state.attributes.get("forecast")
    assert series is not None
    assert len(series) == len(MOCK_FORECASTS)
    assert series[0]["ts"] == MOCK_FORECASTS[0]["ts"]
    assert series[0]["W"] == MOCK_FORECASTS[0]["consumption_W"]


async def test_forecast_unknown_when_forecasts_none(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Forecast sensors report 'unknown' when coordinator returns forecasts=None."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    import dataclasses
    data_without_forecasts = dataclasses.replace(MOCK_MOIXA_DATA, forecasts=None)
    with patch.object(
        MoixaCoordinator, "_fetch", return_value=data_without_forecasts
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    for uid in (_CONSUMPTION_UID, _SOLAR_UID):
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, uid)
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unknown"
