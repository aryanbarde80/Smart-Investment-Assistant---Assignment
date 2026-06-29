import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_base_dir() -> Path:
    if os.getenv("VERCEL"):
        return Path("/tmp/smart-investment-assistant")
    return Path(".")


BASE_DIR = _default_base_dir()


class Settings(BaseSettings):
    app_name: str = "Smart Investment Assistant"
    max_upload_mb: int = 25
    storage_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "uploads"
    extracted_assets_dir: Path = BASE_DIR / "extracted_assets"
    allowed_content_types: set[str] = {"application/pdf"}

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIA_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
