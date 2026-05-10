"""Tests for Moixa sensor entities."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator, MoixaData

from .const import MOCK_MOIXA_DATA, MOCK_SITE_ID

# Unique-id suffixes defined in sensor.py
_SENSOR_KEYS = [
    "battery_soc",
    "home_consumption",
    "grid_import",
    "grid_export",
    "solar_production",
    "battery_charging",
    "battery_discharging",
]


async def test_all_sensors_registered(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """All seven sensor entities are created in the entity registry."""
    for key in _SENSOR_KEYS:
        uid = f"{MOCK_SITE_ID}_{key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, uid)
        assert entity_id is not None, f"sensor {key} not found in registry"


async def test_battery_soc_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Battery SOC sensor reports the value from coordinator data."""
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_SITE_ID}_battery_soc"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == pytest.approx(MOCK_MOIXA_DATA.battery_soc)


@pytest.mark.parametrize(
    ("key", "field"),
    [
        ("home_consumption", "consumption_w"),
        ("grid_import", "grid_import_w"),
        ("grid_export", "grid_export_w"),
        ("solar_production", "solar_w"),
        ("battery_charging", "battery_charging_w"),
        ("battery_discharging", "battery_discharging_w"),
    ],
)
async def test_power_sensor_states(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    key: str,
    field: str,
) -> None:
    """Each power sensor reports the correct watt value from coordinator data."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{MOCK_SITE_ID}_{key}")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    expected = getattr(MOCK_MOIXA_DATA, field)
    assert float(state.state) == pytest.approx(expected)


async def test_sensors_unavailable_when_data_is_none(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Sensors report 'unavailable' when coordinator data is None."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data

    with patch.object(MoixaCoordinator, "_fetch", side_effect=OSError("offline")):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    for key in _SENSOR_KEYS:
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{MOCK_SITE_ID}_{key}")
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unavailable", f"{key} should be unavailable"


async def test_sensor_device_info(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """All sensors share the same device, identified by site ID."""
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, MOCK_SITE_ID)})
    assert device is not None
    assert device.manufacturer == "Moixa"
    assert device.model == "Smart Battery"

    for key in _SENSOR_KEYS:
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{MOCK_SITE_ID}_{key}")
        entry = entity_registry.async_get(entity_id)
        assert entry is not None
        assert entry.device_id == device.id
