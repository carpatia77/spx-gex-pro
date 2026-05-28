import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    eulerpool_api_key: str | None = None
    polygon_api_key: str | None = None
    
    # Defaults
    default_ticker: str = "SPX"
    default_expiration_days: int = 30
    strike_range_pct: float = 0.20  # ±20% do spot
    gamma_profile_levels: int = 60
    
    # Output
    output_dir: Path = Path("./output")
    chart_format: Literal["png", "html", "both"] = "png"
    chart_theme: Literal["dark", "light"] = "dark"
    
    # Provider priority
    provider_order: list[str] = ["eulerpool", "polygon", "yahoo"]
    
    # Cache settings
    cache_dir: Path = Path("./.cache")
    cache_ttl_seconds: int = 3600  # 1 hora
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure output and cache directories exist
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs(settings.cache_dir, exist_ok=True)
