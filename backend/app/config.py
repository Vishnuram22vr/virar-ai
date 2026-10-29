from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "Virar AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Server & CORS
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # Database
    # Defaults to SQLite async database in the backend directory
    DATABASE_URL: str = "sqlite+aiosqlite:///./virar_ai.db"
    
    # Security & Dev Auth
    DEV_AUTH_MODE: bool = True
    DEV_ADMIN_KEY: str = "virar-dev-key-change-in-prod"
    DEV_USER_ID: str = "admin-developer"
    
    # Execution & Limits
    MAX_STEPS_PER_RUN: int = 15
    RUN_TIMEOUT_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 0.5
    
    # Cost Estimation Assumptions (Pricing per 1k tokens, USD)
    COST_PER_1K_PROMPT_TOKENS: float = 0.0015
    COST_PER_1K_COMPLETION_TOKENS: float = 0.0020
    
    # Optional LLM Configuration
    LLM_PROVIDER: str = "deterministic" # "deterministic" | "openai" | "gemini" | "anthropic"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "virar-deterministic-v1"

settings = Settings()
