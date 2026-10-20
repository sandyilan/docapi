from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", extra="ignore"
    )

    app_name: str = "Document API"
    environment: str = "dev"
    log_level: str = "INFO"
    max_upload_mb: int = 5
    upload_dir: str = "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()