"""Tests for AylaAuth."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from custom_components.napoleon.api.auth import (
    AylaAuth,
    AylaAuthError,
    InvalidCredentials,
)
from custom_components.napoleon.regions import REGION_EU, get_region


@pytest.fixture
def eu():
    return get_region(REGION_EU)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as s:
        yield s


async def test_sign_in_success_returns_tokens(eu, session):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/sign_in.json",
            payload={
                "access_token": "at-1",
                "refresh_token": "rt-1",
                "expires_in": 3600,
                "role": "EndUser",
            },
            status=200,
        )
        auth = AylaAuth(eu, session=session)
        result = await auth.sign_in("user@example.com", "pw")
        assert result.access_token == "at-1"
        assert result.refresh_token == "rt-1"
        assert auth.access_token == "at-1"
        assert auth.is_valid(now=datetime.now(UTC))


async def test_sign_in_invalid_credentials_raises(eu, session):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/sign_in.json",
            payload={"errors": "invalid credentials"},
            status=401,
        )
        auth = AylaAuth(eu, session=session)
        with pytest.raises(InvalidCredentials):
            await auth.sign_in("user@example.com", "bad")


async def test_refresh_rotates_access_token(eu, session):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/refresh_token.json",
            payload={
                "access_token": "at-2",
                "refresh_token": "rt-2",
                "expires_in": 3600,
            },
            status=200,
        )
        auth = AylaAuth(eu, refresh_token="rt-1", session=session)
        await auth.refresh()
        assert auth.access_token == "at-2"
        assert auth.refresh_token == "rt-2"


async def test_refresh_401_raises_invalid_credentials(eu, session):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/refresh_token.json",
            status=401,
            payload={"errors": "invalid token"},
        )
        auth = AylaAuth(eu, refresh_token="rt-bad", session=session)
        with pytest.raises(InvalidCredentials):
            await auth.refresh()


async def test_refresh_without_refresh_token_raises(eu, session):
    auth = AylaAuth(eu, session=session)
    with pytest.raises(AylaAuthError):
        await auth.refresh()


def test_headers_includes_auth_token(eu):
    auth = AylaAuth(eu)
    auth._access_token = "at-x"
    auth._expires_at = datetime.now(UTC) + timedelta(minutes=30)
    assert auth.headers()["Authorization"] == "auth_token at-x"


def test_headers_without_token_raises(eu):
    auth = AylaAuth(eu)
    with pytest.raises(AylaAuthError):
        auth.headers()


def test_is_valid_false_when_expired(eu):
    auth = AylaAuth(eu)
    auth._access_token = "at-old"
    auth._expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert auth.is_valid(now=datetime.now(UTC)) is False


async def test_sign_in_500_raises_generic_auth_error(eu, session):
    with aioresponses() as m:
        m.post(f"{eu.user_url}/users/sign_in.json", status=500)
        auth = AylaAuth(eu, session=session)
        with pytest.raises(AylaAuthError):
            await auth.sign_in("u@e.com", "pw")
