"""Constants for the Napoleon Home integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "napoleon"

CONF_REGION: Final = "region"
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_HEARTBEAT_INTERVAL: Final = "heartbeat_interval"
CONF_DIAGNOSTIC_LOGGING: Final = "diagnostic_logging"

DEFAULT_HEARTBEAT_INTERVAL: Final = 300  # seconds
MIN_HEARTBEAT_INTERVAL: Final = 60
MAX_HEARTBEAT_INTERVAL: Final = 3600

TOKEN_REFRESH_MARGIN: Final = 300  # refresh N seconds before expiry
PROPERTY_UPDATE_STALE_SECONDS: Final = 90  # "online via recent update" threshold

MQTT_RECONNECT_BACKOFFS: Final = (1, 2, 5, 15, 60)  # seconds
