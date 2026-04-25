"""Sensor platform for Napoleon Home."""
from __future__ import annotations

from typing import Any, cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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
    for dsn in coordinator.dsns:
        # Base sensors
        entities.append(NapoleonSensor(coordinator, dsn, "Software Version", "sw_version"))
        entities.append(NapoleonSensor(coordinator, dsn, "Connection Status", "connection_status"))
        
        # Property sensors (if data available)
        data = coordinator.data.get(dsn, {})
        properties = data.get("properties", {})
        for prop_name in properties:
            entities.append(NapoleonPropertySensor(coordinator, dsn, prop_name))

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
    def device_info(self) -> DeviceInfo | None:
        """Return device information."""
        device = self.coordinator.data.get(self._dsn, {}).get("device")
        if not device:
            return DeviceInfo(
                identifiers={(DOMAIN, self._dsn)},
                name=f"Napoleon {self._dsn}",
                manufacturer="Napoleon",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._dsn)},
            name=device.product_name or f"Napoleon {self._dsn}",
            manufacturer="Napoleon",
            model=device.model,
            sw_version=device.sw_version,
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        device = self.coordinator.data.get(self._dsn, {}).get("device")
        if not device:
            return None
        return cast(str | None, getattr(device, self._attribute))


class NapoleonPropertySensor(CoordinatorEntity[NapoleonCoordinator], SensorEntity):
    """Representation of a Napoleon property sensor."""

    def __init__(
        self,
        coordinator: NapoleonCoordinator,
        dsn: str,
        prop_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._dsn = dsn
        self._prop_name = prop_name
        self._attr_name = f"Napoleon {dsn} {prop_name}"
        self._attr_unique_id = f"{dsn}_{prop_name}"
        
        # Set device class based on name
        if "TMP" in prop_name:
            self._attr_device_class = "temperature"
            self._attr_native_unit_of_measurement = "°C"  # Assume Celsius for now

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information."""
        device = self.coordinator.data.get(self._dsn, {}).get("device")
        if not device:
            return DeviceInfo(
                identifiers={(DOMAIN, self._dsn)},
                name=f"Napoleon {self._dsn}",
                manufacturer="Napoleon",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._dsn)},
            name=device.product_name or f"Napoleon {self._dsn}",
            manufacturer="Napoleon",
            model=device.model,
            sw_version=device.sw_version,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        properties = self.coordinator.data.get(self._dsn, {}).get("properties", {})
        return properties.get(self._prop_name)
