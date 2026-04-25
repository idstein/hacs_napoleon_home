"""Sensor platform for Napoleon Home."""
from __future__ import annotations

from typing import cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NapoleonCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: NapoleonCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for dsn in coordinator.data:
        entities.append(NapoleonSensor(coordinator, dsn, "Software Version", "sw_version"))
        entities.append(NapoleonSensor(coordinator, dsn, "Connection Status", "connection_status"))

    async_add_entities(entities)

class NapoleonSensor(CoordinatorEntity[NapoleonCoordinator], SensorEntity):
    """Representation of a Napoleon sensor."""

    def __init__(
        self,
        coordinator: NapoleonCoordinator,
        dsn: str,
        name: str,
        attribute: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._dsn = dsn
        self._attribute = attribute
        self._attr_name = f"Napoleon {dsn} {name}"
        self._attr_unique_id = f"{dsn}_{attribute}"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.coordinator.data.get(self._dsn, {}).get("device")
        if not device:
            return None
        return cast(str | None, getattr(device, self._attribute))
