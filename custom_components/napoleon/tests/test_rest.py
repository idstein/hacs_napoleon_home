"""Tests for AylaRest."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from importlib.resources import files

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from custom_components.napoleon.api.auth import AylaAuth, InvalidCredentials
from custom_components.napoleon.api.rest import AylaRest, CloudUnreachable
from custom_components.napoleon.regions import REGION_EU, get_region


def _fixture(name: str) -> list | dict:
    p = files("custom_components.napoleon.tests.fixtures").joinpath(name)
    return json.loads(p.read_text())


@pytest.fixture
def eu():
    return get_region(REGION_EU)


@pytest.fixture
def auth(eu):
    a = AylaAuth(eu)
    a._access_token = "at-test"
    a._expires_at = datetime.now(UTC) + timedelta(hours=1)
    return a


@pytest_asyncio.fixture
async def session() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as s:
        yield s


async def test_devices_returns_flat_list(eu, auth, session):
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", payload=_fixture("rest_devices.json"))
        rest = AylaRest(eu, auth, session=session)
        devices = await rest.devices()
        assert len(devices) == 1
        assert devices[0].dsn == "AC000TEST00000001"
        assert devices[0].oem_model == "thermometer-mqtt-eu"
        assert devices[0].key == 111111
        assert devices[0].connection_status == "Online"
        assert devices[0].model == "Prestige 500"
        assert devices[0].sw_version == "thermometer v6.0.10_EU"


async def test_properties_returns_dict_by_name(eu, auth, session):
    with aioresponses() as m:
        m.get(
            f"{eu.device_url}/apiv1/dsns/AC000TEST00000001/properties.json",
            payload=_fixture("rest_properties.json"),
        )
        rest = AylaRest(eu, auth, session=session)
        props = await rest.properties("AC000TEST00000001")
        assert props["PRB_TMP_FOUR"] == 28.0
        assert props["RSSI"] == -79
        assert props["version"] == "thermometer v6.0.10_EU"


async def test_lan_config(eu, auth, session):
    with aioresponses() as m:
        m.get(
            f"{eu.device_url}/apiv1/devices/111111/lan.json",
            payload={"lanip": {"lanip_key": "k", "lanip_key_id": 1, "keep_alive": 30}},
        )
        rest = AylaRest(eu, auth, session=session)
        lan = await rest.lan_config(111111)
        assert lan["lanip_key"] == "k"
        assert lan["lanip_key_id"] == 1


async def test_401_raises_invalid_credentials(eu, auth, session):
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", status=401)
        rest = AylaRest(eu, auth, session=session)
        with pytest.raises(InvalidCredentials):
            await rest.devices()


async def test_timeout_raises_cloud_unreachable(eu, auth, session):
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", exception=TimeoutError())
        rest = AylaRest(eu, auth, session=session)
        with pytest.raises(CloudUnreachable):
            await rest.devices()


async def test_client_error_raises_cloud_unreachable(eu, auth, session):
    with aioresponses() as m:
        m.get(
            f"{eu.device_url}/apiv1/devices.json",
            exception=aiohttp.ClientConnectionError("dns failed"),
        )
        rest = AylaRest(eu, auth, session=session)
        with pytest.raises(CloudUnreachable):
            await rest.devices()


async def test_404_returns_empty(eu, auth, session):
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices/999/lan.json", status=404)
        rest = AylaRest(eu, auth, session=session)
        result = await rest.lan_config(999)
        assert result == {}
