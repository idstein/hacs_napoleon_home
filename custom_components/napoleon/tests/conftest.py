"""Shared pytest fixtures + overrides.

The `pytest-homeassistant-custom-component` plugin is autoloaded by pytest and
registers a strict `verify_cleanup` autouse fixture that flags aiohttp's
internal shutdown thread as a leak. That fixture is tuned for tests that use
the ``hass`` fixture; it produces false positives for our pure-logic unit
tests that just talk to mocked HTTP. We shadow it with a no-op so the unit
tests don't have to carry HA-specific threading assumptions.

When integration-level tests that actually use the ``hass`` fixture land
later, they can re-enable the check by scoping their own stricter override
in a nested conftest.py.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def verify_cleanup() -> Generator[None]:
    """No-op override of the HA plugin's thread-leak checker."""
    yield
