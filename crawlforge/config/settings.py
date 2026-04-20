"""
crawlforge.config.settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~
All application configuration via pydantic-settings.
Every configurable value lives here — never scattered across modules.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for every tuneable knob in CrawlForge."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────
    app_name: str = "CrawlForge"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    worker_replicas: int = 2

    # ── Redis ────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Supabase / PostgreSQL ────────────────────────
    supabase_url: str = "http://localhost:54321"
    supabase_key: SecretStr = SecretStr("your-supabase-anon-key")
    supabase_service_key: SecretStr = SecretStr("your-supabase-service-key")
    database_url: str = "postgresql://postgres:postgres@db:5432/crawlforge"

    # ── OpenAI (primary embedding) ───────────────────
    openai_api_key: SecretStr = SecretStr("")
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Google GenAI (secondary embedding) ───────────
    google_api_key: SecretStr = SecretStr("")
    google_embedding_model: str = "models/text-embedding-004"

    # ── crawl4ai ─────────────────────────────────────
    crawl4ai_browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    crawl4ai_headless: bool = True
    crawl4ai_viewport_width: int = 1280
    crawl4ai_viewport_height: int = 720
    crawl4ai_text_mode: bool = False
    crawl4ai_light_mode: bool = False
    crawl4ai_verbose: bool = False

    # ── Queue ────────────────────────────────────────
    queue_max_retries: int = 4  # Total 5 attempts
    queue_num_workers: int = 5
    queue_backoff_base: float = 2.0
    queue_backoff_max: float = 60.0
    queue_default_priority: int = Field(default=5, ge=1, le=10)

    # ── Sessions ─────────────────────────────────────
    session_pool_size: int = 10
    session_ttl_seconds: int = 3600  # 1 hour



    # ── Derived helpers ──────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — created once on first call."""
    return Settings()
