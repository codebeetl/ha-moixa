"""Select platform for the Moixa integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoixaCoordinator

OPERATION_MODES = ["smart", "schedule", "simple"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moixa select entities from a config entry."""
    coordinator: MoixaCoordinator = entry.runtime_data
    async_add_entities([MoixaOperationModeSelect(coordinator)])


class MoixaOperationModeSelect(CoordinatorEntity[MoixaCoordinator], SelectEntity):
    """Select entity for the battery operation mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "operation_mode"
    _attr_options = OPERATION_MODES

    def __init__(self, coordinator: MoixaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.site_id}_operation_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.site_id)},
            name="Moixa GridShare",
            manufacturer="Moixa",
            model="Smart Battery",
        )

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.operation_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_operation_mode(option)
