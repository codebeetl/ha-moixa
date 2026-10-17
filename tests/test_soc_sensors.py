"""Tests for the SOC rate of change and predicted limit time sensors."""

import dataclasses
from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator

from .const import MOCK_MOIXA_DATA, MOCK_SITE_ID


async def test_soc_trend_sensors(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Rate and limit time follow polled SOC and the current intent's limit."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data
    now = dt_util.utcnow()
    series = [
        {
            "startTime": now.isoformat(),
            "endTime": (now + timedelta(hours=8)).isoformat(),
            "intent": {"kind": "charge/discharge", "socMin": 0.1, "socMax": 0.9},
        }
    ]
    for soc in (50.0, 52.0, 54.0):
        data = dataclasses.replace(MOCK_MOIXA_DATA, battery_soc=soc, intent_series=series)
        with patch.object(MoixaCoordinator, "_fetch", return_value=data):
            await coordinator.async_refresh()
            await hass.async_block_till_done()
        if soc < 54.0:
            freezer.tick(timedelta(minutes=15))

    rate_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{MOCK_SITE_ID}_soc_rate")
    limit_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{MOCK_SITE_ID}_soc_limit_time")
    assert float(hass.states.get(rate_id).state) == 8.0
    expected = dt_util.utcnow() + timedelta(hours=(90 - 54) / 8)
    assert abs(datetime.fromisoformat(hass.states.get(limit_id).state) - expected) < timedelta(seconds=1)
