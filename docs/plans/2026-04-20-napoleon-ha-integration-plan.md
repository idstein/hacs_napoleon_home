# Napoleon HA Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship v1 of the `napoleon` HACS integration as specified in `docs/plans/2026-04-20-napoleon-ha-integration-design.md`: read-only sensors, EU+US Ayla cloud, MQTT push with REST heartbeat, grill-offline-is-normal semantics, HACS-installable.

**Architecture:** One Python package `custom_components/napoleon` with a coordinator that owns an `AylaAuth`, `AylaRest`, and `AylaMqttClient`. Per-region config (EU/US), per-oem-model property maps, TDD with `pytest-homeassistant-custom-component` and `aiohttp_client_mock` + a fake MQTT broker.

**Tech Stack:** Python 3.12+, Home Assistant ≥2025.1, `aiohttp`, `aiomqtt>=2.0`, `pytest-homeassistant-custom-component`, `ruff`, `mypy`, `hacs/action`, `home-assistant/actions/hassfest`.

**Reference sub-skills to invoke during execution:**

- `@superpowers:test-driven-development` — use for every task that writes a test
- `@superpowers:verification-before-completion` — use before marking any task complete (pytest / ruff / mypy must pass)
- `@superpowers:executing-plans` — the meta-skill that drives this plan

---

## Ground rules

- **TDD strictly.** Test fails before implementation. Implementation is minimal to make the test pass. Refactor after green.
- **Commit after every task.** Messages follow Conventional Commits: `feat(auth): …`, `test(rest): …`, `chore(ci): …`, `docs: …`. Every commit message ends with the `Co-Authored-By` line.
- **Never commit credentials.** Fixtures use placeholder DSN `AC000TEST00000001`, placeholder email `test@example.com`, placeholder refresh_token `rt-placeholder-1`.
- **Git identity** must be `paulidstein@gmail.com` / `Paul Strawder`. Confirm with `git config user.email` once per session.
- **Run tests from repo root** with the project venv activated.
- **CI must be green** before merging any phase-completion PR. For a solo-maintainer public repo this means: push to `main` only after the task's local checks pass; watch GH Actions and fix any gap before starting the next task.

---

## Phase 0 — Repo scaffolding

### Task 0.1 — Python project + dev dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `requirements-dev.txt`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "hacs-napoleon-home"
version = "0.0.0"
description = "Home Assistant custom integration for Napoleon Connected grills"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Paul Strawder" }]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "N", "UP", "ASYNC", "S", "C4", "SIM", "RUF"]
ignore = ["S101"]  # allow asserts in tests

[tool.ruff.lint.per-file-ignores]
"custom_components/napoleon/tests/*" = ["S", "ASYNC"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["custom_components/napoleon/tests"]
asyncio_mode = "auto"
addopts = "--cov=custom_components.napoleon --cov-report=term-missing"
```

**Step 2: Create `.python-version`**

```
3.12
```

**Step 3: Create `requirements-dev.txt`**

```
pytest==8.3.*
pytest-asyncio==0.24.*
pytest-cov==5.*
pytest-homeassistant-custom-component==0.13.*
ruff==0.7.*
mypy==1.13.*
aioresponses==0.7.*
```

**Step 4: Set up venv, install, verify**

```bash
cd /Users/pstrawder/PycharmProjects/hacs_napoleon_home
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
ruff --version
mypy --version
pytest --version
```

Expected: each `--version` prints cleanly.

**Step 5: Commit**

```bash
git add pyproject.toml .python-version requirements-dev.txt
git commit -m "chore: add python project + dev tooling

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.2 — HACS manifest and info page

**Files:**
- Create: `hacs.json`
- Create: `info.md`

**Step 1: Create `hacs.json`**

```json
{
  "name": "Napoleon Home",
  "content_in_root": false,
  "render_readme": true,
  "homeassistant": "2025.1.0",
  "zip_release": false
}
```

**Step 2: Create `info.md`**

```markdown
# Napoleon Home

Cloud-push Home Assistant integration for Napoleon Connected grills (Prestige 500 today; Prestige Pro and others as contributors add property maps).

- EU and US Ayla regions
- Read-only in v1: probe temperatures, tank weight, firmware, connectivity, alerts
- Offline-aware: the grill is off most of the time; sensors go `unavailable` silently

See the [repository README](https://github.com/idstein/hacs_napoleon_home) for install and configuration.
```

**Step 3: Commit**

```bash
git add hacs.json info.md
git commit -m "chore(hacs): add hacs manifest and info page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 0.3 — CI: HACS validate + hassfest workflow

**Files:**
- Create: `.github/workflows/validate.yml`

**Step 1: Create workflow**

```yaml
name: Validate

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

**Step 2: Commit + push + watch**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: add HACS and hassfest validation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin main
gh run watch
```

Expected: `hacs` job passes (no integration yet — validates repo shape). `hassfest` job will fail because there's no manifest.json; that's expected. Continue to Task 0.4 which will turn it green.

---

### Task 0.4 — Minimal `manifest.json` so hassfest passes

**Files:**
- Create: `custom_components/napoleon/__init__.py` (empty)
- Create: `custom_components/napoleon/manifest.json`

**Step 1: Create empty `__init__.py`**

```python
"""Napoleon Home integration for Home Assistant."""
```

**Step 2: Create `manifest.json`**

```json
{
  "domain": "napoleon",
  "name": "Napoleon Home",
  "codeowners": ["@idstein"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/idstein/hacs_napoleon_home",
  "iot_class": "cloud_push",
  "issue_tracker": "https://github.com/idstein/hacs_napoleon_home/issues",
  "requirements": ["aiomqtt>=2.3.0"],
  "version": "0.1.0"
}
```

**Step 3: Push and watch validation**

```bash
git add custom_components/napoleon/__init__.py custom_components/napoleon/manifest.json
git commit -m "feat: add empty napoleon integration scaffold

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push
gh run watch
```

Expected: both `hacs` and `hassfest` pass.

---

### Task 0.5 — Lint + test CI workflows

**Files:**
- Create: `.github/workflows/lint.yml`
- Create: `.github/workflows/test.yml`

**Step 1: Lint workflow**

```yaml
name: Lint
on: [push, pull_request]
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff==0.7.*
      - run: ruff check .
      - run: ruff format --check .
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: mypy custom_components/napoleon
```

**Step 2: Test workflow**

```yaml
name: Test
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ matrix.python-version }} }
      - run: pip install -r requirements-dev.txt
      - run: pytest
```

**Step 3: Run locally to verify green before push**

```bash
ruff check . && ruff format --check .
mypy custom_components/napoleon
pytest custom_components/napoleon/tests/ || echo "no tests yet — expected"
```

Expected: ruff + mypy green. pytest reports no tests collected (fine).

**Step 4: Commit + push + watch**

```bash
git add .github/workflows/lint.yml .github/workflows/test.yml
git commit -m "ci: add lint and test workflows

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push
gh run watch
```

Expected: lint green, test green (empty collection is not an error with `--cov-fail-under` not set yet; we add the gate later).

---

## Phase 1 — Pure-logic building blocks

### Task 1.1 — `const.py`

**Files:**
- Create: `custom_components/napoleon/const.py`

**Step 1: Write**

```python
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
```

**Step 2: Verify**

```bash
python -c "from custom_components.napoleon.const import DOMAIN; print(DOMAIN)"
```

Expected: `napoleon`

**Step 3: Commit**

```bash
git add custom_components/napoleon/const.py
git commit -m "feat: add const.py with domain and config keys

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.2 — `regions.py` (TDD)

