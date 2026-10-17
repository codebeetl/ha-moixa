"""Tests for Moixa service calls."""

from datetime import time
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator
from custom_components.moixa.moixa_api.schedule_windows import ScheduleWindow

from .const import MOCK_SITE_ID

SERVICES = ("set_operation_mode", "add_schedule_intent", "set_schedule", "remove_schedule_slot")


async def test_services_registered(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """All services are registered after setup."""
    for service in SERVICES:
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


async def test_set_schedule_service(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """set_schedule service converts the windows and delegates to coordinator."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    with patch.object(coordinator, "async_set_schedule", new_callable=AsyncMock) as mock:
        await hass.services.async_call(
            DOMAIN,
            "set_schedule",
            {
                "windows": [
                    {
                        "start": "01:30",
                        "end": "05:00",
                        "days": ["mon", "sun"],
                        "kind": "charge/discharge",
                        "power_watts": 2500,
                    },
                    {"start": "17:00", "end": "19:00", "kind": "idle"},
                ]
            },
            blocking=True,
        )
    mock.assert_awaited_once_with(
        [
            ScheduleWindow(
                start=time(1, 30),
                end=time(5, 0),
                kind="charge/discharge",
                days=(0, 6),
                power_watts=2500.0,
            ),
            ScheduleWindow(start=time(17, 0), end=time(19, 0), kind="idle"),
        ]
    )


async def test_services_removed_on_unload(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Services are unregistered when the last entry is unloaded."""
    await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    for service in SERVICES:
        assert not hass.services.has_service(DOMAIN, service)
