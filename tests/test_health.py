"""
tests.test_health
~~~~~~~~~~~~~~~~~~
Validate the health endpoint works correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from crawlforge import __version__


class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """GET /health should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self, client: TestClient) -> None:
        """Response should contain status, version, and environment."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__
        assert "environment" in data

    def test_health_version_matches(self, client: TestClient) -> None:
        """Version in response should match package version."""
        response = client.get("/health")
        assert response.json()["version"] == "0.1.0"
