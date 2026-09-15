from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/app.db"
    cors_origin: str = "http://localhost:3000"

    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_timeout_ms: int = 60000

    required_multiplier: int = 3
    low_accuracy_no_hint_threshold: float = 0.4
    high_wrong_after_hint3_threshold: float = 0.2


@lru_cache
def get_settings() -> Settings:
    return Settings()
