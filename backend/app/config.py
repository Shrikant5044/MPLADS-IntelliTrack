import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "MPLADS-IntelliTrack API"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Base paths
    # Resolves to repo_root/data/raw regardless of where uvicorn is launched from
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    REPO_ROOT: Path = BASE_DIR.parent
    DATA_RAW_DIR: Path = REPO_ROOT / "data" / "raw"

    # CORS settings for frontend integration
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
