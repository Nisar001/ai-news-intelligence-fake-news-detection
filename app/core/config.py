from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", case_sensitive=False)

    name: str = "AI News Intelligence Platform"
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    allowed_origins: str = "http://localhost:3000"
    internal_api_keys: str = ""
    rate_limit: str = "60/minute"

    hf_model_name: str = "your-org/roberta-fake-news"
    hf_model_revision: str = "main"
    hf_use_gpu: bool = False
    model_label_fake: str = "FAKE"
    model_label_real: str = "REAL"
    model_low_confidence_threshold: float = 0.55
    model_uncertain_margin: float = 0.15
    model_max_tokens: int = 1024

    gemini_api_key: str = ""
    gemini_primary_model: str = "gemini-2.0-flash"
    gemini_fallback_model: str = "gemini-1.5-pro"
    gemini_timeout_seconds: int = 20
    gemini_max_retries: int = 3
    gemini_temperature: float = 0.2

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/ai_news"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    cache_ttl_seconds: int = 3600

    sentry_dsn: str = ""
    prometheus_enabled: bool = True

    app_config_path: str = "configs/app.yaml"
    prompts_config_path: str = "configs/prompts.yaml"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

    @property
    def api_keys(self) -> set[str]:
        return {x.strip() for x in self.internal_api_keys.split(",") if x.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def load_yaml_config(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
