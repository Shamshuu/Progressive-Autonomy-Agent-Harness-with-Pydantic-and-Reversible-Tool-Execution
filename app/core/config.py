import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Progressive Autonomy Agent Harness"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/agent_harness"
    )
    TRUST_THRESHOLD: int = int(os.getenv("TRUST_THRESHOLD", "3"))
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    MOCK_LLM_ENABLED: bool = os.getenv("MOCK_LLM_ENABLED", "true").lower() in ("true", "1", "yes")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
