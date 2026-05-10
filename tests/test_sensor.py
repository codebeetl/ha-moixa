"""Tests for Moixa sensor entities."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

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


_ENERGY_KEYS = [
    "solar_energy",
    "grid_import_energy",
    "grid_export_energy",
    "battery_charging_energy",
    "battery_discharging_energy",
]


async def test_energy_sensors_registered(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """All five energy sensor entities are created in the entity registry."""
    for key in _ENERGY_KEYS:
        uid = f"{MOCK_SITE_ID}_{key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, uid)
        assert entity_id is not None, f"energy sensor {key} not found in registry"


async def test_energy_sensor_initial_state(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Energy sensors start at 0.0 on first install (no restored state)."""
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_SITE_ID}_solar_energy"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == pytest.approx(0.0)


async def test_energy_sensor_accumulates(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Energy sensor accumulates kWh on coordinator refresh using trapezoidal integration."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_SITE_ID}_solar_energy"
    )
    assert entity_id is not None

    future_time = dt_util.utcnow() + timedelta(hours=1)
    with (
        patch.object(MoixaCoordinator, "_fetch", return_value=MOCK_MOIXA_DATA),
        patch("custom_components.moixa.sensor.dt_util.utcnow", return_value=future_time),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    # solar_w = 722.0 W constant across both polls
    # trapezoidal: (722 + 722) / 2 * 1 h / 1000 = 0.722 kWh
    assert float(state.state) == pytest.approx(0.722, rel=0.01)


async def test_energy_sensor_no_spike_after_outage(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Energy sensor skips one interval after coordinator failure to avoid over-accumulation."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_SITE_ID}_solar_energy"
    )
    assert entity_id is not None

    # First: simulate a 1-hour good poll to build up some energy
    t1 = dt_util.utcnow() + timedelta(hours=1)
    with (
        patch.object(MoixaCoordinator, "_fetch", return_value=MOCK_MOIXA_DATA),
        patch("custom_components.moixa.sensor.dt_util.utcnow", return_value=t1),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    after_first = float(hass.states.get(entity_id).state)
    assert after_first == pytest.approx(0.722, rel=0.01)

    # Then: simulate a failed fetch (coordinator offline for 6 hours)
    with patch.object(MoixaCoordinator, "_fetch", side_effect=OSError("offline")):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    # Then: successful fetch 6 hours later - should NOT accumulate the outage gap
    t2 = t1 + timedelta(hours=6)
    with (
        patch.object(MoixaCoordinator, "_fetch", return_value=MOCK_MOIXA_DATA),
        patch("custom_components.moixa.sensor.dt_util.utcnow", return_value=t2),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    # The sensor skips accumulation on the first good poll after failure, so value unchanged
    after_recovery = float(hass.states.get(entity_id).state)
    assert after_recovery == pytest.approx(after_first, rel=0.01)


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