**Files:**
- Create: `custom_components/napoleon/tests/__init__.py` (empty)
- Create: `custom_components/napoleon/tests/test_regions.py`
- Create: `custom_components/napoleon/regions.py`

**Step 1: Write the failing test**

`custom_components/napoleon/tests/test_regions.py`:

```python
"""Unit tests for region profiles."""

from __future__ import annotations

import pytest

from custom_components.napoleon.regions import (
    REGION_EU,
    REGION_US,
    RegionProfile,
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
    with pytest.raises(AttributeError):
        profile.mqtt_port = 1234  # type: ignore[misc]
```

**Step 2: Run test — expect failure**

```bash
pytest custom_components/napoleon/tests/test_regions.py -v
```

Expected: `ImportError` — `regions` module does not exist yet.

**Step 3: Implement `regions.py`**

```python
"""Per-region Ayla cloud endpoints and app credentials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REGION_EU: Final = "EU"
REGION_US: Final = "US"


class UnknownRegion(KeyError):
    """Raised when a region string has no profile."""


@dataclass(frozen=True, slots=True)
class RegionProfile:
    name: str
    user_url: str
    device_url: str
    mqtt_host: str
    mqtt_port: int
    app_id: str
    app_secret: str


_REGION_PROFILES: Final[dict[str, RegionProfile]] = {
    REGION_EU: RegionProfile(
        name=REGION_EU,
        user_url="https://user-field-eu.aylanetworks.com",
        device_url="https://ads-eu.aylanetworks.com",
        mqtt_host="mqtt-field-eu.aylanetworks.com",
        mqtt_port=8883,
        app_id="smarthome_eu-rA-hQ-id-5Q-id",
        app_secret="smarthome_eu-rA-hQ-id-gHzZGo5048znNn0F9nuyc_PSyBw",
    ),
    REGION_US: RegionProfile(
        name=REGION_US,
        user_url="https://user-field.aylanetworks.com",
        device_url="https://ads-field.aylanetworks.com",
        mqtt_host="mqtt-usfield.aylanetworks.com",
        mqtt_port=8883,
        app_id="smarthome_dev-rA-hQ-id",
        app_secret="smarthome_dev-BBeF7xY8xfKBfNcFIx-rhQhA2YY-h64jEJ5ZhCy9GOaWiy0XkbnGc1g",
    ),
}

KNOWN_REGIONS: Final = tuple(_REGION_PROFILES.keys())


def get_region(name: str) -> RegionProfile:
    try:
        return _REGION_PROFILES[name]
    except KeyError as err:
        raise UnknownRegion(name) from err
```

**Step 4: Run test — expect pass**

```bash
pytest custom_components/napoleon/tests/test_regions.py -v
```

Expected: 4 passed.

**Step 5: Commit**

```bash
git add custom_components/napoleon/tests/__init__.py \
        custom_components/napoleon/tests/test_regions.py \
        custom_components/napoleon/regions.py
git commit -m "feat(regions): add EU/US profiles with unit tests

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.3 — `AylaAuth` (TDD)

**Files:**
- Create: `custom_components/napoleon/api/__init__.py` (empty)
- Create: `custom_components/napoleon/api/auth.py`
- Create: `custom_components/napoleon/tests/test_auth.py`

**Step 1: Write failing tests**

`test_auth.py`:

```python
"""Tests for AylaAuth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
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


async def test_sign_in_success_returns_tokens(eu, aioclient_mock):
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
        auth = AylaAuth(eu)
        result = await auth.sign_in("user@example.com", "pw")
        assert result.access_token == "at-1"
        assert result.refresh_token == "rt-1"
        assert auth.access_token == "at-1"
        assert auth.is_valid(now=datetime.now(UTC))


async def test_sign_in_invalid_credentials_raises(eu):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/sign_in.json",
            payload={"errors": "invalid credentials"},
            status=401,
        )
        auth = AylaAuth(eu)
        with pytest.raises(InvalidCredentials):
            await auth.sign_in("user@example.com", "bad")


async def test_refresh_rotates_access_token(eu):
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
        auth = AylaAuth(eu, refresh_token="rt-1")
        await auth.refresh()
        assert auth.access_token == "at-2"
        assert auth.refresh_token == "rt-2"


async def test_refresh_401_raises_invalid_credentials(eu):
    with aioresponses() as m:
        m.post(
            f"{eu.user_url}/users/refresh_token.json",
            status=401,
            payload={"errors": "invalid token"},
        )
        auth = AylaAuth(eu, refresh_token="rt-bad")
        with pytest.raises(InvalidCredentials):
            await auth.refresh()


async def test_headers_includes_auth_token(eu):
    auth = AylaAuth(eu)
    auth._access_token = "at-x"  # test-only direct set
    auth._expires_at = datetime.now(UTC) + timedelta(minutes=30)
    assert auth.headers()["Authorization"] == "auth_token at-x"


async def test_sign_in_500_raises_generic_auth_error(eu):
    with aioresponses() as m:
        m.post(f"{eu.user_url}/users/sign_in.json", status=500)
        auth = AylaAuth(eu)
        with pytest.raises(AylaAuthError):
            await auth.sign_in("u@e.com", "pw")
```

**Step 2: Run test — expect ImportError**

```bash
pytest custom_components/napoleon/tests/test_auth.py -v
```

Expected: ImportError on `auth` module.

**Step 3: Implement `api/auth.py`**

```python
"""Ayla authentication helpers (sign_in, refresh, headers)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import aiohttp

from ..regions import RegionProfile

_LOGGER = logging.getLogger(__name__)


class AylaAuthError(Exception):
    """Base class for authentication errors."""


class InvalidCredentials(AylaAuthError):
    """Raised when Ayla rejects credentials (401)."""


@dataclass(slots=True)
class AuthResult:
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

    async def _post(self, url: str, body: dict) -> AuthResult:
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
```

**Step 4: Run tests — expect pass**

```bash
pytest custom_components/napoleon/tests/test_auth.py -v
```

Expected: 6 passed.

**Step 5: Commit**

```bash
git add custom_components/napoleon/api/__init__.py \
        custom_components/napoleon/api/auth.py \
        custom_components/napoleon/tests/test_auth.py
git commit -m "feat(auth): add AylaAuth with sign_in/refresh + tests

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 1.4 — `AylaRest` (TDD)

**Files:**
- Create: `custom_components/napoleon/api/rest.py`
- Create: `custom_components/napoleon/tests/test_rest.py`
- Create: `custom_components/napoleon/tests/fixtures/__init__.py`
- Create: `custom_components/napoleon/tests/fixtures/rest_devices.json`
- Create: `custom_components/napoleon/tests/fixtures/rest_properties.json`

