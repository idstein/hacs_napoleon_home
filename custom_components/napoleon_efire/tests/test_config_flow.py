"""Tests for the Napoleon Home config flow."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from custom_components.napoleon_efire.api.auth import AuthResult, AylaAuthError, InvalidCredentials
from custom_components.napoleon_efire.const import CONF_REGION, DOMAIN


async def test_flow_user_init(hass: HomeAssistant) -> None:
    """Test the user step has a form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

async def test_flow_user_success(hass: HomeAssistant) -> None:
    """Test successful config flow."""
    with patch(
        "custom_components.napoleon_efire.api.auth.AylaAuth.sign_in",
        return_value=AuthResult("at", "rt", 3600),
    ), patch(
        "custom_components.napoleon_efire.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_REGION: "EU",
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test-password",
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "test@example.com"
        assert result["data"] == {
            CONF_REGION: "EU",
            CONF_EMAIL: "test@example.com",
            "refresh_token": "rt",
        }
        await hass.async_block_till_done()
        assert len(mock_setup.mock_calls) == 1

async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test invalid authentication."""
    with patch(
        "custom_components.napoleon_efire.api.auth.AylaAuth.sign_in",
        side_effect=InvalidCredentials,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_REGION: "EU",
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test-password",
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}

async def test_flow_user_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection error."""
    with patch(
        "custom_components.napoleon_efire.api.auth.AylaAuth.sign_in",
        side_effect=AylaAuthError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_REGION: "EU",
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test-password",
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
