"""Ayla authentication helpers (sign_in, refresh, headers)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp

from ..regions import RegionProfile


class AylaAuthError(Exception):
    """Base class for authentication errors."""


class InvalidCredentials(AylaAuthError):  # noqa: N818 — public API name, kept stable across versions
    """Raised when Ayla rejects credentials (401)."""


@dataclass(slots=True)
class AuthResult:
    """Outcome of a sign_in / refresh_token call."""

    access_token: str
    refresh_token: str
    expires_in: int


class AylaAuth:
    """Manages the Ayla access/refresh token lifecycle for one account."""

    def __init__(
        self,
        region: RegionProfile,
        *,
        refresh_token: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._region = region
        self._refresh_token = refresh_token
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._session = session

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    def headers(self) -> dict[str, str]:
        if not self._access_token:
            raise AylaAuthError("no access token yet")
        return {
            "Authorization": f"auth_token {self._access_token}",
            "Accept": "application/json",
            "X-Ayla-App-Id": self._region.app_id,
            "X-Ayla-App-Secret": self._region.app_secret,
        }

    def is_valid(self, *, now: datetime) -> bool:
        return (
            self._access_token is not None
            and self._expires_at is not None
            and now < self._expires_at
        )

    async def sign_in(self, email: str, password: str) -> AuthResult:
        body = {
            "user": {
                "email": email,
                "password": password,
                "application": {
                    "app_id": self._region.app_id,
                    "app_secret": self._region.app_secret,
                },
            }
        }
        return await self._post(f"{self._region.user_url}/users/sign_in.json", body)

    async def refresh(self) -> AuthResult:
        if not self._refresh_token:
            raise AylaAuthError("no refresh token to refresh with")
        body = {"user": {"refresh_token": self._refresh_token}}
        return await self._post(f"{self._region.user_url}/users/refresh_token.json", body)

    async def _post(self, url: str, body: dict[str, Any]) -> AuthResult:
        owns_session = self._session is None
        session = self._session or aiohttp.ClientSession()
        try:
            async with session.post(url, json=body) as resp:
                if resp.status == 401:
                    raise InvalidCredentials(await resp.text())
                if resp.status >= 400:
                    raise AylaAuthError(f"{resp.status}: {await resp.text()}")
                payload = await resp.json()
        finally:
            if owns_session:
                await session.close()

        result = AuthResult(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token", self._refresh_token or ""),
            expires_in=int(payload.get("expires_in", 3600)),
        )
        self._access_token = result.access_token
        self._refresh_token = result.refresh_token
        self._expires_at = datetime.now(UTC) + timedelta(seconds=result.expires_in)
        return result
