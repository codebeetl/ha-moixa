"""Constants for the Moixa integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "moixa"
PLATFORMS: list[Platform] = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(minutes=5)