**Step 1: Create fixture files**

`rest_devices.json`:

```json
[
  {
    "device": {
      "dsn": "AC000TEST00000001",
      "product_name": "Prestige",
      "model": "Prestige 500",
      "oem_model": "thermometer-mqtt-eu",
      "key": 111111,
      "lan_ip": "10.0.0.82",
      "lan_enabled": true,
      "connection_status": "Online",
      "mac": "aa:bb:cc:dd:ee:ff",
      "sw_version": "thermometer v6.0.10_EU"
    }
  }
]
```

`rest_properties.json`:

```json
[
  {"property": {"name": "PRB_TMP_ONE", "value": 0.0, "base_type": "decimal", "direction": "output"}},
  {"property": {"name": "PRB_TMP_FOUR", "value": 28.0, "base_type": "decimal", "direction": "output"}},
  {"property": {"name": "TUNIT", "value": 0, "base_type": "boolean", "direction": "input"}},
  {"property": {"name": "TNK_WT", "value": 7910, "base_type": "integer", "direction": "output"}},
  {"property": {"name": "EMTY_TNK_W", "value": 13000, "base_type": "integer", "direction": "input"}},
  {"property": {"name": "F_TNKWT", "value": 24000, "base_type": "integer", "direction": "input"}},
  {"property": {"name": "RSSI", "value": -79, "base_type": "integer", "direction": "output"}},
  {"property": {"name": "version", "value": "thermometer v6.0.10_EU", "base_type": "string", "direction": "output"}}
]
```

**Step 2: Write failing tests**

`test_rest.py`:

```python
"""Tests for AylaRest."""

from __future__ import annotations

import json
from importlib.resources import files

import pytest
from aioresponses import aioresponses

from custom_components.napoleon.api.auth import AylaAuth
from custom_components.napoleon.api.rest import AylaRest
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
    from datetime import UTC, datetime, timedelta
    a._expires_at = datetime.now(UTC) + timedelta(hours=1)
    return a


async def test_devices_returns_flat_list(eu, auth):
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", payload=_fixture("rest_devices.json"))
        rest = AylaRest(eu, auth)
        devices = await rest.devices()
        assert len(devices) == 1
        assert devices[0].dsn == "AC000TEST00000001"
        assert devices[0].oem_model == "thermometer-mqtt-eu"
        assert devices[0].key == 111111
        assert devices[0].connection_status == "Online"


async def test_properties_returns_dict_by_name(eu, auth):
    with aioresponses() as m:
        m.get(
            f"{eu.device_url}/apiv1/dsns/AC000TEST00000001/properties.json",
            payload=_fixture("rest_properties.json"),
        )
        rest = AylaRest(eu, auth)
        props = await rest.properties("AC000TEST00000001")
        assert props["PRB_TMP_FOUR"] == 28.0
        assert props["RSSI"] == -79


async def test_lan_config(eu, auth):
    with aioresponses() as m:
        m.get(
            f"{eu.device_url}/apiv1/devices/111111/lan.json",
            payload={"lanip": {"lanip_key": "k", "lanip_key_id": 1, "keep_alive": 30}},
        )
        rest = AylaRest(eu, auth)
        lan = await rest.lan_config(111111)
        assert lan["lanip_key"] == "k"


async def test_401_raises_invalid_credentials(eu, auth):
    from custom_components.napoleon.api.auth import InvalidCredentials
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", status=401)
        rest = AylaRest(eu, auth)
        with pytest.raises(InvalidCredentials):
            await rest.devices()


async def test_timeout_raises_cannot_connect(eu, auth):
    from custom_components.napoleon.api.rest import CloudUnreachable
    import asyncio
    with aioresponses() as m:
        m.get(f"{eu.device_url}/apiv1/devices.json", exception=asyncio.TimeoutError())
        rest = AylaRest(eu, auth)
        with pytest.raises(CloudUnreachable):
            await rest.devices()
```

**Step 3: Run test — expect ImportError**

```bash
pytest custom_components/napoleon/tests/test_rest.py -v
```

**Step 4: Implement `api/rest.py`**

```python
"""Ayla REST client for device + property + LAN config calls."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from ..regions import RegionProfile
from .auth import AylaAuth, AylaAuthError, InvalidCredentials

_LOGGER = logging.getLogger(__name__)


class CloudUnreachable(Exception):
    """Network-level failure to reach Ayla cloud."""


@dataclass(slots=True, frozen=True)
class Device:
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
        out: list[Device] = []
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
        raw = await self._get(
            f"{self._region.device_url}/apiv1/devices/{device_key}/lan.json"
        )
        return raw.get("lanip", raw)

    async def _get(self, url: str) -> Any:
        owns_session = self._session is None
        session = self._session or aiohttp.ClientSession()
        try:
            async with session.get(url, headers=self._auth.headers(), timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 401:
                    raise InvalidCredentials(await resp.text())
                if resp.status == 404:
                    return {}
                if resp.status >= 400:
                    raise AylaAuthError(f"{resp.status}: {await resp.text()}")
                return await resp.json()
        except asyncio.TimeoutError as err:
            raise CloudUnreachable("timeout") from err
        except aiohttp.ClientError as err:
            raise CloudUnreachable(str(err)) from err
        finally:
            if owns_session:
                await session.close()
```

**Step 5: Run tests — expect pass**

```bash
pytest custom_components/napoleon/tests/test_rest.py -v
```

Expected: 5 passed.

**Step 6: Commit**

```bash
git add custom_components/napoleon/api/rest.py \
        custom_components/napoleon/tests/test_rest.py \
        custom_components/napoleon/tests/fixtures/
git commit -m "feat(rest): add AylaRest with device/property/lan endpoints

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — Property maps

### Task 2.1 — `PropertyMap` base (TDD)

**Files:**
- Create: `custom_components/napoleon/property_maps/__init__.py`
- Create: `custom_components/napoleon/property_maps/base.py`
- Create: `custom_components/napoleon/tests/test_property_maps_base.py`

**Step 1: Failing test**

`test_property_maps_base.py`:

```python
from __future__ import annotations

import pytest

from custom_components.napoleon.property_maps.base import (
    EntityCategory,
    EntityDef,
    EntityKind,
    PropertyMap,
)


def test_entity_def_value_fn_applied():
    ed = EntityDef(
        key="probe_1",
        name="Probe 1",
        kind=EntityKind.SENSOR,
        source="PRB_TMP_ONE",
        value_fn=lambda v: None if v == 0 else v,
    )
    assert ed.resolve({"PRB_TMP_ONE": 0}) is None
    assert ed.resolve({"PRB_TMP_ONE": 24.5}) == 24.5


def test_entity_def_missing_source_returns_none():
    ed = EntityDef(key="x", name="X", kind=EntityKind.SENSOR, source="NOPE")
    assert ed.resolve({}) is None


