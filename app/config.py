import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).parent.parent / "data" / "careerpath.db")
    )
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        str(Path(__file__).parent.parent / "model" / "skill_matcher.keras")
    )
    CORS_ORIGINS: list[str] = ["*"]
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

settings = Settings()
