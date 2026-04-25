"""Unit tests for region profiles."""

from __future__ import annotations

import pytest

from custom_components.napoleon_efire.regions import (
    REGION_EU,
    REGION_US,
    UnknownRegion,
    get_region,
)


def test_eu_profile_has_expected_endpoints() -> None:
    profile = get_region(REGION_EU)
    assert profile.user_url == "https://user-field-eu.aylanetworks.com"
    assert profile.device_url == "https://ads-eu.aylanetworks.com"
    assert profile.mqtt_host == "mqtt-field-eu.aylanetworks.com"
    assert profile.mqtt_port == 8883
    assert profile.app_id == "smarthome_eu-rA-hQ-id-5Q-id"
    assert profile.app_secret.startswith("smarthome_eu-")


def test_us_profile_has_expected_endpoints() -> None:
    profile = get_region(REGION_US)
    assert profile.user_url == "https://user-field.aylanetworks.com"
    assert profile.device_url == "https://ads-field.aylanetworks.com"
    assert profile.mqtt_host == "mqtt-usfield.aylanetworks.com"
    assert profile.app_id == "smarthome_dev-rA-hQ-id"


def test_unknown_region_raises() -> None:
    with pytest.raises(UnknownRegion):
        get_region("CA")


def test_region_profile_is_frozen() -> None:
    profile = get_region(REGION_EU)
    with pytest.raises((AttributeError, TypeError)):
        profile.mqtt_port = 1234  # type: ignore[misc]