def test_property_map_emits_all_defs():
    m = PropertyMap(
        oem_model="test",
        entities=[
            EntityDef(key="a", name="A", kind=EntityKind.SENSOR, source="A"),
            EntityDef(key="b", name="B", kind=EntityKind.BINARY_SENSOR, source="B",
                      category=EntityCategory.DIAGNOSTIC),
        ],
    )
    assert [e.key for e in m.entities] == ["a", "b"]


def test_entity_def_value_fn_exception_returns_none():
    ed = EntityDef(
        key="x", name="X", kind=EntityKind.SENSOR, source="X",
        value_fn=lambda v: 1 / 0,
    )
    assert ed.resolve({"X": 1}) is None
```

**Step 2: Run — expect ImportError**

**Step 3: Implement `base.py`**

```python
"""Property map data classes (per-oem_model → HA entity defs)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


class EntityKind(str, Enum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"


class EntityCategory(str, Enum):
    DIAGNOSTIC = "diagnostic"
    NONE = ""


@dataclass(slots=True, frozen=True)
class EntityDef:
    key: str
    name: str
    kind: EntityKind
    source: str
    value_fn: Callable[[Any], Any] | None = None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    category: EntityCategory = EntityCategory.NONE
    icon: str | None = None
    # if True, stays available when grill is offline (last-known value)
    always_available: bool = False

    def resolve(self, props: dict[str, Any]) -> Any:
        if self.source not in props:
            return None
        raw = props[self.source]
        if self.value_fn is None:
            return raw
        try:
            return self.value_fn(raw)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("value_fn failed for %s: %s", self.key, err)
            return None


@dataclass(slots=True, frozen=True)
class PropertyMap:
    oem_model: str
    entities: list[EntityDef] = field(default_factory=list)
```

**Step 4: Run — expect pass**

**Step 5: Commit**

```bash
git add custom_components/napoleon/property_maps/__init__.py \
        custom_components/napoleon/property_maps/base.py \
        custom_components/napoleon/tests/test_property_maps_base.py
git commit -m "feat(maps): add EntityDef and PropertyMap base

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.2 — `thermometer_mqtt_eu` property map (TDD)

**Files:**
- Create: `custom_components/napoleon/property_maps/thermometer_mqtt_eu.py`
- Create: `custom_components/napoleon/tests/test_thermometer_mqtt_eu.py`
- Create: `custom_components/napoleon/tests/fixtures/thermometer_mqtt_eu_live.json` (full 59-prop capture, anonymized)

**Step 1: Create the fixture** — dump of the real 59 properties we captured today, with DSN replaced by the placeholder. (Executor: reference `~/.napoleon_session.json` + earlier REST capture to assemble. Must include `TRGT_TMP_FOUR = {"ptr":[4095]}`, `CKTIME = {}` empty JSON, and all probe temps.)

`thermometer_mqtt_eu_live.json`:

```json
{
  "BRT_LVL": 5,
  "BSMODE": false,
  "BT_LVL": 5,
  "CKNME_PRB_FOUR": "",
  "CKTIME": "{\n\n}",
  "CNTRY": "Germany",
  "DEVC_NME": "Prestige",
  "DTSPLY": 0,
  "DTYPE": 1,
  "EMTY_TNK_W": 13000,
  "F_TNKWT": 24000,
  "GS_TNK_NAME": "Rheingas",
  "GS_UNT": 0,
  "LCD_OFF": true,
  "PRB_FOUR_NME": "",
  "PRB_STAT": 8,
  "PRB_TMP_FOUR": 28.0,
  "PRB_TMP_ONE": 0.0,
  "PRB_TMP_THREE": 0.0,
  "PRB_TMP_TWO": 0.0,
  "REGN": "Central Europe",
  "RSSI": -79,
  "RST_CNT": 1,
  "TMP_ALRT_PRB_FOUR": "",
  "TMR_ALRT_PRB_FOUR": "",
  "TNK_WT": 7910,
  "TOFF": false,
  "TRGT_STAT_FOUR": 2,
  "TRGT_TMP_FOUR": "{\n  \"ptr\" : [\n    4095\n  ]\n}",
  "TUNIT": false,
  "version": "thermometer v6.0.10_EU"
}
```

**Step 2: Failing test**

`test_thermometer_mqtt_eu.py`:

```python
from __future__ import annotations

import json
from importlib.resources import files

import pytest

from custom_components.napoleon.property_maps import load_map
from custom_components.napoleon.property_maps.base import EntityKind


@pytest.fixture
def live():
    p = files("custom_components.napoleon.tests.fixtures").joinpath(
        "thermometer_mqtt_eu_live.json"
    )
    return json.loads(p.read_text())


def test_load_by_oem_model():
    m = load_map("thermometer-mqtt-eu")
    assert m.oem_model == "thermometer-mqtt-eu"
    assert len(m.entities) >= 15


def test_probe_temperatures_expose_celsius_when_tunit_false(live):
    m = load_map("thermometer-mqtt-eu")
    probe4 = next(e for e in m.entities if e.key == "probe_4_temperature")
    assert probe4.kind is EntityKind.SENSOR
    assert probe4.resolve(live) == 28.0
    assert probe4.unit in {"°C", "C"}


def test_probe_temperature_zero_means_unplugged_none(live):
    m = load_map("thermometer-mqtt-eu")
    probe1 = next(e for e in m.entities if e.key == "probe_1_temperature")
    assert probe1.resolve(live) is None  # PRB_TMP_ONE = 0.0 → unplugged


def test_target_temp_ptr_sentinel_returns_none(live):
    m = load_map("thermometer-mqtt-eu")
    target4 = next(e for e in m.entities if e.key == "probe_4_target_temperature")
    assert target4.resolve(live) is None


def test_tank_percent_derived(live):
    m = load_map("thermometer-mqtt-eu")
    pct = next(e for e in m.entities if e.key == "tank_percent")
    v = pct.resolve(live)
    assert v is not None
    assert -100 < v < 100  # raw math: (7910 - 13000) / (24000 - 13000) * 100 ≈ -46


def test_rssi_diagnostic(live):
    from custom_components.napoleon.property_maps.base import EntityCategory
    m = load_map("thermometer-mqtt-eu")
    rssi = next(e for e in m.entities if e.key == "rssi")
    assert rssi.category is EntityCategory.DIAGNOSTIC
    assert rssi.unit == "dBm"
    assert rssi.resolve(live) == -79


def test_firmware_always_available(live):
    m = load_map("thermometer-mqtt-eu")
    fw = next(e for e in m.entities if e.key == "firmware_version")
    assert fw.always_available is True
    assert fw.resolve(live) == "thermometer v6.0.10_EU"


def test_unknown_model_falls_back_to_generic():
    m = load_map("martian-grill")
    assert m.oem_model == "unknown"
```

**Step 3: Run — expect ImportError**

**Step 4: Implement `property_maps/__init__.py` loader**

```python
"""Load the PropertyMap matching a given Ayla oem_model."""

from __future__ import annotations

from .base import EntityCategory, EntityDef, EntityKind, PropertyMap

_MAPS: dict[str, PropertyMap] = {}


def register(m: PropertyMap) -> None:
    _MAPS[m.oem_model] = m


def load_map(oem_model: str) -> PropertyMap:
    if oem_model in _MAPS:
        return _MAPS[oem_model]
    return _MAPS["unknown"]


# Eager-register all shipped maps
from . import thermometer_mqtt_eu as _t  # noqa: F401,E402
from . import unknown as _u  # noqa: F401,E402
```

**Step 5: Implement `property_maps/unknown.py`**

```python
"""Fallback property map: every raw property as a diagnostic sensor."""

from __future__ import annotations

from . import register
from .base import EntityCategory, EntityDef, EntityKind, PropertyMap

# runtime-populated from the first properties() call; shipped empty
UNKNOWN = PropertyMap(oem_model="unknown", entities=[])
register(UNKNOWN)
```

**Step 6: Implement `property_maps/thermometer_mqtt_eu.py`**

```python
"""PropertyMap for Napoleon thermometer-mqtt-eu (Prestige 500 thermometer module)."""

from __future__ import annotations

import json
from typing import Any

from . import register
from .base import EntityCategory, EntityDef, EntityKind, PropertyMap


def _probe_temp(v: Any) -> float | None:
    # 0.0 → unplugged probe
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f == 0.0 else f


def _target_temp(v: Any) -> float | None:
    # Device encodes "unset" as {"ptr":[4095]}; otherwise a single float in ptr[0]
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return None if f >= 4094 else f
    if isinstance(v, str):
        try:
            doc = json.loads(v)
        except json.JSONDecodeError:
            return None
        ptr = doc.get("ptr") if isinstance(doc, dict) else None
        if not ptr:
            return None
        f = float(ptr[0])
        return None if f >= 4094 else f
    return None


def _tank_pct_factory(empty_key: str, full_key: str, cur_key: str):
    # Closure that needs the full property dict, not just one value;
    # we model this as a "derived" entity whose value_fn takes the dict via
    # a special marker (see EntityDef.resolve_derived below).
    def fn(props: dict[str, Any]) -> float | None:
        try:
            empty = float(props[empty_key])
            full = float(props[full_key])
            cur = float(props[cur_key])
            if full == empty:
                return None
            return round((cur - empty) / (full - empty) * 100.0, 1)
        except (KeyError, TypeError, ValueError):
            return None

    return fn


THERMOMETER_MQTT_EU = PropertyMap(
    oem_model="thermometer-mqtt-eu",
    entities=[
        EntityDef("probe_1_temperature", "Probe 1 temperature", EntityKind.SENSOR,
                  source="PRB_TMP_ONE", value_fn=_probe_temp,
                  unit="°C", device_class="temperature", state_class="measurement"),
        EntityDef("probe_2_temperature", "Probe 2 temperature", EntityKind.SENSOR,
                  source="PRB_TMP_TWO", value_fn=_probe_temp,
                  unit="°C", device_class="temperature", state_class="measurement"),
        EntityDef("probe_3_temperature", "Probe 3 temperature", EntityKind.SENSOR,
                  source="PRB_TMP_THREE", value_fn=_probe_temp,
                  unit="°C", device_class="temperature", state_class="measurement"),
        EntityDef("probe_4_temperature", "Probe 4 temperature", EntityKind.SENSOR,
                  source="PRB_TMP_FOUR", value_fn=_probe_temp,
                  unit="°C", device_class="temperature", state_class="measurement"),
        EntityDef("probe_4_target_temperature", "Probe 4 target", EntityKind.SENSOR,
                  source="TRGT_TMP_FOUR", value_fn=_target_temp,
                  unit="°C", device_class="temperature"),
        EntityDef("tank_weight_current", "Propane tank weight", EntityKind.SENSOR,
                  source="TNK_WT", unit="g", device_class="weight", state_class="measurement"),
        EntityDef("tank_weight_empty", "Propane tank empty weight", EntityKind.SENSOR,
                  source="EMTY_TNK_W", unit="g", category=EntityCategory.DIAGNOSTIC),
        EntityDef("tank_weight_full", "Propane tank full weight", EntityKind.SENSOR,
                  source="F_TNKWT", unit="g", category=EntityCategory.DIAGNOSTIC),
        EntityDef("rssi", "Wi-Fi signal", EntityKind.SENSOR,
                  source="RSSI", unit="dBm", device_class="signal_strength",
                  state_class="measurement", category=EntityCategory.DIAGNOSTIC,
                  always_available=True),
        EntityDef("firmware_version", "Firmware", EntityKind.SENSOR,
                  source="version", category=EntityCategory.DIAGNOSTIC,
                  always_available=True),
        EntityDef("device_name", "Device name", EntityKind.SENSOR,
                  source="DEVC_NME", category=EntityCategory.DIAGNOSTIC,
                  always_available=True),
        EntityDef("country", "Country", EntityKind.SENSOR,
                  source="CNTRY", category=EntityCategory.DIAGNOSTIC,
                  always_available=True),
        EntityDef("gas_tank_name", "Gas tank brand", EntityKind.SENSOR,
                  source="GS_TNK_NAME", category=EntityCategory.DIAGNOSTIC,
                  always_available=True),
        EntityDef("reset_count", "Reset count", EntityKind.SENSOR,
                  source="RST_CNT", category=EntityCategory.DIAGNOSTIC,
                  state_class="total_increasing", always_available=True),
        EntityDef("lcd_off", "LCD off", EntityKind.BINARY_SENSOR,
                  source="LCD_OFF", category=EntityCategory.DIAGNOSTIC),
        EntityDef("base_mode", "Base mode", EntityKind.BINARY_SENSOR, source="BSMODE"),
        EntityDef("turn_off", "Scheduled off", EntityKind.BINARY_SENSOR, source="TOFF"),
        EntityDef("probe_4_alert_temp", "Probe 4 temp alert", EntityKind.BINARY_SENSOR,
                  source="TMP_ALRT_PRB_FOUR",
                  value_fn=lambda v: bool(v)),
        EntityDef("probe_4_alert_timer", "Probe 4 timer alert", EntityKind.BINARY_SENSOR,
                  source="TMR_ALRT_PRB_FOUR",
                  value_fn=lambda v: bool(v)),
    ],
)


# Derived entity exposed separately because its value_fn needs the full props dict.
# Implemented via a thin subclass so the test can still `.resolve(live)`.
class DerivedEntityDef(EntityDef):
    def resolve(self, props: dict[str, Any]) -> Any:  # type: ignore[override]
        if self.value_fn is None:
            return None
        try:
            return self.value_fn(props)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return None


_TANK_PCT = DerivedEntityDef(
    key="tank_percent",
    name="Propane tank level",
    kind=EntityKind.SENSOR,
    source="TNK_WT",  # listed for UI; resolve() uses full dict
    value_fn=_tank_pct_factory("EMTY_TNK_W", "F_TNKWT", "TNK_WT"),
    unit="%",
    state_class="measurement",
)
object.__setattr__(THERMOMETER_MQTT_EU, "entities", [*THERMOMETER_MQTT_EU.entities, _TANK_PCT])

register(THERMOMETER_MQTT_EU)
```

**Step 7: Run tests — expect pass**

```bash
pytest custom_components/napoleon/tests/test_thermometer_mqtt_eu.py -v
```

**Step 8: Commit**

```bash
git add custom_components/napoleon/property_maps/ \
        custom_components/napoleon/tests/test_thermometer_mqtt_eu.py \
        custom_components/napoleon/tests/fixtures/thermometer_mqtt_eu_live.json
git commit -m "feat(maps): add thermometer-mqtt-eu property map with derived tank%

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — MQTT client + Coordinator

### Task 3.1 — `AylaMqttClient` (TDD with fake broker)

**Files:**
- Create: `custom_components/napoleon/api/mqtt.py`
- Create: `custom_components/napoleon/tests/test_mqtt.py`

**Design note:** Use `aiomqtt` but inject the client factory so tests can swap in a fake. Keep the public surface tiny: `connect()`, `disconnect()`, `on_property(handler)`, `on_connectivity(handler)`.

**Step 1: Failing test** — writes a FakeMqttClient that mimics `aiomqtt.Client`'s async context-manager + `.messages` async iterator. Asserts: on connect we subscribe to the three topics derived from DSN list; on incoming message of each type, the registered handler fires with parsed payload; on disconnect the backoff sequence follows constants.

*(Full test code is verbose but mechanical; executor should start with 6 tests — one per topic type, one for subscribe list, one for backoff order, one for credential rotation.)*

**Step 2–4: Implement + iterate until green.** Key shape:

```python
class AylaMqttClient:
    def __init__(
        self,
        region: RegionProfile,
        auth: AylaAuth,
        *,
        client_id: str,
        client_factory=aiomqtt.Client,
    ) -> None: ...

    def watch_device(self, dsn: str) -> None: ...
    def on_property(self, cb: Callable[[str, str, Any], None]) -> None: ...
    def on_connectivity(self, cb: Callable[[str, str], None]) -> None: ...
    async def start(self) -> None: ...  # background task, exp backoff, token rotation
    async def stop(self) -> None: ...
```

Topic constants:

```python
TOPIC_PROPERTY_UPDATE = "ayla/{dsn}/property/update"
TOPIC_PROPERTY_BATCH = "ayla/{dsn}/property/batch"
TOPIC_CONNECTIVITY = "ayla/{dsn}/connectivity"
```

**Step 5: Commit**

```bash
git commit -m "feat(mqtt): add AylaMqttClient with reconnect and token rotation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

**Note to executor:** Exact MQTT topic strings must be confirmed against a live session before the first release. The design acknowledges this. If topics differ, only the three constants above change — handler shape is identical.

---

### Task 3.2 — `NapoleonCoordinator` (TDD, focuses on availability rule)

**Files:**
- Create: `custom_components/napoleon/coordinator.py`
- Create: `custom_components/napoleon/tests/test_coordinator.py`

**Step 1: Availability-rule table-driven test (THE key test).** Cover all 8 combinations of the three inputs in §4e of the design doc:

```python
@pytest.mark.parametrize("mqtt,recent_update,rest,expected", [
    ("online",  True,  "Online",  True),
    ("online",  True,  "Offline", True),
    ("online",  False, "Offline", True),
    ("offline", True,  "Online",  True),   # recent update wins
    ("offline", False, "Online",  True),   # rest wins
    ("offline", False, "Offline", False),
    (None,      True,  "Offline", True),
    (None,      False, "Offline", False),
])
def test_connectivity_rule(mqtt, recent_update, rest, expected):
    c = NapoleonCoordinator.__new__(NapoleonCoordinator)  # no-hass construction
    c._connectivity = {"D": mqtt} if mqtt else {}
    c._last_update = {"D": time.time()} if recent_update else {}
    c._rest_status = {"D": rest}
    assert c.is_online("D") is expected
```

Plus a test that `UpdateFailed` is **never** raised when `is_online == False` during a coordinator refresh, and that `ingest()` merges partial dicts.

**Step 2–4: Implement** — `coordinator.py`:

```python
"""DataUpdateCoordinator merging REST heartbeat + MQTT pushes."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.auth import AylaAuth, InvalidCredentials
from .api.mqtt import AylaMqttClient
from .api.rest import AylaRest, CloudUnreachable, Device
from .const import (
    DOMAIN,
    PROPERTY_UPDATE_STALE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class NapoleonCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        auth: AylaAuth,
        rest: AylaRest,
        mqtt: AylaMqttClient,
        heartbeat_seconds: int,
    ) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=None,  # set via heartbeat task, not polling
        )
        self._auth = auth
        self._rest = rest
        self._mqtt = mqtt
        self._heartbeat = heartbeat_seconds
        self._devices: list[Device] = []
        self._props: dict[str, dict[str, Any]] = {}
        self._rest_status: dict[str, str] = {}
        self._connectivity: dict[str, str] = {}
        self._last_update: dict[str, float] = {}
        mqtt.on_property(self._on_property)
        mqtt.on_connectivity(self._on_connectivity)

    @property
    def devices(self) -> list[Device]:
        return self._devices

    def props(self, dsn: str) -> Mapping[str, Any]:
        return self._props.get(dsn, {})

    def is_online(self, dsn: str) -> bool:
        if self._connectivity.get(dsn) == "online":
            return True
        last = self._last_update.get(dsn, 0.0)
        if last and time.time() - last < PROPERTY_UPDATE_STALE_SECONDS:
            return True
        return self._rest_status.get(dsn) == "Online"

    def ingest(self, dsn: str, partial: Mapping[str, Any]) -> None:
        self._props.setdefault(dsn, {}).update(partial)
        self._last_update[dsn] = time.time()

    async def hydrate(self) -> None:
        try:
            self._devices = await self._rest.devices()
            for d in self._devices:
                self._rest_status[d.dsn] = d.connection_status
                self._props[d.dsn] = await self._rest.properties(d.dsn)
                self._mqtt.watch_device(d.dsn)
        except InvalidCredentials as err:
            raise ConfigEntryAuthFailed from err
        except CloudUnreachable as err:
            raise UpdateFailed(str(err)) from err
        self.async_set_updated_data(self._props)

    async def heartbeat(self) -> None:
        """Slow REST poll to refresh connection_status. Does NOT raise on grill offline."""
        try:
            devices = await self._rest.devices()
            for d in devices:
                self._rest_status[d.dsn] = d.connection_status
        except InvalidCredentials as err:
            raise ConfigEntryAuthFailed from err
        except CloudUnreachable:
            _LOGGER.debug("heartbeat: cloud unreachable, keeping last state")
            return
        self.async_set_updated_data(self._props)

    def _on_property(self, dsn: str, prop: str, value: Any) -> None:
        self.ingest(dsn, {prop: value})
        self.async_set_updated_data(self._props)

    def _on_connectivity(self, dsn: str, state: str) -> None:
        self._connectivity[dsn] = state
        self.async_set_updated_data(self._props)
