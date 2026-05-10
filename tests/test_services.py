"""Tests for Moixa service calls."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator

from .const import MOCK_SITE_ID


async def test_services_registered(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """All three services are registered after setup."""
    for service in ("set_operation_mode", "add_schedule_intent", "remove_schedule_slot"):
        assert hass.services.has_service(DOMAIN, service)


async def test_set_operation_mode_service(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """set_operation_mode service delegates to coordinator."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(coordinator, "async_set_operation_mode", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN, "set_operation_mode", {"mode": "schedule"}, blocking=True
        )
    mock.assert_awaited_once_with("schedule")


async def test_add_schedule_intent_service(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """add_schedule_intent service delegates to coordinator with correct args."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(coordinator, "async_add_schedule_intent", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN,
            "add_schedule_intent",
            {
                "kind": "charge/discharge",
                "duration_minutes": 120,
                "power_watts": 2000,
                "soc_max": 0.9,
            },
            blocking=True,
        )
    mock.assert_awaited_once_with(
        kind="charge/discharge",
        duration_minutes=120,
        position=-1,
        soc_min=0.1,
        soc_max=0.9,
        power_watts=2000.0,
    )


async def test_remove_schedule_slot_service(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """remove_schedule_slot service delegates to coordinator."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(coordinator, "async_remove_schedule_slot", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN, "remove_schedule_slot", {"index": 2}, blocking=True
        )
    mock.assert_awaited_once_with(2)


async def test_services_removed_on_unload(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Services are unregistered when the last entry is unloaded."""
    await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    for service in ("set_operation_mode", "add_schedule_intent", "remove_schedule_slot"):
        assert not hass.services.has_service(DOMAIN, service)
