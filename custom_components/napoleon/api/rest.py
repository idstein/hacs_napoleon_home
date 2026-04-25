"""Ayla REST client for device + property + LAN config calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from ..regions import RegionProfile
from .auth import AylaAuth, AylaAuthError, InvalidCredentials


class CloudUnreachable(Exception):  # noqa: N818 — public API name, kept stable across versions
    """Network-level failure to reach Ayla cloud (timeouts, DNS, refused)."""


@dataclass(slots=True, frozen=True)
class Device:
    """Ayla-registered device summary."""

    dsn: str
    product_name: str
    model: str | None
    oem_model: str
    key: int
    lan_ip: str | None
    connection_status: str
    mac: str | None
    sw_version: str | None


class AylaRest:
    """Thin async REST wrapper around the Ayla device service."""

    def __init__(
        self,
        region: RegionProfile,
        auth: AylaAuth,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._region = region
        self._auth = auth
        self._session = session

    async def devices(self) -> list[Device]:
        payload = await self._get(f"{self._region.device_url}/apiv1/devices.json")
        if isinstance(payload, dict) and "devices" in payload:
            payload = payload["devices"]

        out: list[Device] = []
        if not isinstance(payload, list):
            return out

        for raw in payload:
            d = raw.get("device", raw)
            out.append(
                Device(
                    dsn=d["dsn"],
                    product_name=d.get("product_name", ""),
                    model=d.get("model"),
                    oem_model=d.get("oem_model", ""),
                    key=int(d.get("key", 0)),
                    lan_ip=d.get("lan_ip"),
                    connection_status=d.get("connection_status", "Unknown"),
                    mac=d.get("mac"),
                    sw_version=d.get("sw_version"),
                )
            )
        return out

    async def properties(self, dsn: str) -> dict[str, Any]:
        raw = await self._get(f"{self._region.device_url}/apiv1/dsns/{dsn}/properties.json")
        out: dict[str, Any] = {}
        for item in raw:
            prop = item.get("property", item)
            out[prop["name"]] = prop.get("value")
        return out

    async def lan_config(self, device_key: int) -> dict[str, Any]:
        raw = await self._get(f"{self._region.device_url}/apiv1/devices/{device_key}/lan.json")
        if not isinstance(raw, dict):
            return {}
        lanip = raw.get("lanip", raw)
        return lanip if isinstance(lanip, dict) else {}

    async def _get(self, url: str) -> Any:
        owns_session = self._session is None
        session = self._session or aiohttp.ClientSession()
        try:
            try:
                async with session.get(
                    url,
                    headers=self._auth.headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 401:
                        raise InvalidCredentials(await resp.text())
                    if resp.status == 404:
                        return {}
                    if resp.status >= 400:
                        raise AylaAuthError(f"{resp.status}: {await resp.text()}")
                    return await resp.json()
            except TimeoutError as err:
                raise CloudUnreachable("timeout") from err
            except aiohttp.ClientError as err:
                raise CloudUnreachable(str(err)) from err
        finally:
            if owns_session:
                await session.close()
