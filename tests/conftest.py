"""
tests.conftest
~~~~~~~~~~~~~~~
Shared pytest fixtures.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from crawlforge.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI."""
    app = create_app()
    return TestClient(app)
