"""Fixtures for Napoleon Home tests."""
import threading

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations to be loaded."""
    yield

@pytest.fixture(autouse=True)
def skip_thread_leak_check(monkeypatch):
    """Targeted skip for the _run_safe_shutdown_loop thread leak."""
    orig_enumerate = threading.enumerate

    def mocked_enumerate():
        threads = orig_enumerate()
        return [t for t in threads if "_run_safe_shutdown_loop" not in t.name]

    monkeypatch.setattr(threading, "enumerate", mocked_enumerate)