```

**Step 5: Commit**

```bash
git commit -m "feat(coordinator): NapoleonCoordinator with offline-is-healthy rule

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — HA integration surface

### Task 4.1 — `entity.py` base

**Files:**
- Create: `custom_components/napoleon/entity.py`
- Create: `custom_components/napoleon/tests/test_entity.py`

**Step 1: Failing test** — asserts unique_id format `<dsn>_<entity_key>`, device_info includes identifiers `{(DOMAIN, dsn)}`, name, model, sw_version, manufacturer `"Napoleon Grills"`, and that `available` follows the `coordinator.is_online()` rule combined with `EntityDef.always_available`.

**Step 2–4: Implement**

```python
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.rest import Device
from .const import DOMAIN
from .coordinator import NapoleonCoordinator
from .property_maps.base import EntityDef


class NapoleonEntity(CoordinatorEntity[NapoleonCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NapoleonCoordinator,
        device: Device,
        entity_def: EntityDef,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._def = entity_def
        self._attr_unique_id = f"{device.dsn}_{entity_def.key}"
        self._attr_name = entity_def.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.dsn)},
            name=device.product_name or "Napoleon Grill",
            manufacturer="Napoleon Grills",
            model=device.model or device.oem_model,
            sw_version=device.sw_version,
            configuration_url="https://www.napoleon.com/en/napoleon-home",
        )
        self._attr_entity_category = (
            None if entity_def.category.value == "" else "diagnostic"
        )

    @property
    def available(self) -> bool:
        if self._def.always_available:
            return True
        return self.coordinator.is_online(self._device.dsn)

    def _raw_value(self):
        props = self.coordinator.props(self._device.dsn)
        return self._def.resolve(dict(props))
```

