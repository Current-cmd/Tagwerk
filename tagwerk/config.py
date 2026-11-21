from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    hf_token: str = ""
    gpu_worker_url: str = ""
    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./cache")
    data_date: str = "2026-11-26"
    site_lat: float = 48.137
    site_lon: float = 11.575
    replay_mode: bool = False
    project: str = "hoersaal"  # seed/ for hoersaal, else seed/projects/<project>/
    api_token: str = ""  # bearer token for every endpoint but /health and the pages; required unless TAGWERK_DEV=1
    tagwerk_dev: bool = False  # local development: allow an empty API_TOKEN (auth off)
    allow_project_create: bool = False  # /api/scan?make_project= writes seed/projects/<name>/
    max_upload_mb: int = 500  # per file and per request
    max_upload_files: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
