"""
RiskGraph AI - Configuration.

All secrets/config come from environment variables (see .env.example).
Nothing here is a real credential; defaults are safe for local dev.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "RiskGraph AI"
    environment: str = os.getenv("ENVIRONMENT", "local")

    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/riskgraph.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # LLM provider - never hard-code the key; read from env only.
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    model_artifact_path: str = os.getenv(
        "MODEL_ARTIFACT_PATH", str(BASE_DIR / "ml" / "artifacts" / "model.pkl")
    )
    rules_policy_path: str = os.getenv(
        "RULES_POLICY_PATH", str(BASE_DIR / "backend" / "app" / "policies" / "rules.yaml")
    )
    policy_docs_dir: str = os.getenv("POLICY_DOCS_DIR", str(BASE_DIR / "data" / "policies"))

    cors_allow_origins: list[str] = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")

    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
