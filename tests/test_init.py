"""Tests for Moixa integration setup and teardown."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.coordinator import MoixaCoordinator
from custom_components.moixa.moixa_py.exceptions import MoixaAuthError

from .conftest import _fake_login_and_discover
from .const import MOCK_CONFIG, MOCK_MOIXA_DATA, MOCK_SITE_ID


async def test_setup_and_unload(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Integration loads successfully and unloads cleanly."""
    assert loaded_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_runtime_data_is_coordinator(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """entry.runtime_data holds the coordinator after setup."""
    assert isinstance(loaded_entry.runtime_data, MoixaCoordinator)
    assert loaded_entry.runtime_data.site_id == MOCK_SITE_ID


async def test_setup_auth_failure(hass: HomeAssistant) -> None:
    """An auth error during _async_setup puts the entry into SETUP_ERROR (reauth required)."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, version=1)
    entry.add_to_hass(hass)

    with patch.object(
        MoixaCoordinator,
        "_login_and_discover",
        side_effect=MoixaAuthError("bad creds"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_connection_failure(hass: HomeAssistant) -> None:
    """A generic error during _async_setup puts the entry into SETUP_RETRY."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, version=1)
    entry.add_to_hass(hass)

    with patch.object(
        MoixaCoordinator,
        "_login_and_discover",
        side_effect=OSError("network unreachable"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_update_auth_failure_triggers_reauth(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """An auth error during a scheduled refresh marks the entry as requiring reauth."""
    coordinator: MoixaCoordinator = loaded_entry.runtime_data

    with patch.object(
        MoixaCoordinator,
        "_fetch",
        side_effect=MoixaAuthError("token expired"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.LOADED
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(f["context"]["source"] == "reauth" for f in flows)
