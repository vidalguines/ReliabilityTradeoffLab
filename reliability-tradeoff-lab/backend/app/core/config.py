"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "ReliabilityTradeoffLab"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://reliabilitytradeofflab.com",
        "*",  # Adjust for production
    ]
    MONTE_CARLO_DEFAULT_ITERATIONS: int = 10_000
    MONTE_CARLO_MAX_ITERATIONS: int = 100_000
    MAX_COMPONENTS: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