**Step 5: Commit**

---

### Task 4.2 — `sensor.py` platform (TDD)

**Files:**
- Create: `custom_components/napoleon/sensor.py`
- Create: `custom_components/napoleon/tests/test_sensor.py`

**Step 1: Failing HA-fixture test** — sets up an entry with a mocked coordinator preloaded from the live fixture, asserts:
- `sensor.prestige_probe_4_temperature` exists, `native_value == 28.0`, unit `"°C"`
- `sensor.prestige_tank_percent` exists with a float value
- `sensor.prestige_firmware` stays available when coordinator `is_online = False`
- `sensor.prestige_probe_4_temperature` goes to `STATE_UNAVAILABLE` when coordinator `is_online = False`

**Step 2–4: Implement sensor.py**

```python
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NapoleonCoordinator
from .entity import NapoleonEntity
from .property_maps import load_map
from .property_maps.base import EntityKind


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback
) -> None:
    coordinator: NapoleonCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NapoleonSensor] = []
    for device in coordinator.devices:
        pmap = load_map(device.oem_model)
        for d in pmap.entities:
            if d.kind is EntityKind.SENSOR:
                entities.append(NapoleonSensor(coordinator, device, d))
    add(entities)


class NapoleonSensor(NapoleonEntity, SensorEntity):
    def __init__(self, coordinator, device, entity_def) -> None:
        super().__init__(coordinator, device, entity_def)
        self._attr_native_unit_of_measurement = entity_def.unit
        self._attr_device_class = entity_def.device_class
        self._attr_state_class = entity_def.state_class
        self._attr_icon = entity_def.icon

    @property
    def native_value(self):
        return self._raw_value()
```

