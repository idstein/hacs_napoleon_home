"""Per-region Ayla cloud endpoints and app credentials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REGION_EU: Final = "EU"
REGION_US: Final = "US"


class UnknownRegion(KeyError):  # noqa: N818 — public API name, kept stable across versions
    """Raised when a region string has no profile."""


@dataclass(frozen=True, slots=True)
class RegionProfile:
    """Endpoints and app credentials for one Ayla regional cloud."""

    name: str
    user_url: str
    device_url: str
    mqtt_host: str
    mqtt_port: int
    app_id: str
    app_secret: str


# App secrets below are public Ayla SDK values extracted from the Napoleon Home
# APKs (EU: com.napoleon.connected.eu, US: com.napoleon.connected). They are
# baked into the mobile apps and are not user credentials — ruff S106 does not
# apply.
_REGION_PROFILES: Final[dict[str, RegionProfile]] = {
    REGION_EU: RegionProfile(
        name=REGION_EU,
        user_url="https://user-field-eu.aylanetworks.com",
        device_url="https://ads-eu.aylanetworks.com",
        mqtt_host="mqtt-field-eu.aylanetworks.com",
        mqtt_port=8883,
        app_id="smarthome_eu-rA-hQ-id-5Q-id",
        app_secret="smarthome_eu-rA-hQ-id-gHzZGo5048znNn0F9nuyc_PSyBw",  # noqa: S106
    ),
    REGION_US: RegionProfile(
        name=REGION_US,
        user_url="https://user-field.aylanetworks.com",
        device_url="https://ads-field.aylanetworks.com",
        mqtt_host="mqtt-usfield.aylanetworks.com",
        mqtt_port=8883,
        app_id="smarthome_dev-rA-hQ-id",
        app_secret="smarthome_dev-BBeF7xY8xfKBfNcFIx-rhQhA2YY-h64jEJ5ZhCy9GOaWiy0XkbnGc1g",  # noqa: S106
    ),
}

KNOWN_REGIONS: Final = tuple(_REGION_PROFILES.keys())


def get_region(name: str) -> RegionProfile:
    """Return the profile for ``name`` or raise ``UnknownRegion``."""
    try:
        return _REGION_PROFILES[name]
    except KeyError as err:
        raise UnknownRegion(name) from err
