"""DataUpdateCoordinator for Napoleon Home."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.auth import AylaAuth, AylaAuthError, InvalidCredentials
from .api.rest import AylaRest, CloudUnreachable, Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class NapoleonCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Napoleon data."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth: AylaAuth,
        rest: AylaRest,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.auth = auth
        self.rest = rest
        self.devices: list[Device] = []
        self.dsns: set[str] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via REST API."""
        try:
            if not self.auth.is_valid(now=dt_util.utcnow()):
                 await self.auth.refresh()

            self.devices = await self.rest.devices()
            data = {}
            for device in self.devices:
                self.dsns.add(device.dsn)
                props = await self.rest.properties(device.dsn)
                data[device.dsn] = {
                    "device": device,
                    "properties": props,
                }
            return data
        except (AylaAuthError, InvalidCredentials, CloudUnreachable) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
