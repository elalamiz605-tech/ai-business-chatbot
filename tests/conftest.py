"""Test setup: force demo mode (no API key) before app.py is imported."""

import os
import sys
from pathlib import Path

os.environ["GEMINI_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

import app as app_module  # noqa: E402


@pytest.fixture
def client():
    app_module._requests_by_ip.clear()
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


@pytest.fixture
def business():
    return app_module.BUSINESS
