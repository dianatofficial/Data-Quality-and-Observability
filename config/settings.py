import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    """Application settings with environment variable overrides."""

    app_name: str = "Data Quality Gatekeeper"
    environment: Literal["development", "production", "test", "cloud_demo"] = "development"
    debug: bool = False

    # Database
    database_url: str = f"sqlite:///{BASE_DIR / 'local_storage' / 'data_quality.db'}"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Data Quality Thresholds & SLA
    sla_min_health_score: float = 95.0
    sla_max_error_rate: float = 0.05
    quarantine_retention_days: int = 90
    auto_quarantine_enabled: bool = True

    # Alerting & Webhooks
    slack_webhook_url: str = ""
    alert_severity_threshold: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    alert_channel: str = "#data-ops-alerts"

    # Storage Paths
    base_dir: Path = BASE_DIR
    data_docs_dir: Path = BASE_DIR / "reports"
    sample_data_dir: Path = BASE_DIR / "data"

    # Schema Drift Tolerance
    drift_score_threshold: float = 0.15

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> AppSettings:
    """Return cached application settings instance."""
    # Ensure necessary local folders exist
    settings = AppSettings()
    (settings.base_dir / "local_storage").mkdir(parents=True, exist_ok=True)
    settings.data_docs_dir.mkdir(parents=True, exist_ok=True)
    settings.sample_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
