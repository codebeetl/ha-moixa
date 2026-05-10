"""Shared fixtures for Moixa integration tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator

from .const import MOCK_CONFIG, MOCK_MOIXA_DATA, MOCK_SITE_ID


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:  # noqa: PT004
    """Enable custom integrations for every test in this package."""


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Prevent real setup when testing only the config flow."""
    with patch(
        "custom_components.moixa.async_setup_entry", return_value=True
    ) as mock:
        yield mock


def _fake_login_and_discover(coordinator_self: MoixaCoordinator) -> None:
    """Synchronous stub that populates coordinator attributes without hitting the API."""
    coordinator_self.site_id = MOCK_SITE_ID
    coordinator_self._client = MagicMock()


@pytest.fixture
async def loaded_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the Moixa integration with mocked API calls; return the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, unique_id=MOCK_SITE_ID, version=1
    )
    entry.add_to_hass(hass)
    with (
        patch.object(
            MoixaCoordinator,
            "_login_and_discover",
            _fake_login_and_discover,
        ),
        patch.object(
            MoixaCoordinator,
            "_fetch",
            return_value=MOCK_MOIXA_DATA,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry
