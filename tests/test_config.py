"""
tests.test_config
~~~~~~~~~~~~~~~~~~
Validate Settings loads correctly with defaults and env overrides.
"""

from __future__ import annotations

import os

from crawlforge.config.settings import Settings


class TestSettings:
    """Settings validation tests."""

    def test_defaults(self) -> None:
        """Settings should load with all defaults (no .env file needed)."""
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.app_name == "CrawlForge"
        assert settings.app_env == "development"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.app_port == 8000
        assert settings.crawl4ai_browser_type == "chromium"
        assert settings.crawl4ai_headless is True

    def test_is_production(self) -> None:
        """is_production property should work."""
        settings = Settings(app_env="production", _env_file=None)  # type: ignore[call-arg]
        assert settings.is_production is True
        assert settings.is_development is False

    def test_is_development(self) -> None:
        """is_development property should work."""
        settings = Settings(app_env="development", _env_file=None)  # type: ignore[call-arg]
        assert settings.is_development is True
        assert settings.is_production is False

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables should override defaults."""
        monkeypatch.setenv("APP_PORT", "9999")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.app_port == 9999
        assert settings.log_level == "ERROR"

    def test_queue_priority_range(self) -> None:
        """Queue priority must be between 1 and 10."""
        settings = Settings(queue_default_priority=5, _env_file=None)  # type: ignore[call-arg]
        assert 1 <= settings.queue_default_priority <= 10

    def test_secret_fields_masked(self) -> None:
        """SecretStr fields must not leak in repr."""
        settings = Settings(
            openai_api_key="sk-test-secret-key",  # type: ignore[arg-type]
            _env_file=None,  # type: ignore[call-arg]
        )
        repr_str = repr(settings)
        assert "sk-test-secret-key" not in repr_str


import pytest
