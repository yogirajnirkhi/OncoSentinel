"""
OncoSentinel v2.0 — Application Settings
Satisfies: NFR-06 (no secrets in code), NFR-12 (reproducibility)

All configuration is loaded from environment variables or .env file.
No secrets, thresholds, or PHI-related values are hard-coded here.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore

    def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]:  # type: ignore
        return kwargs


class Settings(BaseSettings):
    """Central application settings — loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://onco:password@localhost:5432/oncosentinel"
    )

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://:password@localhost:6379/0")

    # ── MinIO / Object Storage ────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: SecretStr = Field(default=SecretStr("minioadmin"))
    minio_secret_key: SecretStr = Field(default=SecretStr("minioadmin"))
    minio_secure: bool = False
    minio_bucket_images: str = "onco-images"
    minio_bucket_artifacts: str = "onco-artifacts"
    minio_bucket_reports: str = "onco-reports"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_evidence: str = "clinical_evidence"

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:8b"

    # ── MLflow ────────────────────────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "oncosentinel_v2"

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(default=SecretStr("CHANGE_ME_jwt_secret_key"))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Config paths (no thresholds hard-coded here) ──────────────────────────
    taxonomy_config_path: Path = Path("configs/taxonomy.yaml")
    thresholds_config_path: Path = Path("configs/thresholds.yaml")
    fairness_strata_config_path: Path = Path("configs/fairness_strata.yaml")
    hms_config_path: Path = Path("configs/hms.yaml")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # ── Current platform phase (controls routing gate) ─────────────────────
    platform_phase: int = 2

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
