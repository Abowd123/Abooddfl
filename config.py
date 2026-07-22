from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    bot_token: str
    encryption_key: str
    database_url: str = "sqlite:///data/bot.db"
    admin_ids: set[int] = Field(default_factory=set)
    max_zip_size_mb: int = 1900
    max_extracted_size_mb: int = 4096
    max_files: int = 10_000
    default_workers: int = 6
    max_workers: int = 12
    default_retries: int = 3
    progress_update_seconds: float = 2.0
    download_dir: Path = Path("data/downloads")
    extract_dir: Path = Path("data/extracted")
    log_dir: Path = Path("logs")
    telegram_local_api: bool = False
    telegram_api_base: str = "http://localhost:8081"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> set[int]:
        if isinstance(value, str):
            return {int(x.strip()) for x in value.split(",") if x.strip()}
        return set(value or [])

    def prepare_dirs(self) -> None:
        for path in (self.download_dir, self.extract_dir, self.log_dir, Path("data")):
            path.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    settings.prepare_dirs()
    return settings
