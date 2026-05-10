"""Moixa GridShare integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import MoixaCoordinator

type MoixaConfigEntry = ConfigEntry[MoixaCoordinator]

_SET_MODE_SCHEMA = vol.Schema({
    vol.Required("mode"): vol.In(["smart", "schedule", "simple"]),
})

_ADD_INTENT_SCHEMA = vol.Schema({
    vol.Required("kind"): vol.In(["balance", "charge/discharge", "idle"]),
    vol.Required("duration_minutes"): vol.All(vol.Coerce(int), vol.Range(min=1, max=10080)),
    vol.Optional("position", default=-1): vol.Coerce(int),
    vol.Optional("soc_min", default=0.1): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
    vol.Optional("soc_max", default=1.0): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
    vol.Optional("power_watts"): vol.All(vol.Coerce(float), vol.Range(min=0, max=10000)),
})

_REMOVE_SLOT_SCHEMA = vol.Schema({
    vol.Required("index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
})


def _loaded_coordinators(hass: HomeAssistant) -> list[MoixaCoordinator]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if hasattr(entry, "runtime_data")
    ]


def _register_services(hass: HomeAssistant) -> None:
    async def handle_set_operation_mode(call: ServiceCall) -> None:
        for coordinator in _loaded_coordinators(hass):
            await coordinator.async_set_operation_mode(call.data["mode"])

    async def handle_add_schedule_intent(call: ServiceCall) -> None:
        for coordinator in _loaded_coordinators(hass):
            await coordinator.async_add_schedule_intent(
                kind=call.data["kind"],
                duration_minutes=call.data["duration_minutes"],
                position=call.data["position"],
                soc_min=call.data["soc_min"],
                soc_max=call.data["soc_max"],
                power_watts=call.data.get("power_watts"),
            )

    async def handle_remove_schedule_slot(call: ServiceCall) -> None:
        for coordinator in _loaded_coordinators(hass):
            await coordinator.async_remove_schedule_slot(call.data["index"])

    hass.services.async_register(DOMAIN, "set_operation_mode", handle_set_operation_mode, schema=_SET_MODE_SCHEMA)
    hass.services.async_register(DOMAIN, "add_schedule_intent", handle_add_schedule_intent, schema=_ADD_INTENT_SCHEMA)
    hass.services.async_register(DOMAIN, "remove_schedule_slot", handle_remove_schedule_slot, schema=_REMOVE_SLOT_SCHEMA)


async def async_setup_entry(hass: HomeAssistant, entry: MoixaConfigEntry) -> bool:
    """Set up Moixa from a config entry."""
    coordinator = MoixaCoordinator(
        hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, "set_operation_mode"):
        _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MoixaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        remaining = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining:
            hass.services.async_remove(DOMAIN, "set_operation_mode")
            hass.services.async_remove(DOMAIN, "add_schedule_intent")
            hass.services.async_remove(DOMAIN, "remove_schedule_slot")
    return unloaded
