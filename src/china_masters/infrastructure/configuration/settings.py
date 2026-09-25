from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CM_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///data/china_masters.db"
    workspace_root: Path = Path("workspace")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False
    job_max_attempts: int = Field(default=3, ge=1, le=20)
    job_poll_interval_seconds: float = Field(default=2.0, gt=0, le=3600)
    job_lease_seconds: int = Field(default=300, ge=1, le=86400)