**Step 5: Commit**

---

### Task 4.3 — `binary_sensor.py` platform (TDD)

Mirror of 4.2 with `BinarySensorEntity`, `is_on` returns `bool(self._raw_value())`, handles `None` as "unknown" → `self._attr_is_on = None`. One test per binary-sensor def in the property map.

---

### Task 4.4 — Config flow (TDD, the biggest task)

**Files:**
- Create: `custom_components/napoleon/config_flow.py`
- Create: `custom_components/napoleon/tests/test_config_flow.py`
- Create: `custom_components/napoleon/strings.json`
- Create: `custom_components/napoleon/translations/en.json`

**Step 1: Failing tests** — one `async def` per flow path:

1. `test_user_step_happy_path` — submit valid EU creds, mock sign_in 200 + devices 200, expect `CREATE_ENTRY` with title = email, data = `{region, email, refresh_token}`.
2. `test_user_step_invalid_auth` — 401 → form shown again with `errors={"base":"invalid_auth"}`.
3. `test_user_step_cannot_connect` — TimeoutError → `cannot_connect`.
4. `test_user_step_no_devices_creates_entry_with_repair` — 200 devices = `[]` → still CREATE_ENTRY, repair issue registered.
5. `test_duplicate_account_rejected` — same unique_id returns `ABORT` `already_configured`.
6. `test_reauth_step_happy_path` — mocked coordinator raises `ConfigEntryAuthFailed`; reauth flow prompts for password, accepts, updates refresh_token.
7. `test_reauth_email_mismatch` — error `reauth_email_mismatch`.
8. `test_options_step` — set heartbeat to 120, diagnostic logging = true, expect update.

**Step 2–4: Implement config_flow.py + strings**

```python
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api.auth import AylaAuth, InvalidCredentials
from .api.rest import AylaRest, CloudUnreachable
from .const import (
    CONF_DIAGNOSTIC_LOGGING,
    CONF_EMAIL,
    CONF_HEARTBEAT_INTERVAL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    DEFAULT_HEARTBEAT_INTERVAL,
    DOMAIN,
    MAX_HEARTBEAT_INTERVAL,
    MIN_HEARTBEAT_INTERVAL,
)
from .regions import KNOWN_REGIONS, UnknownRegion, get_region


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION, default="EU"): vol.In(KNOWN_REGIONS),
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class NapoleonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                region = get_region(user_input[CONF_REGION])
            except UnknownRegion:
                errors["base"] = "unknown_region"
            else:
                auth = AylaAuth(region)
                try:
                    result = await auth.sign_in(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
                except InvalidCredentials:
                    errors["base"] = "invalid_auth"
                except CloudUnreachable:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        f"{region.name}:{user_input[CONF_EMAIL].lower()}"
                    )
                    self._abort_if_unique_id_configured()
                    # devices discovered at startup, not here — unavailable if grill off
                    return self.async_create_entry(
                        title=user_input[CONF_EMAIL],
                        data={
                            CONF_REGION: region.name,
                            CONF_EMAIL: user_input[CONF_EMAIL],
                            CONF_REFRESH_TOKEN: result.refresh_token,
                        },
                    )
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        assert entry is not None
        if user_input is not None:
            if user_input.get(CONF_EMAIL, entry.data[CONF_EMAIL]).lower() != entry.data[CONF_EMAIL].lower():
                errors["base"] = "reauth_email_mismatch"
            else:
                region = get_region(entry.data[CONF_REGION])
                auth = AylaAuth(region)
                try:
                    result = await auth.sign_in(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
                except InvalidCredentials:
                    errors["base"] = "invalid_auth"
                except CloudUnreachable:
                    errors["base"] = "cannot_connect"
                else:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, CONF_REFRESH_TOKEN: result.refresh_token},
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return NapoleonOptionsFlow(config_entry)


class NapoleonOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_HEARTBEAT_INTERVAL,
                    default=self.entry.options.get(
                        CONF_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL
                    ),
                ): vol.All(int, vol.Range(min=MIN_HEARTBEAT_INTERVAL, max=MAX_HEARTBEAT_INTERVAL)),
                vol.Optional(
                    CONF_DIAGNOSTIC_LOGGING,
                    default=self.entry.options.get(CONF_DIAGNOSTIC_LOGGING, False),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
```

