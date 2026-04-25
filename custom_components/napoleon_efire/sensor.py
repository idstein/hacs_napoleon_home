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


# Property mapping to readable names
PROP_MAP = {
    "PRB_TMP_ONE": "Probe 1",
    "PRB_TMP_TWO": "Probe 2",
    "PRB_TMP_THREE": "Probe 3",
    "PRB_TMP_FOUR": "Probe 4",
    "TNK_WT": "Tank Level",
    "RSSI": "Signal Strength",
}

# Properties to exclude if they aren't useful as standalone sensors
EXCLUDE_PROPS = {"TUNIT", "EMTY_TNK_W", "F_TNKWT", "version"}

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
        
        # Property sensors
        data = coordinator.data.get(dsn, {})
        properties = data.get("properties", {})
        for prop_name in properties:
            if prop_name in EXCLUDE_PROPS:
                continue
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
        self._attr_name = name
        self._attr_unique_id = f"{dsn}_{attribute}"
        self._attr_has_entity_name = True

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
        self._attr_name = PROP_MAP.get(prop_name, prop_name)
        self._attr_unique_id = f"{dsn}_{prop_name}"
        self._attr_has_entity_name = True
        
        # Set device class and units
        if "TMP" in prop_name:
            self._attr_device_class = "temperature"
            self._attr_native_unit_of_measurement = "°C"
        elif prop_name == "TNK_WT":
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:gas-cylinder"
        elif prop_name == "RSSI":
            self._attr_device_class = "signal_strength"
            self._attr_native_unit_of_measurement = "dBm"

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
        data = self.coordinator.data.get(self._dsn, {})
        properties = data.get("properties", {})
        raw_prop = properties.get(self._prop_name)
        
        if not raw_prop or not isinstance(raw_prop, dict):
            return None
            
        val = raw_prop.get("value")

        # Handle temperature probes sitting at 0 when disconnected
        if "TMP" in self._prop_name and val == 0:
            return None

        # Calculate tank percentage
        if self._prop_name == "TNK_WT":
            if val is None:
                return None
            
            # Extract raw values from dicts for calculation
            empty_prop = properties.get("EMTY_TNK_W")
            full_prop = properties.get("F_TNKWT")
            
            empty = (empty_prop.get("value") if isinstance(empty_prop, dict) else None) or 13000
            full = (full_prop.get("value") if isinstance(full_prop, dict) else None) or 24000
            
            _LOGGER.error(
                "DIAGNOSTIC WEIGHTS: DSN=%s, val=%s, empty=%s, full=%s",
                self._dsn, val, empty, full
            )
            
            # Heuristic: If empty == capacity (like 11000), it's likely reporting net weight.
            # If val is close to full and full is ~2x empty, it's likely net weight.
            if empty == 11000 and full == 22000:
                # Grill is reporting net gas weight (0 to 11000)
                pct = (val / 11000) * 100
            elif full > empty:
                if val < empty and val > 0:
                    # Likely net weight
                    pct = (val / (full - empty)) * 100
                else:
                    # Likely total weight
                    pct = ((val - empty) / (full - empty)) * 100
            else:
                return None
                
            return round(max(0, min(100, pct)), 1)

        return val
