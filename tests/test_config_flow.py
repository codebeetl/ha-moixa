"""Tests for the Moixa config flow."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.moixa.const import DOMAIN
from custom_components.moixa.moixa_py.exceptions import MoixaAuthError, MoixaError

from .const import MOCK_CONFIG, MOCK_SITE_ID

_DO_LOGIN = "custom_components.moixa.config_flow._do_login"


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A valid login creates a new config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(_DO_LOGIN, return_value=MOCK_SITE_ID):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_CONFIG[CONF_USERNAME]
    assert result2["data"] == MOCK_CONFIG


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Bad credentials show the invalid_auth error and re-display the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(_DO_LOGIN, side_effect=MoixaAuthError("bad password")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """A MoixaError (e.g. no sites) maps to the cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(_DO_LOGIN, side_effect=MoixaError("no sites")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unknown_exception(hass: HomeAssistant) -> None:
    """An unexpected exception maps to the unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(_DO_LOGIN, side_effect=RuntimeError("unexpected")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Setting up the same site ID a second time aborts with already_configured."""
    # First successful setup.
    with patch(_DO_LOGIN, return_value=MOCK_SITE_ID):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )

    # Second attempt for the same account.
    with patch(_DO_LOGIN, return_value=MOCK_SITE_ID):
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input=MOCK_CONFIG
        )

    assert result3["type"] == FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Reauth with a new password updates the entry and triggers a reload."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, unique_id=MOCK_SITE_ID, version=1
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(_DO_LOGIN, return_value=MOCK_SITE_ID),
        patch("homeassistant.config_entries.ConfigEntries.async_reload") as mock_reload,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PASSWORD: "newpassword"}
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "newpassword"
    assert mock_reload.call_count == 1


async def test_reauth_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Reauth with wrong credentials shows the invalid_auth error."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, unique_id=MOCK_SITE_ID, version=1
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch(_DO_LOGIN, side_effect=MoixaAuthError("bad password")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PASSWORD: "wrongpassword"}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}
