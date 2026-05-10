"""Diagnostics support for the Moixa integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import MoixaCoordinator

_TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: MoixaCoordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(entry.as_dict(), _TO_REDACT),
        "data": asdict(coordinator.data) if coordinator.data is not None else {},
    }
