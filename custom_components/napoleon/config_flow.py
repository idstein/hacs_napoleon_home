"""Config flow for Napoleon Home integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.auth import AylaAuth, AylaAuthError, InvalidCredentials
from .const import CONF_REGION, DOMAIN
from .regions import KNOWN_REGIONS, get_region

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION): vol.In(KNOWN_REGIONS),
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    region_name = data[CONF_REGION]
    email = data[CONF_EMAIL]
    password = data[CONF_PASSWORD]

    region = get_region(region_name)
    session = async_get_clientsession(hass)
    auth = AylaAuth(region, session=session)

    try:
        result = await auth.sign_in(email, password)
    except InvalidCredentials:
        return {"base": "invalid_auth"}
    except AylaAuthError:
        return {"base": "cannot_connect"}
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        return {"base": "unknown"}

    return {"refresh_token": result.refresh_token}

class NapoleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Napoleon Home."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, Any] = {}
        if user_input is not None:
            res = await validate_input(self.hass, user_input)
            if not (errors := {k: v for k, v in res.items() if k == "base"}):
                unique_id = f"{user_input[CONF_REGION]}:{user_input[CONF_EMAIL]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                data = {
                    CONF_REGION: user_input[CONF_REGION],
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    "refresh_token": res["refresh_token"],
                }
                return self.async_create_entry(title=user_input[CONF_EMAIL], data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication."""
        errors: dict[str, Any] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            # Combine existing data with new password for validation
            validation_data = {
                CONF_REGION: reauth_entry.data[CONF_REGION],
                CONF_EMAIL: reauth_entry.data[CONF_EMAIL],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            
            res = await validate_input(self.hass, validation_data)
            if not (errors := {k: v for k, v in res.items() if k == "base"}):
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        "refresh_token": res["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
            errors=errors,
        )
