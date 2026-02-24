from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Podcast Summarizer MVP"
    env: str = "dev"
    log_level: str = "INFO"

    data_dir: Path = Field(default=Path("data"))

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    whisper_model_size: str = "base"
    whisper_compute_type: str = "int8"
    whisper_device: str = "cpu"

    map_chunk_chars: int = 6000

    fmp_api_key: str | None = None
    fmp_base_url: str = "https://financialmodelingprep.com"
    fmp_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "jobs").mkdir(parents=True, exist_ok=True)
    return settings
