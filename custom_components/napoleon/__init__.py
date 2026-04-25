"""Napoleon Home integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.auth import AylaAuth, AylaAuthError
from .api.rest import AylaRest, CloudUnreachable
from .const import CONF_REGION, DOMAIN
from .coordinator import NapoleonCoordinator
from .regions import get_region

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Napoleon Home from a config entry."""
    region_name = entry.data[CONF_REGION]
    refresh_token = entry.data["refresh_token"]

    region = get_region(region_name)
    session = async_get_clientsession(hass)
    auth = AylaAuth(region, refresh_token=refresh_token, session=session)

    try:
        # Initial refresh to get access token
        await auth.refresh()
    except (AylaAuthError, CloudUnreachable) as err:
        raise ConfigEntryNotReady(f"Error connecting to Ayla: {err}") from err

    rest = AylaRest(region, auth, session=session)
    coordinator = NapoleonCoordinator(hass, auth, rest)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"First refresh failed: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if (
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        and DOMAIN in hass.data
    ):
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return True
