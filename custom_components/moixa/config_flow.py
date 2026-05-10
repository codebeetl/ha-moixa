"""Config flow for the Moixa integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector

from .const import DOMAIN
from .moixa_py import MoixaCognitoAuth, MoixaClient
from .moixa_py.exceptions import MoixaAuthError, MoixaError

_LOGGER = logging.getLogger(__name__)

_EMAIL_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
)
_PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): _EMAIL_SELECTOR,
        vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR,
    }
)


def _do_login(username: str, password: str) -> str:
    """Synchronous: authenticate and return the siteId for the account."""
    tokens = MoixaCognitoAuth(username, password).login()
    client = MoixaClient(tokens)
    site_users = client.get_site_users()
    if not site_users:
        raise MoixaError("No sites found for this account")
    return site_users[0]["siteId"]


class MoixaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moixa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                site_id = await self.hass.async_add_executor_job(
                    _do_login,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except MoixaAuthError:
                errors["base"] = "invalid_auth"
            except MoixaError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Moixa setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(site_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start the reauthentication flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth form submission."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    _do_login,
                    entry.data[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except MoixaAuthError:
                errors["base"] = "invalid_auth"
            except MoixaError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Moixa reauth")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