**Step 2 (aux): strings.json** — mirrors the error codes + UI labels.

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Napoleon Home",
        "description": "Sign in with the account you use in the Napoleon Home app.",
        "data": { "region": "Region", "email": "Email", "password": "Password" }
      },
      "reauth_confirm": {
        "title": "Re-authenticate",
        "description": "Your Napoleon Home session for {email} expired. Enter the current password."
      }
    },
    "error": {
      "invalid_auth": "Email or password incorrect.",
      "cannot_connect": "Can't reach the Napoleon (Ayla) cloud.",
      "unknown_region": "Unknown region.",
      "reauth_email_mismatch": "Please use the same email address as the existing entry."
    },
    "abort": {
      "already_configured": "This account is already configured.",
      "reauth_successful": "Re-authentication succeeded."
    }
  },
  "options": {
    "step": {
      "init": {
        "data": {
          "heartbeat_interval": "Cloud heartbeat interval (seconds)",
          "diagnostic_logging": "Enable diagnostic logging"
        }
      }
    }
  },
  "issues": {
    "no_devices": {
      "title": "No Napoleon devices on this account",
      "description": "Add a device in the Napoleon Home app, then click Reload on this integration."
    }
  }
}
```

`translations/en.json` = copy of `strings.json` (HA pattern).

**Step 5: Commit**

```bash
git commit -m "feat(config-flow): add user/reauth/options steps + strings

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4.5 — `__init__.py` integration setup

**Files:**
- Modify: `custom_components/napoleon/__init__.py`
- Create: `custom_components/napoleon/tests/test_init.py`

**Step 1: Test setup + unload round-trip, reload on options change, reauth-on-401 path.**

**Step 2–4: Implement**

```python
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api.auth import AylaAuth, InvalidCredentials
from .api.mqtt import AylaMqttClient
from .api.rest import AylaRest, CloudUnreachable
from .const import (
    CONF_DIAGNOSTIC_LOGGING,
    CONF_HEARTBEAT_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    DEFAULT_HEARTBEAT_INTERVAL,
    DOMAIN,
)
from .coordinator import NapoleonCoordinator
from .regions import get_region

_PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR, Platform.BINARY_SENSOR)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    region = get_region(entry.data[CONF_REGION])
    auth = AylaAuth(region, refresh_token=entry.data[CONF_REFRESH_TOKEN])
    try:
        await auth.refresh()
    except InvalidCredentials as err:
        raise ConfigEntryAuthFailed from err

    rest = AylaRest(region, auth)
    mqtt = AylaMqttClient(region, auth, client_id=f"ha-napoleon-{entry.entry_id}")
    heartbeat = entry.options.get(CONF_HEARTBEAT_INTERVAL, DEFAULT_HEARTBEAT_INTERVAL)
    coordinator = NapoleonCoordinator(hass, auth=auth, rest=rest, mqtt=mqtt, heartbeat_seconds=heartbeat)

    if entry.options.get(CONF_DIAGNOSTIC_LOGGING):
        logging.getLogger("custom_components.napoleon").setLevel(logging.DEBUG)

    try:
        await coordinator.hydrate()
    except CloudUnreachable as err:
        raise ConfigEntryAuthFailed(str(err)) from err  # retry via HA

    await mqtt.start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def _heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(heartbeat)
            try:
                await coordinator.heartbeat()
            except ConfigEntryAuthFailed:
                raise
            except Exception:  # noqa: BLE001
                _LOGGER.debug("heartbeat iteration failed", exc_info=True)

    entry.async_create_background_task(hass, _heartbeat_loop(), name="napoleon-heartbeat")
    entry.async_on_unload(lambda: asyncio.create_task(mqtt.stop()))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
```

**Step 5: Commit**

---

### Task 4.6 — End-to-end "grill offline" smoke test

**Files:**
- Create: `custom_components/napoleon/tests/test_grill_offline.py`

Asserts: install → grill-state sensors go `STATE_UNAVAILABLE` after the fixture flips device to `Offline` and MQTT sends `offline`, firmware sensor stays available, `async_set_updated_data` never triggers `UpdateFailed`, logs do not contain `ERROR`-level records about the grill state.

Single commit.

---

## Phase 5 — Polish

### Task 5.1 — `diagnostics.py`

HA diagnostics panel. Dumps config entry (with tokens scrubbed via `async_redact_data`), device list, latest props per device, connectivity state. Test: scrubbed output never contains `at-`, `rt-`, `smarthome_eu-…`, passwords.

### Task 5.2 — Coverage gate

Add `--cov-fail-under=85` to the `Test` workflow's `pytest` command. Run locally to confirm threshold met; bump if necessary. Commit.

### Task 5.3 — `release.yml` workflow

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  zip:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          cd custom_components/napoleon
          zip -r ../../napoleon.zip .
      - uses: softprops/action-gh-release@v2
        with:
          files: napoleon.zip
```

Commit.

### Task 5.4 — README expansion

Add install-via-HACS steps, screenshot placeholder, the "Is it working?" post-install checklist from design §5d, region support table, and a "Contributing a new property map" section. Commit.

### Task 5.5 — Tag `v0.1.0`

```bash
# manifest.json version already 0.1.0
git tag -a v0.1.0 -m "v0.1.0 — read-only sensors for thermometer-mqtt-eu"
git push --tags
gh release view v0.1.0   # verify asset attached
```

### Task 5.6 — Real-hardware smoke test (manual)

Follow the checklist in design §5d against the actual Prestige (DSN `AC000W038641980`). Take notes, file issues for anything broken, then decide whether to cut `v0.1.1`.

---

## Out of scope for this plan (for v2+)

- MQTT topic fuzzing + property control datapoints (write path).
- `pvx-field-us` / `pvx-field-eu` Prestige Pro property maps (community PRs).
- MeatStick / Woodstove / thermostat maps.
- Local MQTT proxy for true-offline operation.
- Translations beyond English.
- Codecov upload.

---

## Done criteria for v1

- [ ] All phase tasks committed, pushed, and green in CI.
- [ ] `v0.1.0` tagged, release asset attached.
- [ ] README install flow works in a fresh HA OS VM (via HACS custom repo).
- [ ] Real-hardware smoke test passes: sensors animate during an active cook, go `unavailable` quietly after the cook ends, HA restart resumes silently.
- [ ] Coverage ≥85 %, ruff + mypy clean.
- [ ] Ayla account password rotated from the one leaked earlier in this session.
